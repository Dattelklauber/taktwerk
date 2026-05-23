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


# ─── Klang-Synthese ──────────────────────────────────────────────────────
def drumhit(dur_ms: float, amp: float, brightness: float, decay: float,
            seed: int = 0) -> np.ndarray:
    """Drum-artiger Transient: gefilterte Rauschspitze mit Sinus-Anteil.

    Breitbandiger Spektral-Anteil → triggert den HFC-Onset-Detektor
    zuverlässig (anders als reine Sinuswellen)."""
    rng = np.random.default_rng(seed)
    n = int(SR * dur_ms / 1000)
    t = np.arange(n) / SR
    env = np.exp(-t * decay)
    noise = rng.standard_normal(n) * 0.5
    tone1 = np.sin(2 * np.pi * brightness * t) * 0.3
    tone2 = np.sin(2 * np.pi * (brightness / 2) * t) * 0.2
    return (amp * (noise + tone1 + tone2) * env).astype(np.float32)


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SR), dtype=np.float32)


def add(target: np.ndarray, offset: int, signal: np.ndarray) -> None:
    """In-place Addition mit Bounds-Check."""
    end = min(offset + len(signal), len(target))
    target[offset:end] += signal[: end - offset]


# ─── Pattern-Generatoren ────────────────────────────────────────────────
def click_track(bpm: float, n_beats: int, brightness: float = 2000) -> np.ndarray:
    interval = 60.0 / bpm
    duration = int(n_beats * interval * SR) + int(SR * 0.5)  # +Decay-Tail
    out = np.zeros(duration, dtype=np.float32)
    hit = drumhit(dur_ms=18, amp=0.5, brightness=brightness, decay=80)
    for i in range(n_beats):
        add(out, int(i * interval * SR), hit)
    return out[: int(n_beats * interval * SR)]


def funk(bpm: float, n_bars: int) -> np.ndarray:
    """4/4 Funk-Pattern: Kick 1+3, Snare 2+4, Hi-Hat durchgehende Achtel."""
    bar_s = 4 * 60.0 / bpm
    eighth = bar_s / 8
    duration = int(bar_s * n_bars * SR) + int(SR * 0.5)
    out = np.zeros(duration, dtype=np.float32)
    kick = drumhit(dur_ms=50, amp=0.7, brightness=200,  decay=40, seed=1)
    snare = drumhit(dur_ms=35, amp=0.6, brightness=800,  decay=60, seed=2)
    hh = drumhit(dur_ms=18, amp=0.35, brightness=5000, decay=120, seed=3)
    for bar in range(n_bars):
        bar_start_s = bar * bar_s
        # Hi-Hat auf jedem Achtel
        for i in range(8):
            add(out, int((bar_start_s + i * eighth) * SR), hh)
        # Kick auf Schlag 1 und 3
        for beat in [0, 2]:
            add(out, int((bar_start_s + beat * 60.0 / bpm) * SR), kick)
        # Snare auf Schlag 2 und 4
        for beat in [1, 3]:
            add(out, int((bar_start_s + beat * 60.0 / bpm) * SR), snare)
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
add_segment("01 Klicks 100 BPM Viertel (16 Schläge)",  click_track(100, 16))
add_segment("02 Stille",                               silence(3))
add_segment("03 Klicks 100 BPM Achtel (32 Schläge)",   click_track(100, 32, brightness=1500))
add_segment("04 Stille",                               silence(3))
add_segment("05 Klicks 100 BPM 16tel (64 Schläge)",    click_track(100, 64, brightness=1200))
add_segment("06 Stille",                               silence(3))
add_segment("07 Klicks 80 BPM Viertel (12 Schläge)",   click_track(80, 12))
add_segment("08 Stille",                               silence(3))
add_segment("09 Klicks 120 BPM Viertel (20 Schläge)",  click_track(120, 20))
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
