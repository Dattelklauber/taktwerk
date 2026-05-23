#!/usr/bin/env python3
"""Taktwerk — Drum Tempo Monitor

Grundgerüst der Live-Tempo-Erkennung mit eingebautem Mikrofon.

Funktion
    1. Spielt einen Klick im eingestellten Tempo (Audio + LED)
    2. Erfasst das Schlagzeug per Mikrofon und erkennt jeden Schlag
    3. Vergleicht jeden Schlag mit dem nächstliegenden erwarteten Klick
    4. Gibt Soll-BPM, Ist-BPM und Phasenabweichung in ms aus

Plattformen
    - Mac/Linux  → Entwicklungsmodus, Konsolen-Ausgabe, System-Audio
    - Raspberry Pi → produktiv, I²S-Audio + GPIO-LED

Abhängigkeiten
    pip install sounddevice numpy
    pip install gpiozero       # nur auf dem Pi

Hinweis: die Onset-Detection ist in reinem NumPy implementiert (HFC-
gewichteter Spektralfluss, gleiche Methode wie aubio's "hfc"). Es gibt
keine externe DSP-Bibliothek mehr — läuft auf jeder Python-Version, die
NumPy unterstützt.

Aufruf
    python3 tempo_monitor.py --bpm 120 --meter 4
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 44100
BLOCK_SIZE = 512

ON_PI = any(arch in platform.machine().lower() for arch in ("arm", "aarch64"))


# ────────────────────────────────────────────────────────────────────────
#  Onset-Detektor (HFC + Energie-Spektralfluss kombiniert)
# ────────────────────────────────────────────────────────────────────────
class OnsetDetector:
    """Erkennt Drum-Onsets durch zwei parallele Detektoren mit ODER-Logik:

    - **HFC-Spektralfluss**: Frequenz-gewichteter Fluss
      → empfindlich für Snare, Hi-Hat, Becken (hochfrequent)
    - **Energie-Spektralfluss**: ungewichteter Fluss
      → empfindlich für Kick, Tom (tieffrequent)

    Beide Detektoren haben adaptive Schwellwerte (Median × Faktor) UND
    eine Schwellwert-Untergrenze (10 % des Max der letzten 5 Sekunden).
    Die Untergrenze verhindert, dass die Schwelle in Stille-Phasen
    gegen Null sinkt und Raumrauschen als Onset erkannt wird.
    """

    MIN_INTERVAL_S = 0.12          # Doppel-Trigger-Sperre
    HISTORY_LEN = 20               # Median-Fenster für Schwelle
    THRESHOLD_FACTOR = 4.0
    FLOOR_WINDOW_BLOCKS = 430      # ~5 s bei 512 Samples / 44.1 kHz
    FLOOR_FRACTION = 0.10          # Schwelle nie unter 10 % des Max

    def __init__(self, sample_rate: int, block_size: int) -> None:
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._block_dur = block_size / sample_rate
        self._last_onset_t = 0.0
        n_bins = block_size // 2 + 1
        self._hfc_weights = np.arange(n_bins, dtype=np.float32)
        self._window = np.hanning(block_size).astype(np.float32)
        self._prev_hfc = np.zeros(n_bins, dtype=np.float32)
        self._prev_mag = np.zeros(n_bins, dtype=np.float32)
        self._hfc_history: deque[float] = deque(maxlen=self.HISTORY_LEN)
        self._eng_history: deque[float] = deque(maxlen=self.HISTORY_LEN)
        self._hfc_max_window: deque[float] = deque(maxlen=self.FLOOR_WINDOW_BLOCKS)
        self._eng_max_window: deque[float] = deque(maxlen=self.FLOOR_WINDOW_BLOCKS)
        # für Web-App-Kompatibilität / Diagnostik
        self.fluxHistory = self._hfc_history

    def process(self, samples: np.ndarray, block_start_t: float) -> float | None:
        spec = np.abs(np.fft.rfft(samples * self._window)).astype(np.float32)

        # HFC-Spektralfluss (gewichtet mit Frequenz-Index)
        hfc = self._hfc_weights * spec
        hfc_flux = float(np.maximum(0.0, hfc - self._prev_hfc).sum())
        self._prev_hfc = hfc

        # Energie-Spektralfluss (ungewichtete Summe der positiven Differenzen)
        eng_flux = float(np.maximum(0.0, spec - self._prev_mag).sum())
        self._prev_mag = spec

        # Historien aktualisieren
        self._hfc_history.append(hfc_flux)
        self._eng_history.append(eng_flux)
        self._hfc_max_window.append(hfc_flux)
        self._eng_max_window.append(eng_flux)

        if len(self._hfc_history) < 5:
            return None

        # Adaptive Schwellen MIT Untergrenze
        hfc_med = float(np.median(self._hfc_history))
        eng_med = float(np.median(self._eng_history))
        hfc_floor = max(self._hfc_max_window) * self.FLOOR_FRACTION
        eng_floor = max(self._eng_max_window) * self.FLOOR_FRACTION
        hfc_thresh = max(hfc_med * self.THRESHOLD_FACTOR, hfc_floor, 1e-6)
        eng_thresh = max(eng_med * self.THRESHOLD_FACTOR, eng_floor, 1e-6)

        # ODER-Trigger: entweder hoher HFC- oder hoher Energie-Sprung
        triggered = (hfc_flux > hfc_thresh) or (eng_flux > eng_thresh)
        if triggered and (block_start_t - self._last_onset_t) > self.MIN_INTERVAL_S:
            self._last_onset_t = block_start_t
            return block_start_t + self._block_dur / 2
        return None


# ────────────────────────────────────────────────────────────────────────
#  Metronom-Zustand
# ────────────────────────────────────────────────────────────────────────
@dataclass
class Metronome:
    bpm: float = 120.0
    beats_per_bar: int = 4
    start_time: float = 0.0
    running: bool = False

    @property
    def beat_interval(self) -> float:
        return 60.0 / self.bpm

    def expected_beat_time(self, index: int) -> float:
        return self.start_time + index * self.beat_interval

    def nearest_expected(self, t: float) -> float:
        idx = round((t - self.start_time) / self.beat_interval)
        return self.expected_beat_time(int(idx))


# ────────────────────────────────────────────────────────────────────────
#  Auswertung
# ────────────────────────────────────────────────────────────────────────
class Analyzer:
    """Vergleicht erkannte Onsets mit erwarteten Klicks."""

    PHASE_HISTORY = 64
    BPM_WINDOW = 8

    def __init__(self) -> None:
        self.phase_dev_ms: deque[tuple[float, float]] = deque(maxlen=self.PHASE_HISTORY)
        self.onsets: deque[float] = deque(maxlen=self.BPM_WINDOW + 1)
        self.measured_bpm: float | None = None

    def add_onset(self, t: float, metro: Metronome) -> tuple[float, float | None]:
        dev_ms = (t - metro.nearest_expected(t)) * 1000.0
        self.phase_dev_ms.append((t, dev_ms))
        self.onsets.append(t)
        if len(self.onsets) >= 2:
            intervals = np.diff(np.array(self.onsets))
            self.measured_bpm = 60.0 / float(np.mean(intervals))
        return dev_ms, self.measured_bpm

    @staticmethod
    def zone(dev_ms: float) -> str:
        a = abs(dev_ms)
        if a <= 10:
            return "GRN"
        if a <= 25:
            return "GLB"
        return "ROT"


# ────────────────────────────────────────────────────────────────────────
#  Beat-Tracker (Autokorrelation der Onset-Sequenz)
# ────────────────────────────────────────────────────────────────────────
class BeatTracker:
    """Schätzt das Tempo per Autokorrelation der Onset-Folge.

    Robust gegen polyrhythmische Patterns (z.B. Funk-Beat: Hi-Hat-Viertel
    plus synkopierte Kick/Snare-Schläge). Die Autokorrelation findet die
    periodische Struktur der ganzen Sequenz, unabhängig davon ob auch
    zwischen den Schlägen gespielt wird.

    Algorithmus:
    1. Onsets als Sparse-Signal in Zeitbins (10 ms Auflösung) ablegen.
    2. FFT-basierte Autokorrelation berechnen.
    3. Im Tempo-Bereich Soll ±30 % nach dem Peak suchen.
    4. Gauss-Gewichtung um Soll-Periode verhindert Lock auf
       Halb-/Doppel-Tempo bei mehrdeutigen Mustern.
    """

    BIN_SIZE_S = 0.010
    WINDOW_S = 6.0          # historischer Puffer für die Schätzung
    TEMPO_SEARCH_PCT = 0.30
    MIN_ONSETS = 4

    def __init__(self, target_bpm: float):
        self.target_bpm = target_bpm
        self.target_period = 60.0 / target_bpm
        self._target_bin = int(self.target_period / self.BIN_SIZE_S)
        self._lo = int(self.target_period * (1 - self.TEMPO_SEARCH_PCT) / self.BIN_SIZE_S)
        self._hi = int(self.target_period * (1 + self.TEMPO_SEARCH_PCT) / self.BIN_SIZE_S)
        # Gauss-Breite: ein Viertel des Suchbereichs, gleichmäßiger Abfall
        self._sigma = max(1.0, (self._hi - self._lo) / 4.0)
        self.onsets: deque[float] = deque()

    def add(self, t: float) -> float | None:
        self.onsets.append(t)
        cutoff = t - self.WINDOW_S
        while self.onsets and self.onsets[0] < cutoff:
            self.onsets.popleft()
        if len(self.onsets) < self.MIN_ONSETS:
            return None
        return self._estimate()

    def _estimate(self) -> float | None:
        t0 = self.onsets[0]
        n_bins = int((self.onsets[-1] - t0) / self.BIN_SIZE_S) + 1
        if n_bins <= self._hi * 2:
            return None  # zu wenig Daten für stabile Autokorrelation
        signal = np.zeros(n_bins, dtype=np.float32)
        for t in self.onsets:
            idx = int((t - t0) / self.BIN_SIZE_S)
            if 0 <= idx < n_bins:
                signal[idx] = 1.0
        # FFT-basierte Autokorrelation
        n_fft = 1 << (2 * signal.size - 1).bit_length()
        spec = np.fft.rfft(signal, n=n_fft)
        ac = np.fft.irfft(spec * np.conj(spec))[:signal.size].real
        # Gauss-gewichtete Argmax-Suche im Tempo-Fenster
        lo = max(1, self._lo)
        hi = min(len(ac), self._hi)
        if hi <= lo:
            return None
        bins = np.arange(lo, hi)
        weights = np.exp(-0.5 * ((bins - self._target_bin) / self._sigma) ** 2)
        weighted = ac[lo:hi] * weights
        peak = lo + int(np.argmax(weighted))
        period = peak * self.BIN_SIZE_S
        return 60.0 / period


# ────────────────────────────────────────────────────────────────────────
#  Live-Visualisierung (matplotlib)
# ────────────────────────────────────────────────────────────────────────
class LivePlot:
    """Scrollender Live-Plot der implizierten BPM über die letzten N Takte.

    - X-Achse: Zeit in s, sliding window (4 Takte breit)
    - Y-Achse: BPM, Soll ±20
    - Soll-Linie: gestrichelt weiß
    - Ist-Linie: cyan, mit Punkten an jedem Onset
    - Hintergrund: dunkelgrün/rot/blau je nach gleitendem Mittel
    """

    BAR_WINDOW = 4
    BPM_TOLERANCE = 2.0
    Y_HALF_RANGE = 20.0
    SMOOTH_N = 8

    def __init__(self, target_bpm: float, beats_per_bar: int) -> None:
        self.target_bpm = target_bpm
        self.beats_per_bar = beats_per_bar
        self.window_s = self.BAR_WINDOW * beats_per_bar * 60.0 / target_bpm
        self.lock = threading.Lock()
        self.data: list[tuple[float, float]] = []

    def push(self, t: float, bpm: float) -> None:
        with self.lock:
            self.data.append((t, bpm))
            cutoff = t - self.window_s * 1.5
            self.data = [(tt, bb) for tt, bb in self.data if tt > cutoff]

    def show(self) -> None:
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(11, 5.5))
        fig.canvas.manager.set_window_title(f"Taktwerk — Soll {self.target_bpm:g} BPM")

        ax.axhline(self.target_bpm, color="white", lw=1.5, ls="--",
                   alpha=0.7, label=f"Soll {self.target_bpm:g} BPM")
        (line,) = ax.plot([], [], "o-", color="#7adbff", lw=2.5, ms=6, label="Ist (impl.)")
        bpm_text = ax.text(0.02, 0.95, "", transform=ax.transAxes,
                           fontsize=28, color="white", va="top",
                           fontfamily="monospace", weight="bold")

        ax.set_xlabel("Zeit (s, gleitend)")
        ax.set_ylabel("BPM")
        ax.set_ylim(self.target_bpm - self.Y_HALF_RANGE,
                    self.target_bpm + self.Y_HALF_RANGE)
        ax.set_xlim(-self.window_s, 0)
        ax.grid(alpha=0.2)
        ax.legend(loc="upper right")

        def update(_frame):
            now = time.monotonic()
            with self.lock:
                points = list(self.data)
            if not points:
                bpm_text.set_text("warte auf Onsets…")
                return line, bpm_text
            xs = [t - now for t, _ in points]
            ys = [b for _, b in points]
            line.set_data(xs, ys)
            # nur die im Sichtfenster für Hintergrund-Mittel berücksichtigen
            visible = [b for t, b in points if (now - t) < self.window_s]
            if visible:
                avg = sum(visible[-self.SMOOTH_N:]) / min(len(visible), self.SMOOTH_N)
                delta = avg - self.target_bpm
                if abs(delta) < self.BPM_TOLERANCE:
                    bg, fg, label = "#0d2818", "#80ff80", "im Tempo"
                elif delta > 0:
                    bg, fg, label = "#281818", "#ff8080", "zu schnell"
                else:
                    bg, fg, label = "#0d1828", "#80a0ff", "zu langsam"
                ax.set_facecolor(bg)
                bpm_text.set_text(f"{avg:5.1f} BPM\nΔ {delta:+5.1f}  {label}")
                bpm_text.set_color(fg)
            return line, bpm_text

        # Animation an Figure binden, damit sie nicht garbage-collected wird
        self._anim = FuncAnimation(fig, update, interval=150,
                                   blit=False, cache_frame_data=False)
        plt.tight_layout()
        plt.show()


# ────────────────────────────────────────────────────────────────────────
#  Klick + LED
# ────────────────────────────────────────────────────────────────────────
class ClickPlayer:
    """Erzeugt den hörbaren Klick und blinkt die Front-LED.

    Auf dem Pi: GPIO 17 schaltet via MOSFET die weiße LED.
    Auf dev: nur Audio-Klick, kein GPIO.
    """

    LED_PIN = 17

    def __init__(self):
        self.sr = SAMPLE_RATE
        self.click_normal = self._make_click(freq=1200, dur_ms=15, gain=0.5)
        self.click_accent = self._make_click(freq=1800, dur_ms=25, gain=0.7)
        self.led = None
        if ON_PI:
            try:
                from gpiozero import LED  # type: ignore
                self.led = LED(self.LED_PIN)
            except Exception as e:
                print(f"[warn] LED nicht initialisiert: {e}", file=sys.stderr)

    def _make_click(self, freq: int, dur_ms: int, gain: float) -> np.ndarray:
        n = int(self.sr * dur_ms / 1000)
        t = np.arange(n) / self.sr
        env = np.exp(-t * 80)
        return (gain * np.sin(2 * np.pi * freq * t) * env).astype(np.float32)

    def play(self, accent: bool = False) -> None:
        wave = self.click_accent if accent else self.click_normal
        # blocking=False → kommt sofort zurück, Klick spielt im Hintergrund
        sd.play(wave, self.sr, blocking=False)
        if self.led is not None:
            self.led.on()
            threading.Timer(0.06 if accent else 0.03, self.led.off).start()


# ────────────────────────────────────────────────────────────────────────
#  Hauptschleife
# ────────────────────────────────────────────────────────────────────────
def run(target_bpm: float, beats_per_bar: int, latency_ms: float = 0.0,
        no_click: bool = False, listen: bool = False, gui: bool = False,
        subdivision: float | None = None, record_file: str | None = None) -> None:
    metro = Metronome(bpm=target_bpm, beats_per_bar=beats_per_bar)
    analyzer = Analyzer()
    detector = OnsetDetector(SAMPLE_RATE, BLOCK_SIZE)
    click = ClickPlayer() if not listen else None
    latency_s = latency_ms / 1000.0
    plot = LivePlot(target_bpm, beats_per_bar) if (listen and gui) else None

    metro.start_time = time.monotonic()
    metro.running = True

    # Listen-Modus: eigener Zustand, unabhängig vom Metronom
    listen_onsets: deque[float] = deque(maxlen=9)
    implied_bpms: deque[float] = deque(maxlen=8)
    onset_count = 0
    target_quarter_ms = 60000.0 / target_bpm  # Soll-Viertel-Dauer als Snap-Referenz

    DIVISIONS = (0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0)
    DIVISION_NAMES = {0.5: "1/2 ", 1.0: "1/4 ", 2.0: "1/8 ", 3.0: "1/8T",
                      4.0: "1/16", 6.0: "1/16T", 8.0: "1/32"}

    # Tempo-Schätzung: Autokorrelation über 6-s-Fenster (robust gegen
    # polyrhythmische Patterns). Fallback bei --subdivision: per-Onset.
    beat_tracker = BeatTracker(target_bpm) if subdivision is None else None
    last_division: float | None = None  # nur fürs Logging des Wechsels

    # Recording: alle Events sammeln, am Ende als JSON schreiben
    log_events: list[dict] = []
    t_start_wall = time.time()
    t_start_mono = time.monotonic()

    def add_event(etype: str, **data) -> None:
        if record_file is None:
            return
        log_events.append({"type": etype, "t": time.monotonic() - t_start_mono, **data})

    def audio_cb(indata, frames, _ts, status):
        nonlocal onset_count, last_division
        if status:
            print(f"[audio] {status}", file=sys.stderr)
        now = time.monotonic()
        block_start = now - frames / SAMPLE_RATE
        samples = indata[:, 0].astype(np.float32)
        onset_t = detector.process(samples, block_start)
        if onset_t is None or not metro.running:
            return
        onset_t -= latency_s

        if listen:
            onset_count += 1
            listen_onsets.append(onset_t)
            last_dt_ms = ((listen_onsets[-1] - listen_onsets[-2]) * 1000.0
                          if len(listen_onsets) >= 2 else None)

            # Tempo schätzen: BeatTracker (default) oder fixe Subdivision
            if beat_tracker is not None:
                bpm = beat_tracker.add(onset_t)
            elif last_dt_ms is not None:
                bpm = 60000.0 / (last_dt_ms * subdivision)
            else:
                bpm = None

            add_event("onset", n=onset_count, onset_t=onset_t,
                      dt_ms=last_dt_ms, bpm=bpm,
                      buffer_size=len(beat_tracker.onsets) if beat_tracker else 0)

            if bpm is None:
                if plot is None:
                    print(f"#{onset_count:3d} | warming up "
                          f"({len(listen_onsets)} Onsets, brauche min. 4 + 1 s)")
                return

            implied_bpms.append(bpm)
            smoothed = float(np.mean(implied_bpms))

            # Beobachtete Unterteilung (rein informativ) aus period / dt
            if last_dt_ms is not None:
                period_ms = 60000.0 / bpm
                ratio = period_ms / last_dt_ms
                division = min(DIVISIONS, key=lambda v: abs(v - ratio))
                if division != last_division:
                    if last_division is not None:
                        print(f"[switch] Unterteilung: "
                              f"{DIVISION_NAMES[last_division]} → "
                              f"{DIVISION_NAMES[division]}")
                    last_division = division

            if plot is not None:
                plot.push(onset_t, smoothed)
            else:
                name = DIVISION_NAMES[last_division] if last_division else "----"
                arrow = "→" if abs(smoothed - target_bpm) < 1 else (
                        "↑" if smoothed > target_bpm else "↓")
                print(f"#{onset_count:3d} | dt {last_dt_ms or 0:6.1f} ms | {name} "
                      f"| BPM {bpm:6.1f} | Mittel {smoothed:6.1f} {arrow} "
                      f"Soll {target_bpm:g}")
            return

        dev_ms, ist_bpm = analyzer.add_onset(onset_t, metro)
        soll = metro.bpm
        ist_str = f"{ist_bpm:5.1f}" if ist_bpm is not None else "  -  "
        print(f"Soll {soll:5.1f} | Ist {ist_str} | "
              f"Δ {dev_ms:+6.1f} ms [{analyzer.zone(dev_ms)}]")

    def scheduler():
        next_beat = 0
        while metro.running:
            t_target = metro.expected_beat_time(next_beat)
            sleep_for = t_target - time.monotonic()
            if sleep_for > 0:
                time.sleep(sleep_for)
            accent = (next_beat % metro.beats_per_bar == 0)
            if not no_click and click is not None:
                click.play(accent=accent)
            next_beat += 1

    platform_name = "Raspberry Pi" if ON_PI else "dev (Mac/Linux)"
    print("─" * 60)
    print(f" Taktwerk — Drum Tempo Monitor")
    if listen:
        print(f" Modus: LISTEN — Soll {target_bpm:g} BPM als Snap-Referenz "
              f"für Unterteilungen (½, ¼, ⅛, Trio, 1/16, 1/16T, 1/32)")
    else:
        print(f" Soll: {target_bpm:g} BPM, {beats_per_bar}/4")
    print(f" Detector: HFC spectral flux | Platform: {platform_name}")
    print(" Stop mit Ctrl-C")
    print("─" * 60)

    if not listen:
        threading.Thread(target=scheduler, daemon=True).start()

    add_event("start", target_bpm=target_bpm, beats_per_bar=beats_per_bar,
              sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE,
              listen=listen, subdivision=subdivision)
    try:
        with sd.InputStream(channels=1, samplerate=SAMPLE_RATE,
                            blocksize=BLOCK_SIZE, callback=audio_cb):
            if plot is not None:
                plot.show()           # blockiert bis Fenster geschlossen
            else:
                while metro.running:
                    time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        metro.running = False
        add_event("stop", total_onsets=onset_count)
        if record_file:
            with open(record_file, "w") as f:
                json.dump({
                    "session": {
                        "target_bpm": target_bpm,
                        "beats_per_bar": beats_per_bar,
                        "sample_rate": SAMPLE_RATE,
                        "block_size": BLOCK_SIZE,
                        "subdivision": subdivision,
                        "platform": platform.platform(),
                        "wall_start": t_start_wall,
                    },
                    "log": log_events,
                }, f, indent=2)
            print(f"\n[record] {len(log_events)} Events → {record_file}")
        print("\nstopped.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Taktwerk — Drum Tempo Monitor")
    ap.add_argument("--bpm", type=float, default=120.0, help="Soll-Tempo in BPM")
    ap.add_argument("--meter", type=int, default=4, help="Schläge pro Takt")
    ap.add_argument("--latency-ms", type=float, default=0.0,
                    help="Audio-Pfad-Latenz in ms (Mac: ~150; Pi I²S: ~12)")
    ap.add_argument("--no-click", action="store_true",
                    help="Klick-Audio aus (Scheduler läuft weiter), für externe Audioquelle")
    ap.add_argument("--listen", action="store_true",
                    help="Listen-Modus: nur Tempo messen, kein Metronom, keine Soll-Vorgabe")
    ap.add_argument("--gui", action="store_true",
                    help="Live-Plot (matplotlib) statt Konsolen-Ausgabe — nur mit --listen")
    ap.add_argument("--subdivision", type=float, default=None,
                    choices=[0.5, 1, 2, 3, 4, 6, 8],
                    help="Unterteilung fest vorgeben (1=Viertel, 2=Achtel, 3=Triole, "
                         "4=Sechzehntel, 6=16tel-Triole, 8=32stel). "
                         "Sonst wird automatisch nach 4 Onsets gelockt.")
    ap.add_argument("--record", type=str, default=None, metavar="FILE",
                    help="Alle Onsets/Events in JSON-Datei aufzeichnen (für Debugging)")
    args = ap.parse_args()
    run(args.bpm, args.meter, args.latency_ms, args.no_click,
        args.listen, args.gui, args.subdivision, args.record)


if __name__ == "__main__":
    main()


# ────────────────────────────────────────────────────────────────────────
#  TODO für die Pi-Version (in eigene Module auslagern)
# ────────────────────────────────────────────────────────────────────────
#  ui/display.py    Pillow-Rendering auf ST7789 via luma.lcd
#                   - Header: Soll/Ist-BPM, Taktart, Beat-Indikator
#                   - Phase-Scatter (deque analyzer.phase_dev_ms)
#                   - Tempo-Verlauf (Ringpuffer der Ist-BPM)
#
#  ui/controls.py   gpiozero RotaryEncoder + Button
#                   - Encoder dreht BPM (mit Drehbeschleunigung)
#                   - Encoder-Druck wechselt Fokus BPM↔Taktart
#                   - Button 1: Tap-Tempo (4 Taps → BPM)
#                   - Button 2: Start/Stop
#
#  config.py        Persistenz der letzten Einstellung in ~/.taktwerk.json
#
#  calibration.py   Einmal-Kalibrierung der I²S-Latenz (konstanter Offset
#                   wird vom gemessenen Onset-Zeitstempel abgezogen)
