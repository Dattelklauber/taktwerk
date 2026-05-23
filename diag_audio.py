"""Audio-Diagnose: zeigt 30 Sekunden lang den Pegel des Default-Eingangs.

Nutzen: schnell feststellen ob das Mikrofon überhaupt Audio liefert.
"""
import sys
import time
import numpy as np
import sounddevice as sd

print("\nVerfügbare Audio-Eingänge:")
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        marker = " ← Default" if i == sd.default.device[0] else ""
        print(f"  [{i}] {d['name']}{marker}")
print()

print("Audio-Diagnose: 30 s lang Peak-Pegel alle 0,5 s.")
print("Spiele jetzt etwas am Mac ab (Apple Music, Klatschen, Sprechen).")
print("Wenn Peak konstant unter 0,01 bleibt → kein Audio kommt an.\n")
print(f"{'Zeit':>6s}  {'Peak':>6s}  {'Bar (0–1)':<60s}")
print("-" * 78)

state = {"peaks": []}

def cb(indata, frames, _t, status):
    if status:
        print(f"[status: {status}]", file=sys.stderr)
    samples = indata[:, 0]
    state["peaks"].append((time.time(), float(np.abs(samples).max())))

try:
    with sd.InputStream(channels=1, samplerate=44100, blocksize=512, callback=cb):
        start = time.time()
        while time.time() - start < 30:
            time.sleep(0.5)
            now = time.time()
            recent = [p for t, p in state["peaks"] if t > now - 0.5]
            max_peak = max(recent) if recent else 0.0
            bar_len = int(max_peak * 60)
            bar = "█" * bar_len
            color = "" if max_peak > 0.01 else " (sehr leise!)"
            print(f"{now-start:6.1f}  {max_peak:6.3f}  {bar:<60s}{color}")
except KeyboardInterrupt:
    pass

# Zusammenfassung
peaks_all = [p for _, p in state["peaks"]]
if peaks_all:
    print(f"\n=== Zusammenfassung ===")
    print(f"  Min:    {min(peaks_all):.4f}")
    print(f"  Median: {sorted(peaks_all)[len(peaks_all)//2]:.4f}")
    print(f"  Max:    {max(peaks_all):.4f}")
    if max(peaks_all) < 0.01:
        print(f"\n  ✗ Kein Audio. Default-Eingang scheint stumm zu sein.")
    elif max(peaks_all) < 0.1:
        print(f"\n  △ Sehr leise. Mac-Eingangspegel höher stellen.")
    else:
        print(f"\n  ✓ Audio kommt an. Wenn Onset-Detection trotzdem nicht funktioniert,")
        print(f"    ist es ein anderes Problem.")
