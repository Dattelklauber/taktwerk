"""Erzeugt ein Schaltplan-Diagramm (PNG) für die Bauanleitung.

Zeigt Raspberry Pi Zero 2 W in der Mitte mit allen Modulen drumherum:
SPH0645-Mikro, MAX98357A-Amp, ST7789-TFT, KY-040-Encoder,
Drucktastern und LED-Treiber. GPIO-Pins beschriftet.
"""
import schemdraw
import schemdraw.elements as elm
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ─── Schaltplan ────────────────────────────────────────────────────────
schemdraw.config(font="DejaVu Sans", fontsize=10, lw=1.4)

with schemdraw.Drawing(file="schematic.png", show=False, dpi=200) as d:
    # Pi als Block in der Mitte
    pi = d.add(elm.Ic(pins=[
        # Linke Seite (Eingaben)
        elm.IcPin(name="3V3",        side="left",  pin="1"),
        elm.IcPin(name="5V",         side="left",  pin="2"),
        elm.IcPin(name="GND",        side="left",  pin="6"),
        elm.IcPin(name="GPIO 5",     side="left",  pin="29"),
        elm.IcPin(name="GPIO 6",     side="left",  pin="31"),
        elm.IcPin(name="GPIO 26",    side="left",  pin="37"),
        elm.IcPin(name="GPIO 16",    side="left",  pin="36"),
        elm.IcPin(name="GPIO 12",    side="left",  pin="32"),
        elm.IcPin(name="GPIO 17",    side="left",  pin="11"),
        # Rechte Seite (I2S + SPI)
        elm.IcPin(name="GPIO 18 (BCLK)",  side="right", pin="12"),
        elm.IcPin(name="GPIO 19 (LRCLK)", side="right", pin="35"),
        elm.IcPin(name="GPIO 20 (DIN)",   side="right", pin="38"),
        elm.IcPin(name="GPIO 21 (DOUT)",  side="right", pin="40"),
        elm.IcPin(name="GPIO 10 (MOSI)",  side="right", pin="19"),
        elm.IcPin(name="GPIO 11 (SCLK)",  side="right", pin="23"),
        elm.IcPin(name="GPIO 8  (CS)",    side="right", pin="24"),
        elm.IcPin(name="GPIO 24 (DC)",    side="right", pin="18"),
        elm.IcPin(name="GPIO 25 (RST)",   side="right", pin="22"),
        elm.IcPin(name="GPIO 13 (BL)",    side="right", pin="33"),
    ], size=(6, 12), label="Raspberry Pi Zero 2 W"))

    d.config(fontsize=9)
    # Beschriftungen der Module um den Pi herum
    d += elm.Line().right(d.unit).at(pi.pin12).label("→ MAX98357A BCLK\n→ SPH0645 BCLK",
                                                      loc="right", halign="left")
    d += elm.Line().right(d.unit).at(pi.pin35).label("→ MAX98357A LRC\n→ SPH0645 LRCL",
                                                      loc="right", halign="left")
    d += elm.Line().right(d.unit).at(pi.pin38).label("← SPH0645 DOUT",
                                                      loc="right", halign="left")
    d += elm.Line().right(d.unit).at(pi.pin40).label("→ MAX98357A DIN",
                                                      loc="right", halign="left")
    d += elm.Line().right(d.unit).at(pi.pin19).label("→ ST7789 MOSI", loc="right", halign="left")
    d += elm.Line().right(d.unit).at(pi.pin23).label("→ ST7789 SCLK", loc="right", halign="left")
    d += elm.Line().right(d.unit).at(pi.pin24).label("→ ST7789 CS",   loc="right", halign="left")
    d += elm.Line().right(d.unit).at(pi.pin18).label("→ ST7789 DC",   loc="right", halign="left")
    d += elm.Line().right(d.unit).at(pi.pin22).label("→ ST7789 RST",  loc="right", halign="left")
    d += elm.Line().right(d.unit).at(pi.pin33).label("→ ST7789 BL",   loc="right", halign="left")

    d += elm.Line().left(d.unit).at(pi.pin1).label("3.3 V → SPH0645 VDD,  Encoder VCC,  ST7789 VCC",
                                                    loc="left", halign="right")
    d += elm.Line().left(d.unit).at(pi.pin2).label("5 V → MAX98357A VIN,  LED+",
                                                    loc="left", halign="right")
    d += elm.Line().left(d.unit).at(pi.pin6).label("GND → alle Module",
                                                    loc="left", halign="right")
    d += elm.Line().left(d.unit).at(pi.pin29).label("← Encoder CLK",   loc="left", halign="right")
    d += elm.Line().left(d.unit).at(pi.pin31).label("← Encoder DT",    loc="left", halign="right")
    d += elm.Line().left(d.unit).at(pi.pin37).label("← Encoder SW",    loc="left", halign="right")
    d += elm.Line().left(d.unit).at(pi.pin36).label("← Button 1 (TAP)", loc="left", halign="right")
    d += elm.Line().left(d.unit).at(pi.pin32).label("← Button 2 (▶)",   loc="left", halign="right")
    d += elm.Line().left(d.unit).at(pi.pin11).label("→ 2N7000 Gate → LED", loc="left", halign="right")

print("✓ schematic.png erzeugt")

# ─── Block-Diagramm (Übersicht) ───────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 7), dpi=200)
ax.set_xlim(0, 100); ax.set_ylim(0, 70); ax.axis('off')
ax.set_facecolor('#fafafa')

def block(x, y, w, h, label, sublabel="", color="#e8f0f8", border="#1a3a5c"):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5",
                                   linewidth=2, edgecolor=border, facecolor=color)
    ax.add_patch(rect)
    ax.text(x + w/2, y + h/2 + (1.5 if sublabel else 0), label,
            ha='center', va='center', fontsize=11, fontweight='bold',
            color=border)
    if sublabel:
        ax.text(x + w/2, y + h/2 - 2, sublabel,
                ha='center', va='center', fontsize=9, color='#555')

def arrow(x1, y1, x2, y2, label="", curve=False):
    if curve:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='#444',
                                    connectionstyle="arc3,rad=0.2"))
    else:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='#444'))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2 + 1, label, ha='center', fontsize=8,
                color='#222', bbox=dict(boxstyle='round,pad=0.2',
                                         fc='white', ec='none', alpha=0.9))

# Zentraler Pi
block(40, 30, 20, 10, "Raspberry Pi", "Zero 2 W", color="#fff3cd", border="#856404")

# Mikrofon
block(5, 50, 22, 9, "SPH0645", "I²S MEMS-Mikro", color="#e3f2fd", border="#0d47a1")
arrow(27, 55, 40, 38, "I²S DIN")

# Audio-Out
block(5, 30, 22, 9, "MAX98357A + Lautsprecher", "I²S Class-D Amp", color="#e3f2fd", border="#0d47a1")
arrow(40, 33, 27, 34, "I²S DOUT")

# Display
block(72, 50, 23, 9, "ST7789 TFT", "2.0″ SPI 240×320", color="#f3e5f5", border="#4a148c")
arrow(60, 38, 72, 55, "SPI")

# Encoder + Buttons
block(72, 30, 23, 9, "Encoder + Taster", "KY-040 + 2× Drucktaster", color="#e8f5e9", border="#1b5e20")
arrow(72, 33, 60, 34, "GPIO Input")

# LED
block(72, 10, 23, 9, "LED + MOSFET", "Weiß, hell, via 2N7000", color="#fff9c4", border="#f57f17")
arrow(60, 32, 72, 15, "GPIO 17", curve=True)

# Power
block(5, 10, 22, 9, "USB 5 V Power", "Netzteil oder Powerbank", color="#ffebee", border="#b71c1c")
arrow(27, 14, 40, 30, "USB-Power")

# Mounting
block(40, 10, 20, 9, "Hi-Hat-Halterung", "PETG-Druck + Klemme", color="#efebe9", border="#3e2723")

ax.set_title("Taktwerk — Block-Diagramm", fontsize=14, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig("block_diagram.png", dpi=200, bbox_inches='tight', facecolor='white')
print("✓ block_diagram.png erzeugt")
