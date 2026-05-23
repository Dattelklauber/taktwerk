"""Erzeugt eine WAV-Testdatei zur Validierung des Taktwerk-Algorithmus.

Die Datei enthält bekannte Click-Tracks und Drum-Patterns mit exakten
Zeitstempeln. Begleitende JSON-Datei beschreibt jede Phase. Den Log
des tempo_monitor.py-Laufs gegen diese Phasen kann man auswerten.

Nutzung:
    python generate_test_audio.py
    # -> test-protocol.wav, test-protocol.json
"""
from __future__ import annotations

import json
import wave
import numpy as np

SR = 44100


# ─── Schlagzeug-Synthese ────────────────────────────────────────────────
# Realistische Drum-Sounds via additive Synthese:
#  - Kick:  tonaler Sweep (200 → 50 Hz) + Attack-Click
#  - Snare: tonale 180 Hz + breitbandiges Snare-Buzz (hochpass-Rauschen)
#  - Hi-Hat: kurzer heller Rausch-Burst (mehrfach differenziertes Rauschen)

def kick(amp: float = 0.9, seed: int = 0) -> np.ndarray:
    """Bassdrum: kraftvoller Pitch-Sweep mit Click-Attack."""
    rng = np.random.default_rng(seed)
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    # Starker Pitched-Sweep: 250 Hz → 50 Hz exponentiell
    freq = 50.0 + 200.0 * np.exp(-t * 30)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * np.exp(-t * 10)
    # Druckvoller Attack-Click
    cn = int(SR * 0.006)
    click_env = np.exp(-np.arange(cn) / SR * 500)
    out = np.zeros(n, dtype=np.float32)
    out[:cn] += (rng.standard_normal(cn) * click_env * 0.6).astype(np.float32)
    out += body.astype(np.float32)
    return amp * out


def snare(amp: float = 0.75, seed: int = 1) -> np.ndarray:
    """Snare: harter Crack-Attack + tonal-Körper + Snare-Buzz."""
    rng = np.random.default_rng(seed)
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    # Tonaler Körper (Snare-Fell) — zwei Harmonische
    tone = (np.sin(2 * np.pi * 200 * t)
            + np.sin(2 * np.pi * 400 * t) * 0.5) * np.exp(-t * 30)
    # Snare-Buzz: hochpassgefiltertes Rauschen
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0)
    noise_env = np.exp(-t * 12)
    # Harter Crack am Anfang
    cn = int(SR * 0.005)
    crack = rng.standard_normal(cn) * np.exp(-np.arange(cn) / SR * 500) * 0.7
    out = np.zeros(n, dtype=np.float32)
    out[:cn] += crack.astype(np.float32)
    out += (tone * 0.35).astype(np.float32)
    out += (noise * noise_env * 0.7).astype(np.float32)
    return amp * out


def hihat(amp: float = 0.55, dur_s: float = 0.10, seed: int = 2) -> np.ndarray:
    """Closed Hi-Hat: heller Rausch-Burst mit Becken-Ringeln."""
    rng = np.random.default_rng(seed)
    n = int(SR * dur_s)
    t = np.arange(n) / SR
    # Helles Rauschen (einmal differenziert reicht — klingt natürlicher)
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0)
    # Leichte Becken-Ringel (tonale Komponente)
    ring = (np.sin(2 * np.pi * 8000 * t)
            + np.sin(2 * np.pi * 6500 * t) * 0.6
            + np.sin(2 * np.pi * 11000 * t) * 0.4)
    env = np.exp(-t * 50)
    return (amp * (noise.astype(np.float32) * 0.85
                   + ring.astype(np.float32) * 0.08) * env.astype(np.float32))


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SR), dtype=np.float32)


def add(target: np.ndarray, offset: int, signal: np.ndarray) -> None:
    """In-place Addition mit Bounds-Check."""
    end = min(offset + len(signal), len(target))
    target[offset:end] += signal[: end - offset]


# ─── Pattern-Generatoren ────────────────────────────────────────────────
def click_track(bpm: float, n_beats: int, sound: str = "hihat") -> np.ndarray:
    """Click-Track mit gewähltem Drum-Sound (kick / snare / hihat)."""
    interval = 60.0 / bpm
    duration = int(n_beats * interval * SR) + int(SR * 0.5)
    out = np.zeros(duration, dtype=np.float32)
    for i in range(n_beats):
        if sound == "kick":
            hit = kick(seed=100 + i)
        elif sound == "snare":
            hit = snare(seed=100 + i)
        else:
            hit = hihat(seed=100 + i)
        add(out, int(i * interval * SR), hit)
    return out[: int(n_beats * interval * SR)]


def funk(bpm: float, n_bars: int) -> np.ndarray:
    """4/4 Funk-Pattern: Kick 1+3, Snare 2+4, Hi-Hat durchgehende Achtel."""
    bar_s = 4 * 60.0 / bpm
    eighth = bar_s / 8
    duration = int(bar_s * n_bars * SR) + int(SR * 0.5)
    out = np.zeros(duration, dtype=np.float32)
    for bar in range(n_bars):
        bar_start_s = bar * bar_s
        # Hi-Hat auf jedem Achtel — variierender Seed → klingt nicht maschinell
        for i in range(8):
            add(out, int((bar_start_s + i * eighth) * SR),
                hihat(amp=0.35, seed=200 + bar * 8 + i))
        # Kick auf Schlag 1 und 3
        for beat in [0, 2]:
            add(out, int((bar_start_s + beat * 60.0 / bpm) * SR),
                kick(amp=0.8, seed=300 + bar * 2 + (beat // 2)))
        # Snare auf Schlag 2 und 4
        for beat in [1, 3]:
            add(out, int((bar_start_s + beat * 60.0 / bpm) * SR),
                snare(amp=0.6, seed=400 + bar * 2 + (beat // 2)))
    return out[: int(bar_s * n_bars * SR)]


# ─── Test-Protokoll zusammenstellen ─────────────────────────────────────
segments = []
parts = []
t_samples = 0


def add_segment(label: str, signal: np.ndarray) -> None:
    global t_samples
    segments.append({
        "label": label,
        "start_s": round(t_samples / SR, 3),
        "end_s": round((t_samples + len(signal)) / SR, 3),
        "duration_s": round(len(signal) / SR, 3),
    })
    parts.append(signal)
    t_samples += len(signal)


# Test-Phasen
add_segment("00 Stille (Baseline)",                    silence(5))
add_segment("01 Kick 100 BPM Viertel (16 Schläge)",    click_track(100, 16, "kick"))
add_segment("02 Stille",                               silence(3))
add_segment("03 Snare 100 BPM Achtel (32 Schläge)",    click_track(100, 32, "snare"))
add_segment("04 Stille",                               silence(3))
add_segment("05 Hi-Hat 100 BPM 16tel (64 Schläge)",    click_track(100, 64, "hihat"))
add_segment("06 Stille",                               silence(3))
add_segment("07 Kick 80 BPM Viertel (12 Schläge)",     click_track(80, 12, "kick"))
add_segment("08 Stille",                               silence(3))
add_segment("09 Kick 120 BPM Viertel (20 Schläge)",    click_track(120, 20, "kick"))
add_segment("10 Stille",                               silence(3))
add_segment("11 Funk 100 BPM (4 Takte)",               funk(100, 4))
add_segment("12 Stille",                               silence(3))
add_segment("13 Funk 110 BPM (4 Takte, Drift-Test)",   funk(110, 4))
add_segment("14 Stille (Outro)",                       silence(5))

# Zusammenfügen, normieren, als 16-bit WAV speichern
audio = np.concatenate(parts)
peak = float(np.abs(audio).max())
if peak > 0:
    audio = audio * (0.85 / peak)
audio_int = np.clip(audio * 32767, -32768, 32767).astype(np.int16)

WAV_PATH = "test-protocol.wav"
JSON_PATH = "test-protocol.json"

with wave.open(WAV_PATH, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(audio_int.tobytes())

with open(JSON_PATH, "w") as f:
    json.dump({
        "sample_rate": SR,
        "total_duration_s": round(len(audio) / SR, 3),
        "segments": segments,
    }, f, indent=2, ensure_ascii=False)

print(f"\n✓ {WAV_PATH}  ({len(audio)/SR:.1f} s, {len(audio_int)*2/1024:.0f} KB)")
print(f"✓ {JSON_PATH}\n")
print("Test-Phasen:")
for s in segments:
    print(f"  [{s['start_s']:6.1f} – {s['end_s']:6.1f}]  {s['label']}")
