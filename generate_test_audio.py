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

def kick(amp: float = 0.75, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * 0.30)
    t = np.arange(n) / SR
    # Pitched Sweep: 200 Hz → 50 Hz exponentiell
    freq = 50.0 + 150.0 * np.exp(-t * 25)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    pitched = np.sin(phase) * np.exp(-t * 12)
    # Attack-Click (kurzer Rausch-Burst am Anfang)
    cn = int(SR * 0.004)
    click_env = np.exp(-np.arange(cn) / SR * 600)
    out = np.zeros(n, dtype=np.float32)
    out[:cn] += (rng.standard_normal(cn) * click_env * 0.4).astype(np.float32)
    out += pitched.astype(np.float32)
    return amp * out


def snare(amp: float = 0.55, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * 0.20)
    t = np.arange(n) / SR
    # Tonaler Körper (Snare-Fell)
    tone = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 25)
    # Snare-Buzz: hochpassgefiltertes Rauschen (per Differenzierung)
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0)        # erste Differenzierung
    noise_env = np.exp(-t * 18)
    return (amp * (tone.astype(np.float32) * 0.35
                   + noise.astype(np.float32) * noise_env.astype(np.float32) * 0.7))


def hihat(amp: float = 0.40, dur_s: float = 0.09,
          decay: float = 65, seed: int = 2) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * dur_s)
    t = np.arange(n) / SR
    # Sehr helles Rauschen: doppelt differenziert
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0)
    noise = np.diff(noise, prepend=0)
    env = np.exp(-t * decay)
    return (amp * noise.astype(np.float32) * env.astype(np.float32))


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SR), dtype=np.float32)


def add(target: np.ndarray, offset: int, signal: np.ndarray) -> None:
    """In-place Addition mit Bounds-Check."""
    end = min(offset + len(signal), len(target))
    target[offset:end] += signal[: end - offset]


# ─── Pattern-Generatoren ────────────────────────────────────────────────
def click_track(bpm: float, n_beats: int, hi_dur: float = 0.09) -> np.ndarray:
    """Hi-Hat-Klicks bei gegebenem Tempo — wie ein Drummer-Time-Keeper."""
    interval = 60.0 / bpm
    duration = int(n_beats * interval * SR) + int(SR * 0.5)
    out = np.zeros(duration, dtype=np.float32)
    # Verschiedene Seeds pro Hit → leicht unterschiedlich, klingt natürlicher
    for i in range(n_beats):
        hit = hihat(amp=0.42, dur_s=hi_dur, seed=100 + i)
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
add_segment("01 Hi-Hat 100 BPM Viertel (16 Schläge)",  click_track(100, 16))
add_segment("02 Stille",                               silence(3))
add_segment("03 Hi-Hat 100 BPM Achtel (32 Schläge)",   click_track(100, 32))
add_segment("04 Stille",                               silence(3))
add_segment("05 Hi-Hat 100 BPM 16tel (64 Schläge)",    click_track(100, 64, hi_dur=0.06))
add_segment("06 Stille",                               silence(3))
add_segment("07 Hi-Hat 80 BPM Viertel (12 Schläge)",   click_track(80, 12))
add_segment("08 Stille",                               silence(3))
add_segment("09 Hi-Hat 120 BPM Viertel (20 Schläge)",  click_track(120, 20))
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
