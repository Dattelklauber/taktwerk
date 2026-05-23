"""Korreliert session.json mit test-protocol.json — diagnostische Analyse."""
import json
import numpy as np

with open("session.json") as f:
    session = json.load(f)
with open("test-protocol.json") as f:
    proto = json.load(f)

onsets = [e for e in session["log"] if e["type"] == "onset"]
# event["t"] ist Skript-relativ (seit Script-Start). Verwende das.
t_script = np.array([o["t"] for o in onsets])
bpms = np.array([o["bpm"] if o["bpm"] is not None else np.nan for o in onsets])
dts  = np.array([o["dt_ms"] if o["dt_ms"] is not None else np.nan for o in onsets])

print(f"=== Übersicht ===")
print(f"Erste Onset (Script-Zeit):  {t_script[0]:6.2f} s")
print(f"Letzte Onset:               {t_script[-1]:6.2f} s")
print(f"Spanne:                     {t_script[-1] - t_script[0]:6.2f} s")
print(f"Anzahl Onsets:              {len(onsets)}\n")

# Such-Heuristik: erste 16 Onsets sollten Phase 01 (Kick Viertel, 600 ms Abstand) sein.
# Daraus den Offset zwischen Script-Zeit und WAV-Zeit ableiten.
# Methode: Median der dt der ersten 15 Onsets sollte ~600 ms sein.
first_dts = dts[1:16]
print(f"=== Synchronisation (erste 15 Inter-Onset-Intervalle) ===")
print(f"Median dt: {np.nanmedian(first_dts):.1f} ms  (Soll: 600 ms für Kick-Viertel)")
print(f"Werte: {[round(float(d), 0) for d in first_dts if not np.isnan(d)]}\n")

# Offset bestimmen: Onset #1 sollte bei WAV-Zeit ~5.0 sein (Anfang Phase 01)
offset = t_script[0] - proto["segments"][1]["start_s"]
print(f"Berechneter Offset (Script t=0 → WAV t={-offset:.2f}): {offset:+.2f} s")
print(f"  → positiv: Script lief vor WAV-Play\n")

# WAV-Zeiten
t_wav = t_script - offset

# Pro Phase auswerten
print(f"=== Phasen-Analyse ===\n")
fmt = "{:<42} {:>8} {:>8} {:>10} {:>11} {:>10}  {}"
print(fmt.format("Phase", "Soll", "Erkannt", "Soll-BPM", "BPM-Median", "dt-Median", "Bewertung"))
print("-" * 120)

# Mapping Phase → erwartete Onset-Anzahl + musikalisch korrekte BPM
expected_map = {
    "00 Stille":        (0, None, None),
    "01 Kick 100":      (16, 100, 600),
    "02 Stille":        (0, None, None),
    "03 Snare 100":     (32, 100, 300),
    "04 Stille":        (0, None, None),
    "05 Hi-Hat 100":    (64, 100, 150),
    "06 Stille":        (0, None, None),
    "07 Kick 80":       (12, 80,  750),
    "08 Stille":        (0, None, None),
    "09 Kick 120":      (20, 120, 500),
    "10 Stille":        (0, None, None),
    "11 Funk 100":      (None, 100, None),  # Anzahl variiert da überlappende Hits
    "12 Stille":        (0, None, None),
    "13 Funk 110":      (None, 110, None),
    "14 Stille":        (0, None, None),
}

for seg in proto["segments"]:
    label = seg["label"]
    s, e = seg["start_s"], seg["end_s"]
    key = " ".join(label.split()[:3])  # erste 3 Tokens als Key
    expected_n, expected_bpm, expected_dt = expected_map.get(key, (None, None, None))

    in_phase = (t_wav >= s) & (t_wav < e)
    n_det = int(in_phase.sum())
    bpms_p = bpms[in_phase]
    dts_p  = dts[in_phase]
    bpm_med = float(np.nanmedian(bpms_p)) if len(bpms_p) else float("nan")
    dt_med  = float(np.nanmedian(dts_p))  if len(dts_p)  else float("nan")

    # Bewertung
    rating = ""
    if expected_n == 0:
        rating = "✓" if n_det == 0 else f"✗ {n_det} Falsch-Auslöser"
    elif expected_n is not None:
        ratio = n_det / expected_n if expected_n else 0
        if 0.85 <= ratio <= 1.15:
            rating = "✓"
        elif ratio < 0.5:
            rating = "✗ viele verfehlt"
        elif ratio > 1.5:
            rating = "✗ Doppel-Trigger"
        else:
            rating = "△ teilweise verfehlt"
    if expected_bpm and not np.isnan(bpm_med):
        if abs(bpm_med - expected_bpm) > 5:
            rating += " | BPM falsch"

    exp_n_str = str(expected_n) if expected_n is not None else "~24?"
    bpm_soll  = f"{expected_bpm}" if expected_bpm else "—"
    bpm_med_s = f"{bpm_med:.1f}" if not np.isnan(bpm_med) else "—"
    dt_med_s  = f"{dt_med:.0f}"   if not np.isnan(dt_med)  else "—"
    print(fmt.format(label[:42], exp_n_str, n_det, bpm_soll, bpm_med_s, dt_med_s, rating))
