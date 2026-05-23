"""Erzeugt ein Fritzing-ähnliches Verdrahtungs-Diagramm.

Ziel: stilisierte Bauteil-Darstellung mit farbcodierten Leitungen, klar
ablesbar welcher Pi-Pin an welchen Modul-Pin geht. Nicht photorealistisch,
aber deutlich anschaulicher als reine Schaltpläne.

Farbcode (Industriestandard):
    Rot      = 5 V
    Orange   = 3,3 V
    Schwarz  = GND
    Gelb     = Daten / Signal
    Blau     = SPI MOSI / Daten
    Grün     = SPI SCLK / Takt
    Violett  = I²S BCLK + LRCLK (gemeinsam)
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle

# ─── Farbpalette ─────────────────────────────────────────────────────────
COL_5V   = "#d92020"
COL_3V3  = "#ff8800"
COL_GND  = "#202020"
COL_SIG  = "#ddbb00"
COL_MOSI = "#1670c0"
COL_SCLK = "#1aa040"
COL_I2S  = "#8030c0"
COL_PCB_PI    = "#0d5a2a"   # Pi PCB dunkelgrün
COL_PCB_WHITE = "#f5f5f5"   # Breakouts oft weiß
COL_PCB_BLUE  = "#1a3a5c"   # Adafruit blau
COL_PCB_BLACK = "#1a1a1a"   # TFT
COL_PIN  = "#cba938"        # Gold Stiftleiste

# ─── Aufbau ──────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 10), dpi=200)
ax.set_xlim(0, 140); ax.set_ylim(0, 100); ax.axis('off')
ax.set_facecolor("#fafafa")

# ─── Helfer ──────────────────────────────────────────────────────────────
def board(x, y, w, h, color, label, sublabel="", text_color="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1",
                                 facecolor=color, edgecolor="#444",
                                 linewidth=1.5))
    ax.text(x + w/2, y + h - 2.5, label, ha="center", va="top",
            fontsize=10, fontweight="bold", color=text_color)
    if sublabel:
        ax.text(x + w/2, y + h - 5.5, sublabel, ha="center", va="top",
                fontsize=8, color=text_color, alpha=0.85)

def pin(x, y, label, side="left", color=COL_PIN, fontsize=7):
    ax.add_patch(Rectangle((x - 0.6, y - 0.6), 1.2, 1.2,
                            facecolor=color, edgecolor="#665010", linewidth=0.5))
    if side == "left":
        ax.text(x - 1.8, y, label, ha="right", va="center", fontsize=fontsize)
    elif side == "right":
        ax.text(x + 1.8, y, label, ha="left", va="center", fontsize=fontsize)
    elif side == "top":
        ax.text(x, y + 1.5, label, ha="center", va="bottom", fontsize=fontsize)
    elif side == "bottom":
        ax.text(x, y - 1.5, label, ha="center", va="top", fontsize=fontsize)

def wire(x1, y1, x2, y2, color, lw=1.8, mid_x=None):
    """Manhattan-Routing: vertikal-horizontal-vertikal über mid_x falls gegeben."""
    if mid_x is None:
        ax.plot([x1, x2], [y1, y2], color=color, lw=lw, solid_capstyle="round")
    else:
        ax.plot([x1, mid_x, mid_x, x2], [y1, y1, y2, y2],
                color=color, lw=lw, solid_capstyle="round")

# ─── Pi Zero 2 W mit 40-Pin Header ───────────────────────────────────────
PI_X, PI_Y, PI_W, PI_H = 45, 35, 50, 18
board(PI_X, PI_Y, PI_W, PI_H, COL_PCB_PI, "Raspberry Pi Zero 2 W",
      "40-Pin GPIO Header")

# Header: 2 Reihen × 20 Pins
# obere Reihe = ungerade Pins, untere = gerade
# Reale Lage: Pin 1 oben links bei der Ecke mit dem quadratischen Pad
header_x0 = PI_X + 2
header_y_top = PI_Y + PI_H - 9
header_y_bot = PI_Y + PI_H - 11.5
pin_spacing = (PI_W - 4) / 19

pi_pins = {}  # mapping pin_nr -> (x, y, side="up" or "down")
for i in range(20):
    px = header_x0 + i * pin_spacing
    pi_pins[2*i + 1] = (px, header_y_top, "up")   # ungerade Reihe = nach oben
    pi_pins[2*i + 2] = (px, header_y_bot, "down") # gerade Reihe = nach unten
    ax.add_patch(Rectangle((px - 0.6, header_y_top - 0.6), 1.2, 1.2,
                            facecolor=COL_PIN, edgecolor="#665010", lw=0.5))
    ax.add_patch(Rectangle((px - 0.6, header_y_bot - 0.6), 1.2, 1.2,
                            facecolor=COL_PIN, edgecolor="#665010", lw=0.5))

# Beschriftungen wichtiger Pins (klein, daneben/darunter)
key_labels = {
    1: "3V3", 2: "5V", 6: "GND", 8: "GPIO 14", 12: "GPIO 18\nBCLK",
    19: "GPIO 10\nMOSI", 23: "GPIO 11\nSCLK", 24: "GPIO 8\nCS",
    18: "GPIO 24\nDC", 22: "GPIO 25\nRST", 33: "GPIO 13\nBL",
    35: "GPIO 19\nLRCLK", 38: "GPIO 20\nDIN", 40: "GPIO 21\nDOUT",
    29: "GPIO 5", 31: "GPIO 6", 37: "GPIO 26",
    36: "GPIO 16", 32: "GPIO 12",
    11: "GPIO 17",
}
for p_nr, lbl in key_labels.items():
    px, py, side = pi_pins[p_nr]
    if side == "up":
        ax.text(px, py + 1.5, lbl, ha="center", va="bottom", fontsize=5.5)
    else:
        ax.text(px, py - 1.5, lbl, ha="center", va="top", fontsize=5.5)
    # Pin-Nummer in der Mitte
    ax.text(px, py, str(p_nr), ha="center", va="center", fontsize=4, color="#222")

# ─── Module rund um den Pi ───────────────────────────────────────────────

# SPH0645 Mikrofon (oben links, blaues Adafruit-Board)
MIC_X, MIC_Y, MIC_W, MIC_H = 5, 78, 22, 13
board(MIC_X, MIC_Y, MIC_W, MIC_H, COL_PCB_BLUE,
      "SPH0645", "I²S MEMS-Mikrofon")
# Mikrofon-Symbol (Kreis)
ax.add_patch(Circle((MIC_X + 4, MIC_Y + 7), 1.5, facecolor="#888", edgecolor="#444"))
ax.text(MIC_X + 4, MIC_Y + 4, "Mic", ha="center", fontsize=6, color="white")
# Pins unten
mic_pins = {"VDD": MIC_X + 9, "GND": MIC_X + 11.5, "BCLK": MIC_X + 14,
            "LRCL": MIC_X + 16.5, "DOUT": MIC_X + 19, "SEL": MIC_X + 21.5}
for label, x in mic_pins.items():
    pin(x, MIC_Y + 0.5, label, side="bottom", fontsize=5.5)

# MAX98357A Audio-Verstärker (oben rechts)
AMP_X, AMP_Y, AMP_W, AMP_H = 105, 78, 25, 13
board(AMP_X, AMP_Y, AMP_W, AMP_H, COL_PCB_BLUE,
      "MAX98357A", "I²S Class-D Amp")
amp_pins = {"VIN": AMP_X + 3, "GND": AMP_X + 6, "BCLK": AMP_X + 9,
            "LRC": AMP_X + 12, "DIN": AMP_X + 15, "GAIN": AMP_X + 18,
            "SPK+": AMP_X + 21, "SPK-": AMP_X + 24}
for label, x in amp_pins.items():
    pin(x, AMP_Y + 0.5, label, side="bottom", fontsize=5)

# Lautsprecher
SPK_X, SPK_Y = 121, 70
ax.add_patch(Circle((SPK_X, SPK_Y), 4, facecolor="#333", edgecolor="#000"))
ax.add_patch(Circle((SPK_X, SPK_Y), 2.5, facecolor="#555", edgecolor="#222"))
ax.add_patch(Circle((SPK_X, SPK_Y), 1, facecolor="#222"))
ax.text(SPK_X, SPK_Y - 6, "Lautsprecher\n4 Ω / 3 W", ha="center", fontsize=7)

# TFT-Display (rechts)
TFT_X, TFT_Y, TFT_W, TFT_H = 115, 35, 22, 25
board(TFT_X, TFT_Y, TFT_W, TFT_H, COL_PCB_BLACK,
      "TFT ST7789", "2.0″ 240×320")
# Display-Fläche
ax.add_patch(Rectangle((TFT_X + 3, TFT_Y + 9), TFT_W - 6, 12,
                        facecolor="#1a3a5c", edgecolor="#888"))
ax.text(TFT_X + TFT_W/2, TFT_Y + 15, "120 BPM", ha="center", color="white",
        fontsize=7, fontweight="bold")
ax.text(TFT_X + TFT_W/2, TFT_Y + 12, "± 0.5", ha="center", color="#7adbff",
        fontsize=6)
tft_pins = {"VCC": TFT_X + 2, "GND": TFT_X + 4.5, "MOSI": TFT_X + 7,
            "SCLK": TFT_X + 9.5, "CS": TFT_X + 12, "DC": TFT_X + 14.5,
            "RST": TFT_X + 17, "BL": TFT_X + 19.5}
for label, x in tft_pins.items():
    pin(x, TFT_Y + 0.5, label, side="bottom", fontsize=4.5)

# Encoder + Buttons (unten links)
ENC_X, ENC_Y, ENC_W, ENC_H = 3, 5, 22, 18
board(ENC_X, ENC_Y, ENC_W, ENC_H, COL_PCB_BLUE,
      "KY-040", "Rotary Encoder")
# Knopf-Symbol
ax.add_patch(Circle((ENC_X + 11, ENC_Y + 10), 3, facecolor="#888", edgecolor="#444"))
ax.add_patch(Circle((ENC_X + 11, ENC_Y + 10), 1.5, facecolor="#444"))
enc_pins = {"GND": ENC_X + 3, "+": ENC_X + 6, "SW": ENC_X + 12,
            "DT": ENC_X + 16, "CLK": ENC_X + 20}
for label, x in enc_pins.items():
    pin(x, ENC_Y + 0.5, label, side="bottom", fontsize=5.5)

# 2 Drucktaster (Mitte unten)
BTN_X = 35
ax.add_patch(Circle((BTN_X, 10), 3, facecolor="#222", edgecolor="#000"))
ax.add_patch(Circle((BTN_X, 10), 2, facecolor="#444"))
ax.text(BTN_X, 4, "Button 1\nTAP", ha="center", fontsize=7)
pin(BTN_X - 2, 5, "GND", side="bottom", fontsize=5)
pin(BTN_X + 2, 5, "GPIO 16", side="bottom", fontsize=5)

BTN2_X = 55
ax.add_patch(Circle((BTN2_X, 10), 3, facecolor="#622", edgecolor="#400"))
ax.add_patch(Circle((BTN2_X, 10), 2, facecolor="#844"))
ax.text(BTN2_X, 4, "Button 2\n▶ Start", ha="center", fontsize=7)
pin(BTN2_X - 2, 5, "GND", side="bottom", fontsize=5)
pin(BTN2_X + 2, 5, "GPIO 12", side="bottom", fontsize=5)

# LED + MOSFET (unten rechts)
LED_X, LED_Y = 80, 15
ax.add_patch(Circle((LED_X, LED_Y), 2, facecolor="#fff8aa", edgecolor="#aa7a00", linewidth=1.5))
ax.text(LED_X + 4, LED_Y + 1, "LED\n(weiß, hell)", fontsize=6)
ax.add_patch(Rectangle((LED_X + 12, LED_Y - 1), 4, 3,
                        facecolor="#666", edgecolor="#222"))
ax.text(LED_X + 14, LED_Y + 0.5, "2N7000", ha="center", fontsize=5,
        color="white", fontweight="bold")
ax.text(LED_X + 14, LED_Y - 3, "MOSFET", ha="center", fontsize=6)

# ─── Verkabelung ─────────────────────────────────────────────────────────
# I²S-Bus (BCLK + LRCLK gemeinsam zu Mic und Amp; DIN und DOUT separat)

# 3.3V: Pi Pin 1 → Mic VDD
px, py, _ = pi_pins[1]
wire(px, py + 0.8, MIC_X + 9, MIC_Y, COL_3V3, mid_x=MIC_X + 9)

# 3.3V: Pi Pin 1 → TFT VCC, Encoder +
wire(px, py + 0.8, TFT_X + 2, TFT_Y, COL_3V3, mid_x=PI_X + PI_W + 7)
wire(px, py + 0.8, ENC_X + 6, ENC_Y, COL_3V3, mid_x=PI_X - 8)

# 5V: Pi Pin 2 → Amp VIN
px, py, _ = pi_pins[2]
wire(px, py - 0.8, AMP_X + 3, AMP_Y, COL_5V, mid_x=AMP_X + 3)
# 5V → LED+ (via 100Ω; vereinfacht hier direkt)
wire(px, py - 0.8, LED_X - 5, LED_Y + 2, COL_5V, mid_x=LED_X - 5)
ax.text(LED_X - 4, LED_Y + 3.5, "100Ω", fontsize=5, color="#444")
ax.plot([LED_X - 5, LED_X - 2], [LED_Y + 2, LED_Y], color=COL_5V, lw=1.8)

# GND: Pi Pin 6 → Mic GND, Amp GND, TFT GND, Encoder GND, Button GNDs, MOSFET Source
px, py, _ = pi_pins[6]
gnd_targets = [
    (MIC_X + 11.5, MIC_Y, MIC_X + 11.5),
    (AMP_X + 6, AMP_Y, AMP_X + 6),
    (TFT_X + 4.5, TFT_Y, PI_X + PI_W + 5),
    (ENC_X + 3, ENC_Y, PI_X - 6),
    (BTN_X - 2, 5, BTN_X - 2),
    (BTN2_X - 2, 5, BTN2_X - 2),
]
for tx, ty, mx in gnd_targets:
    wire(px, py - 0.8, tx, ty, COL_GND, mid_x=mx)

# I²S BCLK (GPIO 18 / Pin 12) → Mic BCLK + Amp BCLK
px, py, _ = pi_pins[12]
wire(px, py + 0.8, MIC_X + 14, MIC_Y, COL_I2S, mid_x=MIC_X + 14)
wire(px, py + 0.8, AMP_X + 9, AMP_Y, COL_I2S, mid_x=AMP_X + 9)
# I²S LRCLK (GPIO 19 / Pin 35) → Mic LRCL + Amp LRC
px, py, _ = pi_pins[35]
wire(px, py - 0.8, MIC_X + 16.5, MIC_Y, COL_I2S, mid_x=20)
wire(px, py - 0.8, AMP_X + 12, AMP_Y, COL_I2S, mid_x=AMP_X + 12)
# I²S DIN (GPIO 20 / Pin 38) ← Mic DOUT
px, py, _ = pi_pins[38]
wire(px, py - 0.8, MIC_X + 19, MIC_Y, COL_SIG, mid_x=25)
# I²S DOUT (GPIO 21 / Pin 40) → Amp DIN
px, py, _ = pi_pins[40]
wire(px, py - 0.8, AMP_X + 15, AMP_Y, COL_SIG, mid_x=AMP_X + 15)

# SPI: MOSI (Pin 19) → TFT MOSI
px, py, _ = pi_pins[19]
wire(px, py + 0.8, TFT_X + 7, TFT_Y, COL_MOSI, mid_x=PI_X + PI_W + 9)
# SCLK (Pin 23) → TFT SCLK
px, py, _ = pi_pins[23]
wire(px, py + 0.8, TFT_X + 9.5, TFT_Y, COL_SCLK, mid_x=PI_X + PI_W + 11)
# CS (Pin 24) → TFT CS
px, py, _ = pi_pins[24]
wire(px, py - 0.8, TFT_X + 12, TFT_Y, COL_SIG, mid_x=PI_X + PI_W + 13)
# DC (Pin 18) → TFT DC
px, py, _ = pi_pins[18]
wire(px, py - 0.8, TFT_X + 14.5, TFT_Y, COL_SIG, mid_x=PI_X + PI_W + 15)
# RST (Pin 22) → TFT RST
px, py, _ = pi_pins[22]
wire(px, py - 0.8, TFT_X + 17, TFT_Y, COL_SIG, mid_x=PI_X + PI_W + 17)
# BL (Pin 33) → TFT BL
px, py, _ = pi_pins[33]
wire(px, py - 0.8, TFT_X + 19.5, TFT_Y, COL_SIG, mid_x=PI_X + PI_W + 19)

# Encoder: CLK (Pin 29), DT (Pin 31), SW (Pin 37)
for p_nr, target_x in [(29, ENC_X + 20), (31, ENC_X + 16), (37, ENC_X + 12)]:
    px, py, _ = pi_pins[p_nr]
    wire(px, py - 0.8, target_x, ENC_Y, COL_SIG, mid_x=PI_X - 4)

# Buttons: GPIO 16 (Pin 36), GPIO 12 (Pin 32)
px, py, _ = pi_pins[36]
wire(px, py - 0.8, BTN_X + 2, 5, COL_SIG, mid_x=BTN_X + 2)
px, py, _ = pi_pins[32]
wire(px, py - 0.8, BTN2_X + 2, 5, COL_SIG, mid_x=BTN2_X + 2)

# LED-Treiber: GPIO 17 → 220Ω → Gate
px, py, _ = pi_pins[11]
wire(px, py + 0.8, LED_X + 12, LED_Y + 2, COL_SIG, mid_x=LED_X + 12)
ax.text(LED_X + 7, LED_Y + 3, "220Ω", fontsize=5, color="#444")

# Speaker
ax.plot([AMP_X + 21, SPK_X - 4], [AMP_Y + 2, SPK_Y], color="#888", lw=2)
ax.plot([AMP_X + 24, SPK_X - 4], [AMP_Y + 2, SPK_Y - 2], color="#888", lw=2)

# ─── Legende ─────────────────────────────────────────────────────────────
legend_y = 95
legend_items = [
    (COL_5V,   "5 V"),
    (COL_3V3,  "3,3 V"),
    (COL_GND,  "GND"),
    (COL_I2S,  "I²S Takt"),
    (COL_MOSI, "SPI MOSI"),
    (COL_SCLK, "SPI SCLK"),
    (COL_SIG,  "Datenleitung"),
]
for i, (color, label) in enumerate(legend_items):
    lx = 8 + i * 18
    ax.plot([lx, lx + 5], [legend_y, legend_y], color=color, lw=3, solid_capstyle="round")
    ax.text(lx + 6, legend_y, label, ha="left", va="center", fontsize=8)
ax.text(70, 99, "Taktwerk — Verdrahtungs-Diagramm",
        ha="center", fontsize=13, fontweight="bold")

plt.tight_layout()
plt.savefig("wiring_diagram.png", dpi=200, bbox_inches="tight", facecolor="white")
print("✓ wiring_diagram.png erzeugt")
