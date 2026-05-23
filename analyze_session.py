"""Korreliert session.json mit test-protocol.json.

Findet den Offset zwischen Script-Zeit und WAV-Zeit automatisch via
Cross-Correlation: testet eine Reihe möglicher Offsets und wählt den,
bei dem die meisten erkannten Onsets nahe an einem erwarteten Schlag
liegen.
"""
import json
import numpy as np

with open("session.json") as f:
    session = json.load(f)
with open("test-protocol.json") as f:
    proto = json.load(f)

onsets = [e for e in session["log"] if e["type"] == "onset"]
t_script = np.array([o["t"] for o in onsets])
bpms = np.array([o["bpm"] if o["bpm"] is not None else np.nan for o in onsets])
dts = np.array([o["dt_ms"] if o["dt_ms"] is not None else np.nan for o in onsets])

print(f"=== Übersicht ===")
print(f"Onsets total: {len(onsets)}")
print(f"Script-Zeit-Spanne: {t_script[0]:.2f} – {t_script[-1]:.2f} s\n")

# ─── Erwartete Onset-Zeiten aus dem Test-Protokoll generieren ───────
expected_hits = []  # Liste von (label, t_wav)
target_bpm = 100
for seg in proto["segments"]:
    label = seg["label"]
    s, e = seg["start_s"], seg["end_s"]
    interval = None
    if "100 BPM Viertel" in label:        interval = 0.6
    elif "Snare 100" in label:            interval = 0.3
    elif "16tel" in label:                interval = 0.15
    elif "80 BPM Viertel" in label:       interval = 0.75
    elif "120 BPM Viertel" in label:      interval = 0.5
    elif "Funk 100" in label:             interval = 0.15  # HH 8tel + Synkopen ≈ alle ~150 ms ein Onset
    elif "Funk 110" in label:             interval = 60.0 / 110 / 4
    if interval is None:
        continue
    t = s
    while t < e - 0.01:
        expected_hits.append((label, t))
        t += interval
expected_t = np.array([h[1] for h in expected_hits])
print(f"Erwartete Onsets aus Protokoll: {len(expected_t)}")

# ─── Optimalen Offset durch Suche finden ───────────────────────────
def matches(offset, tol_s=0.080):
    """Wie viele erkannte Onsets liegen innerhalb ±tol einer erwarteten Zeit?"""
    if len(t_script) == 0 or len(expected_t) == 0: return 0
    t_wav = t_script - offset
    # Für jeden erkannten Onset: gibt es einen erwarteten in der Nähe?
    diffs = np.abs(t_wav[:, None] - expected_t[None, :]).min(axis=1)
    return int((diffs < tol_s).sum())

offset_candidates = np.arange(0.0, 60.0, 0.05)
scores = [matches(o) for o in offset_candidates]
best_idx = int(np.argmax(scores))
offset = float(offset_candidates[best_idx])
print(f"\n=== Synchronisation (Cross-Correlation) ===")
print(f"Optimaler Offset: {offset:+.2f} s  (max Score: {scores[best_idx]}/{len(t_script)} Onsets passen)\n")

# WAV-Zeit
t_wav = t_script - offset

# ─── Pro Phase auswerten ────────────────────────────────────────────
print(f"=== Phasen-Analyse ===\n")
fmt = "{:<42} {:>5} {:>5} {:>8} {:>11} {:>9}  {}"
print(fmt.format("Phase", "Soll", "Erk.", "BPM-Soll", "BPM-Median", "dt-Med", "Bewertung"))
print("-" * 120)

expected_map = {
    "00 Stille":     (0, None),
    "01 Kick 100":   (16, 100),
    "02 Stille":     (0, None),
    "03 Snare 100":  (32, 100),
    "04 Stille":     (0, None),
    "05 Hi-Hat 100": (64, 100),
    "06 Stille":     (0, None),
    "07 Kick 80":    (12, 80),
    "08 Stille":     (0, None),
    "09 Kick 120":   (20, 120),
    "10 Stille":     (0, None),
    "11 Funk 100":   (None, 100),
    "12 Stille":     (0, None),
    "13 Funk 110":   (None, 110),
    "14 Stille":     (0, None),
}

for seg in proto["segments"]:
    label = seg["label"]
    s, e = seg["start_s"], seg["end_s"]
    key = " ".join(label.split()[:3])
    expected_n, expected_bpm = expected_map.get(key, (None, None))

    in_phase = (t_wav >= s) & (t_wav < e)
    n_det = int(in_phase.sum())
    bpms_p = bpms[in_phase]
    dts_p = dts[in_phase]
    bpm_med = float(np.nanmedian(bpms_p)) if len(bpms_p) and not np.all(np.isnan(bpms_p)) else float("nan")
    dt_med = float(np.nanmedian(dts_p)) if len(dts_p) and not np.all(np.isnan(dts_p)) else float("nan")

    rating = ""
    if expected_n == 0:
        rating = "✓" if n_det == 0 else f"✗ {n_det} false"
    elif expected_n is not None:
        ratio = n_det / expected_n if expected_n else 0
        if 0.85 <= ratio <= 1.15: rating = "✓"
        elif ratio < 0.5: rating = "✗ viele verfehlt"
        elif ratio > 1.5: rating = "✗ Doppel-Trigger"
        else: rating = "△ teilweise"
    if expected_bpm and not np.isnan(bpm_med):
        if abs(bpm_med - expected_bpm) > 5:
            rating += " | BPM falsch"
        else:
            rating += " | BPM ✓"

    exp_n_str = str(expected_n) if expected_n is not None else "~24"
    bpm_soll = f"{expected_bpm}" if expected_bpm else "—"
    bpm_med_s = f"{bpm_med:.1f}" if not np.isnan(bpm_med) else "—"
    dt_med_s = f"{dt_med:.0f}" if not np.isnan(dt_med) else "—"
    print(fmt.format(label[:42], exp_n_str, n_det, bpm_soll, bpm_med_s, dt_med_s, rating))
