"""Generate the build manual PDF for the Drum Tempo Monitor."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether,
)

OUTPUT = "/Users/guidoport/drum-tempo-monitor/Drum_Tempo_Monitor_Bauanleitung.pdf"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="H1Custom", parent=styles["Heading1"],
    fontSize=18, spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#1a3a5c"),
))
styles.add(ParagraphStyle(
    name="H2Custom", parent=styles["Heading2"],
    fontSize=13, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#2c5a8a"),
))
styles.add(ParagraphStyle(
    name="Body", parent=styles["BodyText"],
    fontSize=10.5, leading=14, alignment=TA_JUSTIFY, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="CodeBlock", parent=styles["BodyText"],
    fontName="Courier", fontSize=9, leading=11, leftIndent=12,
    textColor=colors.HexColor("#222"), backColor=colors.HexColor("#f0f0f0"),
    borderPadding=6, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="Caption", parent=styles["BodyText"],
    fontSize=9, textColor=colors.HexColor("#555"), spaceAfter=10,
    alignment=TA_LEFT,
))


def H1(text): return Paragraph(text, styles["H1Custom"])
def H2(text): return Paragraph(text, styles["H2Custom"])
def P(text): return Paragraph(text, styles["Body"])
def Code(text): return Paragraph(text.replace(" ", "&nbsp;").replace("\n", "<br/>"), styles["CodeBlock"])
def Cap(text): return Paragraph(text, styles["Caption"])


def make_table(data, col_widths, header=True, zebra=True):
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#1a3a5c")),
        ]
    if zebra:
        for i in range(1 if header else 0, len(data)):
            if (i - (1 if header else 0)) % 2 == 1:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f7f7f7")))
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    t.setStyle(TableStyle(style))
    return t


story = []

# ───── Title page ─────
story.append(Spacer(1, 30 * mm))
story.append(Paragraph(
    "Drum Tempo Monitor",
    ParagraphStyle("Title1", parent=styles["Title"], fontSize=32,
                   textColor=colors.HexColor("#1a3a5c"), spaceAfter=10),
))
story.append(Paragraph(
    "Bau- und Konfigurationsanleitung",
    ParagraphStyle("Sub1", parent=styles["Title"], fontSize=16,
                   textColor=colors.HexColor("#666"), spaceAfter=40),
))
story.append(Spacer(1, 20 * mm))
story.append(P(
    "Ein eigenständiges, USB-betriebenes Gerät zur Tempokontrolle beim "
    "Live-Schlagzeugspiel. Es gibt einen Klick im gewählten Tempo vor "
    "(Audio + LED), erfasst das Schlagzeug über ein integriertes Mikrofon, "
    "erkennt jeden einzelnen Schlag und zeigt auf einem TFT-Display die "
    "aktuell gespielte BPM, die Phasenabweichung pro Schlag und einen "
    "scrollenden Tempo-Verlauf an."
))
story.append(Spacer(1, 10 * mm))
story.append(P(
    "<b>Plattform:</b> Raspberry Pi Zero 2 W &nbsp;&nbsp; "
    "<b>Versorgung:</b> 5 V / 2 A über USB &nbsp;&nbsp; "
    "<b>Montage:</b> Hi-Hat-Ständer (⌀ 12–13 mm)"
))
story.append(PageBreak())

# ───── 1. Übersicht ─────
story.append(H1("1. Funktionsübersicht"))
story.append(P(
    "Das Gerät kombiniert drei Funktionen, die normalerweise nur in "
    "kommerziellen Hardware-Metronomen ab 200 € zusammen verfügbar sind:"
))
story.append(P(
    "<b>Klick-Ausgabe.</b> Ein kleiner, leistungsfähiger Lautsprecher "
    "(3 W) gibt den Klick auch bei voller Bandlautstärke hörbar wieder. "
    "Parallel pulst eine helle Front-LED synchron — auf Zählzeit 1 mit "
    "doppelt langem Blitz, damit die Taktart auch peripher sichtbar ist."
))
story.append(P(
    "<b>Schlag-Erfassung.</b> Ein digitales MEMS-Mikrofon im Gehäuse "
    "nimmt das Schlagzeug im Raum auf. Per Onset-Detection (HFC-Methode "
    "aus aubio) wird jeder Schlag mit einer Zeitauflösung von wenigen "
    "Millisekunden erkannt — ohne Piezo-Sensoren oder Kabel an den "
    "Trommeln."
))
story.append(P(
    "<b>Auswertung & Anzeige.</b> Zwei voneinander unabhängige Metriken "
    "werden parallel berechnet und dargestellt:"
))
story.append(P(
    "&nbsp;&nbsp;<b>(a) Tempo-Trend</b> — die über die letzten 8 Schläge "
    "gemittelte BPM, als Linie gegen die Soll-BPM aufgetragen. Zeigt "
    "Drift (langsames Schneller- oder Langsamer-Werden)."
))
story.append(P(
    "&nbsp;&nbsp;<b>(b) Phasenabweichung</b> — für jeden Schlag der "
    "ms-Versatz zum nächstliegenden erwarteten Klick. Zeigt Mikro-"
    "Präzision (Jitter)."
))

# ───── 2. Bauteilliste ─────
story.append(H1("2. Bauteilliste"))
parts = [
    ["Pos", "Bauteil", "Modell / Spezifikation", "Stk", "Preis"],
    ["1",  "Mikrocontroller",   "Raspberry Pi Zero 2 W",                       "1",   "22 €"],
    ["2",  "microSD-Karte",     "16 GB, Class A1 (z.B. SanDisk Ultra)",        "1",   "8 €"],
    ["3",  "Mikrofon",          "SPH0645LM4H I²S MEMS Breakout (Adafruit 3421)", "1", "10 €"],
    ["4",  "Audio-Verstärker",  "MAX98357A I²S Class-D Mono Amp",              "1",   "7 €"],
    ["5",  "Lautsprecher",      "Visaton K 36 WP, 4 Ω, 3 W, ⌀ 36 mm",          "1",   "8 €"],
    ["6",  "TFT-Display",       "2.0″ ST7789 SPI, 240 × 320 px",               "1",   "12 €"],
    ["7",  "Rotary Encoder",    "KY-040 mit Druckfunktion",                    "1",   "3 €"],
    ["8",  "Drucktaster",       "12 mm momentary, schwarz/rot",                "2",   "2 €"],
    ["9",  "LED",               "Weiß, 5 mm, ≥ 20 000 mcd, klar",              "1",   "1 €"],
    ["10", "MOSFET",            "2N7000 N-Channel Logic-Level",                "1",   "1 €"],
    ["11", "Widerstände",       "100 Ω, 220 Ω, 1 kΩ, 10 kΩ (¼ W)",            "je 1","1 €"],
    ["12", "Stiftleisten",      "2,54 mm Raster, gerade",                      "div.", "2 €"],
    ["13", "Lochrasterplatine", "70 × 50 mm, doppelseitig",                    "1",   "3 €"],
    ["14", "Schaltdraht",       "0,25 mm² flexibel, mehrere Farben",           "5 m", "3 €"],
    ["15", "Schrauben",         "M3 × 10 + M3-Einschlagmuttern",               "8 St", "3 €"],
    ["16", "Gehäuse",           "3D-Druck PETG  oder  Hammond 1591ESBK",       "1",   "5–30 €"],
    ["17", "Hi-Hat-Halterung",  "integriert (Druck) oder Manfrotto Clamp 035", "1",   "0–28 €"],
    ["18", "USB-Kabel",         "USB-A → micro-USB, 1 m, gewinkelt",           "1",   "4 €"],
]
story.append(make_table(parts, [13*mm, 36*mm, 70*mm, 13*mm, 22*mm]))
story.append(Spacer(1, 4))
story.append(Cap(
    "Summe: ca. <b>90 € (3D-Druck-Variante)</b> bis <b>130 € "
    "(Hammond + Super Clamp)</b>. Stromversorgung (USB-Netzteil 5 V / 2 A "
    "oder Powerbank) ist meist vorhanden und nicht eingerechnet."
))

# ───── 3. Werkzeug ─────
story.append(H2("Benötigtes Werkzeug"))
story.append(P(
    "Lötkolben (temperaturgeregelt, 30–60 W), Lötzinn 0,5 mm, "
    "Seitenschneider, Abisolierzange, kleiner Kreuzschlitz, Multimeter, "
    "PC mit microSD-Leser, optional Dremel/Proxxon-Fräse (nur bei "
    "Hammond-Gehäuse für die Display-Ausschnitte)."
))

story.append(PageBreak())

# ───── 4. Verdrahtung ─────
story.append(H1("3. Verdrahtung (GPIO-Belegung)"))
story.append(P(
    "Alle GPIO-Nummern sind im <b>BCM</b>-Schema angegeben (so wie sie "
    "in <code>gpiozero</code> und in der Pi-Pinout-Dokumentation verwendet "
    "werden). Mikrofon und Verstärker teilen sich den I²S-Bus — das spart "
    "Pins und ist auf dem Pi mit dem <code>googlevoicehat-soundcard</code>-"
    "Overlay direkt unterstützt (gleicher Aufbau wie das Google AIY Voice Kit)."
))

story.append(H2("3.1  I²S-Bus (gemeinsam für Mikro und Verstärker)"))
i2s = [
    ["Signal", "GPIO (BCM)", "Pin am Pi", "Funktion"],
    ["BCLK",       "GPIO 18", "12", "Bit-Clock, vom Pi an beide"],
    ["LRCLK / WS", "GPIO 19", "35", "Word-Select, vom Pi an beide"],
    ["DOUT (TX)",  "GPIO 21", "40", "Pi → MAX98357A DIN (Klick-Audio)"],
    ["DIN (RX)",   "GPIO 20", "38", "SPH0645 DOUT → Pi (Mikro-Audio)"],
]
story.append(make_table(i2s, [25*mm, 30*mm, 22*mm, 65*mm]))

story.append(H2("3.2  Mikrofon SPH0645"))
mic = [
    ["Mikro-Pin", "Ziel", "Bemerkung"],
    ["VDD",  "3,3 V Pi (Pin 1)",      "max. 3,6 V — niemals 5 V!"],
    ["GND",  "GND Pi (Pin 6)",        "—"],
    ["BCLK", "GPIO 18 (Pin 12)",      "gemeinsam mit Amp"],
    ["LRCL", "GPIO 19 (Pin 35)",      "gemeinsam mit Amp"],
    ["DOUT", "GPIO 20 (Pin 38)",      "Daten zum Pi"],
    ["SEL",  "GND",                   "wählt linker Kanal"],
]
story.append(make_table(mic, [28*mm, 50*mm, 64*mm]))

story.append(H2("3.3  Verstärker MAX98357A"))
amp = [
    ["Amp-Pin",   "Ziel", "Bemerkung"],
    ["VIN",      "5 V Pi (Pin 2)",          "—"],
    ["GND",      "GND Pi (Pin 6)",          "—"],
    ["BCLK",     "GPIO 18 (Pin 12)",        "gemeinsam mit Mikro"],
    ["LRC",      "GPIO 19 (Pin 35)",        "gemeinsam mit Mikro"],
    ["DIN",      "GPIO 21 (Pin 40)",        "Audio vom Pi"],
    ["GAIN",     "unverbunden",             "Default 9 dB"],
    ["SD",       "unverbunden",             "Default 'beide Kanäle'"],
    ["Speaker±", "Lautsprecher",            "Polarität egal bei Mono"],
]
story.append(make_table(amp, [28*mm, 50*mm, 64*mm]))

story.append(PageBreak())

story.append(H2("3.4  TFT-Display ST7789 (SPI)"))
tft = [
    ["TFT-Pin",  "Ziel", "Bemerkung"],
    ["VCC", "3,3 V Pi (Pin 17)",      "—"],
    ["GND", "GND Pi (Pin 9)",         "—"],
    ["DIN / MOSI", "GPIO 10 (Pin 19)", "SPI MOSI"],
    ["CLK / SCLK", "GPIO 11 (Pin 23)", "SPI SCLK"],
    ["CS",  "GPIO 8  (Pin 24)",       "Chip Select 0"],
    ["DC",  "GPIO 24 (Pin 18)",       "Data/Command"],
    ["RST", "GPIO 25 (Pin 22)",       "Reset"],
    ["BL",  "GPIO 13 (Pin 33)",       "Backlight (PWM-fähig)"],
]
story.append(make_table(tft, [28*mm, 50*mm, 64*mm]))

story.append(H2("3.5  Bedienelemente"))
ctl = [
    ["Element",  "Pin am Element",  "GPIO (BCM)",  "Pin am Pi"],
    ["Encoder",  "CLK",             "GPIO 5",      "29"],
    ["Encoder",  "DT",              "GPIO 6",      "31"],
    ["Encoder",  "SW (Druck)",      "GPIO 26",     "37"],
    ["Encoder",  "+ / VCC",         "3,3 V",       "1"],
    ["Encoder",  "GND",             "GND",         "6"],
    ["Button 1 (TAP)",      "ein Bein", "GPIO 16", "36"],
    ["Button 1 (TAP)",      "zweites Bein", "GND", "—"],
    ["Button 2 (Start/Stop)", "ein Bein", "GPIO 12", "32"],
    ["Button 2 (Start/Stop)", "zweites Bein", "GND", "—"],
]
story.append(make_table(ctl, [40*mm, 38*mm, 32*mm, 30*mm]))
story.append(Cap(
    "Die internen Pull-Up-Widerstände der GPIO-Pins werden in Software "
    "aktiviert (gpiozero <code>Button(pin, pull_up=True)</code>) — keine "
    "externen Widerstände nötig."
))

story.append(H2("3.6  LED-Treiber (für hohe Helligkeit)"))
story.append(P(
    "Die LED zieht ca. 30 mA — mehr als ein GPIO direkt liefern sollte. "
    "Deshalb über einen Logic-Level-MOSFET schalten:"
))
led = [
    ["Bauteil",  "Pin",  "Verbindung"],
    ["2N7000",  "Gate",   "GPIO 17 (Pin 11) über 220 Ω-Widerstand"],
    ["2N7000",  "Gate",   "zusätzlich 10 kΩ Pull-Down nach GND"],
    ["2N7000",  "Drain",  "LED Kathode"],
    ["2N7000",  "Source", "GND"],
    ["LED",     "Anode",  "über 100 Ω an 5 V"],
    ["LED",     "Kathode", "Drain des 2N7000"],
]
story.append(make_table(led, [28*mm, 28*mm, 90*mm]))

story.append(PageBreak())

# ───── 5. Software-Setup ─────
story.append(H1("4. Software-Setup"))
story.append(P(
    "Basis: <b>Raspberry Pi OS Lite (64-bit, Bookworm)</b>. Kein "
    "Desktop — die UI läuft direkt auf dem TFT über das Framebuffer-"
    "Device, das spart RAM und Boot-Zeit."
))

story.append(H2("4.1  SD-Karte vorbereiten"))
story.append(P(
    "Mit dem Raspberry Pi Imager das Image schreiben. Im Imager unter "
    "&bdquo;Einstellungen&ldquo; Hostname (<code>tempo</code>), "
    "Benutzer/Passwort, WLAN und SSH bereits konfigurieren — danach "
    "läuft das Gerät headless."
))

story.append(H2("4.2  Device-Tree-Overlays aktivieren"))
story.append(P(
    "In <code>/boot/firmware/config.txt</code> ergänzen:"
))
story.append(Code(
    "# Audio: Mikro + Amp am gleichen I²S-Bus\n"
    "dtparam=audio=off\n"
    "dtoverlay=googlevoicehat-soundcard\n"
    "\n"
    "# Display\n"
    "dtparam=spi=on\n"
    "\n"
    "# HDMI deaktivieren, spart Strom und Boot-Zeit\n"
    "hdmi_blanking=2"
))

story.append(H2("4.3  Pakete und Python-Umgebung"))
story.append(Code(
    "sudo apt update\n"
    "sudo apt install -y python3-pip python3-venv \\\n"
    "    libasound2-dev libportaudio2 libsndfile1 \\\n"
    "    libatlas-base-dev fonts-dejavu\n"
    "\n"
    "python3 -m venv ~/dtm-env\n"
    "source ~/dtm-env/bin/activate\n"
    "pip install sounddevice aubio numpy pillow \\\n"
    "    luma.lcd gpiozero spidev"
))

story.append(H2("4.4  Anwendung und Autostart"))
story.append(P(
    "Anwendung in <code>~/drum-tempo-monitor/</code> ablegen. Für den "
    "Autostart einen systemd-Service anlegen:"
))
story.append(Code(
    "sudo tee /etc/systemd/system/dtm.service &lt;&lt;EOF\n"
    "[Unit]\n"
    "Description=Drum Tempo Monitor\n"
    "After=sound.target\n"
    "\n"
    "[Service]\n"
    "User=pi\n"
    "ExecStart=/home/pi/dtm-env/bin/python \\\n"
    "    /home/pi/drum-tempo-monitor/tempo_monitor.py\n"
    "Restart=always\n"
    "\n"
    "[Install]\n"
    "WantedBy=multi-user.target\n"
    "EOF\n"
    "\n"
    "sudo systemctl enable --now dtm.service"
))

story.append(H2("4.5  Read-Only-Dateisystem"))
story.append(P(
    "Damit das Gerät jederzeit hart vom Strom getrennt werden kann "
    "(z.B. wenn die Powerbank leer ist) ohne die SD-Karte zu "
    "korrumpieren, das Overlay-FS aktivieren:"
))
story.append(Code("sudo raspi-config nonint do_overlayfs 0"))

story.append(PageBreak())

# ───── 6. Gehäuse-Optionen ─────
story.append(H1("5. Gehäuse-Optionen"))

story.append(H2("Option A — 3D-Druck PETG  (empfohlen)"))
story.append(P(
    "Maßgeschneidertes Gehäuse, alle Aussparungen direkt im Druck, "
    "integrierte Klemme für den Hi-Hat-Ständer. Material: PETG (UV-"
    "stabil, schlagfest, lebensmittelechte Lebensmittelechtheit "
    "uninteressant, aber temperaturfest)."
))
gehA = [
    ["Eigenschaft", "Wert"],
    ["Abmessungen",        "ca. 130 × 75 × 35 mm (B × H × T)"],
    ["Wandstärke",         "1,6 mm"],
    ["Druckzeit",          "ca. 6 h bei 0,2 mm Schichthöhe"],
    ["Filament-Verbrauch", "ca. 80 g"],
    ["Vorderseite",        "Display 27×40 mm, Encoder ⌀7 mm, 2× Taster ⌀12 mm, LED ⌀5 mm, Lautsprecher-Wabengrill ⌀ 38 mm, Mikro-Schlitz 3×10 mm"],
    ["Rückseite",          "geschlitzte Rohrschelle ⌀ 12–13 mm mit M4-Klemmschraube"],
    ["Verschraubung",      "4× M3-Einschlagmuttern, M3×10 Schrauben"],
    ["Kosten Eigendruck",  "ca. 2 € Filament"],
    ["Kosten Druckservice", "15–25 € (JLCPCB, Anycubic, Treatstock)"],
]
story.append(make_table(gehA, [42*mm, 110*mm]))

story.append(H2("Option B — Hammond 1591ESBK + Super Clamp"))
story.append(P(
    "Industrielles ABS-Fertiggehäuse, alle Aussparungen selbst fräsen "
    "(Proxxon, Dremel, oder Stufenbohrer für die Rundlöcher). "
    "Montage am Hi-Hat über Manfrotto 035 Super Clamp — Standard aus "
    "der Fotografie, hält bombenfest an Rohren bis 55 mm und hat ein "
    "1/4″-20-Gewinde unten."
))
gehB = [
    ["Eigenschaft", "Wert"],
    ["Gehäuse",            "Hammond 1591ESBK, 121×66×40 mm, schwarz ABS"],
    ["Halterung",          "Manfrotto 035 Super Clamp"],
    ["Verbindung",         "1/4″-20 Einschlagmutter in Gehäuse-Rückseite"],
    ["Vorteil",            "robust, ohne 3D-Drucker, abnehmbar"],
    ["Nachteil",           "mehr Fräs-/Bohrarbeit, größerer Footprint"],
    ["Kosten gesamt",      "ca. 40 € (Gehäuse 10 € + Clamp 28 € + Schraubzeug)"],
]
story.append(make_table(gehB, [42*mm, 110*mm]))

story.append(H2("Option C — Aluminium-Druckguss (Premium)"))
story.append(P(
    "Hammond 1455-Serie oder Bopla Alubos — maximal robust, EMI-"
    "abschirmend, edle Optik. Aber: schwerer (300+ g), Bohrungen "
    "aufwendiger, und das Mikrofon braucht eine größere Öffnung weil "
    "Aluminium den Schall stärker dämpft als Kunststoff. Nur sinnvoll "
    "wenn du sowieso Metall-Bauerfahrung hast."
))

story.append(H1("6. Montage am Hi-Hat-Ständer"))
story.append(P(
    "<b>Wichtig (gilt für alle Gehäuse-Varianten):</b> Zwischen Halterung "
    "und Hi-Hat-Rohr immer einen <b>schmalen Gummi- oder Schaumstoff-"
    "Streifen</b> legen. Sonst überträgt jeder Hi-Hat-Tritt Körperschall "
    "direkt ins Gehäuse, und das Mikrofon erkennt Klicks, die nicht "
    "gespielt wurden. Ein zugeschnittener Stück Fahrradschlauch oder "
    "selbstklebendes EPDM-Schaumband (3 mm) reicht."
))
story.append(P(
    "Position: idealerweise auf der dem Spieler abgewandten Seite des "
    "Hi-Hat-Ständers in Brusthöhe — gut sichtbar, aber außerhalb der "
    "direkten Schlag-Linie. Display leicht nach oben zum Spieler kippen."
))

story.append(PageBreak())

# ───── 7. Inbetriebnahme ─────
story.append(H1("7. Erstes Einrichten & Bedienung"))

story.append(H2("7.1  Boot"))
story.append(P(
    "Stromversorgung anstecken — nach ca. 20 s ist das Gerät bereit "
    "(LED leuchtet kurz auf, Display zeigt zuletzt verwendete BPM und "
    "Taktart). Read-Only-FS erlaubt jederzeit sauberes Strom-Trennen."
))

story.append(H2("7.2  Bedienlogik"))
ops = [
    ["Aktion", "Ergebnis"],
    ["Encoder drehen",         "BPM ±1 (langsam) bzw. ±5 (schnell, mit Drehbeschleunigung)"],
    ["Encoder kurz drücken",   "Fokus wechselt: BPM → Taktart → BPM"],
    ["Encoder im Taktart-Fokus drehen", "2/4 → 3/4 → 4/4 → 5/4 → 6/8 → 7/8 → 12/8"],
    ["Encoder lang drücken",   "Einstellung speichern (überlebt Neustart)"],
    ["Button 1 (TAP) 4× tippen", "Tap-Tempo — BPM wird auf gemessenes Tempo gesetzt"],
    ["Button 2 (▶)",            "Metronom Start / Stop"],
]
story.append(make_table(ops, [60*mm, 92*mm]))

story.append(H2("7.3  Display-Inhalte im Spielbetrieb"))
story.append(P(
    "<b>Oben:</b> Soll-BPM und aktuell gemessene Ist-BPM, daneben "
    "Taktart und Beat-Indikator (gefüllte Kreise zeigen den aktuellen "
    "Schlag im Takt)."
))
story.append(P(
    "<b>Mitte — Phasenabweichung:</b> Scatterplot der letzten 30 s, "
    "jeder Punkt ist ein erkannter Schlag. Y-Achse: ms-Versatz zum "
    "nächsten Klick (positiv = zu spät, negativ = zu früh). Mittel-"
    "linie = exakt auf dem Klick. Farbzonen: grün ±10 ms (studio-"
    "tight), gelb ±10–25 ms (musikalisch ok), rot > 25 ms (hörbar off)."
))
story.append(P(
    "<b>Unten — Tempo-Verlauf:</b> Linie der gemessenen BPM gegen Zeit, "
    "mit horizontaler Referenz auf Soll-BPM. Zeigt langfristige Drift "
    "(typisches Schneller-Werden im Refrain)."
))

story.append(H2("7.4  Klick und LED"))
story.append(P(
    "Auf jeder Zählzeit pulst der Lautsprecher kurz (15 ms) und die "
    "Front-LED blitzt für 30 ms. Auf Zählzeit 1 doppelt so langer "
    "Klick + Blitz — so behältst du die Taktart auch peripher im Auge."
))

story.append(PageBreak())

# ───── 8. Aufbau Schritt für Schritt ─────
story.append(H1("8. Aufbau in 8 Schritten"))
steps = [
    ("SD-Karte schreiben", "Raspberry Pi OS Lite 64-bit mit Imager flashen, SSH und WLAN konfigurieren."),
    ("Pi vorab konfigurieren", "Per SSH einloggen, config.txt anpassen (Abschnitt 4.2), Pakete + venv installieren (4.3). Bevor Hardware verkabelt wird, lässt sich so alles testen."),
    ("Lochrasterplatine bestücken", "Mikrofon, Verstärker, MOSFET, Widerstände auflöten. Kurze, geordnete Verbindungen — keine fliegenden Drähte über dem Pi."),
    ("Verkabelung", "Alle Signale gemäß Tabellen in Abschnitt 3 verbinden. Mit Multimeter Durchgang prüfen, bevor zum ersten Mal Strom angelegt wird."),
    ("Funktionstest auf der Werkbank", "Stromversorgung anschließen, per SSH einloggen. Audio-Test: <code>speaker-test -c 1</code>. Mikro-Test: <code>arecord -d 3 test.wav</code> und am PC anhören."),
    ("Anwendung starten", "<code>tempo_monitor.py</code> auf den Pi kopieren, systemd-Service aktivieren (Abschnitt 4.4). Klick und Display sollten sofort funktionieren."),
    ("Gehäuse vorbereiten", "Bei 3D-Druck: Schalen drucken, Einschlagmuttern setzen. Bei Hammond: Ausschnitte fräsen, Gewindeplatte einsetzen."),
    ("Einbau & Endmontage", "Alle Komponenten ins Gehäuse, verschrauben. Gummi-Streifen zwischen Halterung und Hi-Hat-Rohr. Spielposition prüfen, Tempo einstellen, los geht's."),
]
for i, (title, txt) in enumerate(steps, 1):
    story.append(KeepTogether([
        Paragraph(f"<b>Schritt {i}: {title}</b>", styles["Body"]),
        Paragraph(txt, styles["Body"]),
        Spacer(1, 4),
    ]))

# ───── 9. Hinweise zur Weiterentwicklung ─────
story.append(H1("9. Hinweise und mögliche Erweiterungen"))
story.append(P(
    "<b>Kalibrierung der Onset-Erkennung:</b> Der Schwellwert in aubio "
    "(<code>onset.set_threshold</code>) sollte beim ersten Einrichten "
    "ans eigene Schlagzeug angepasst werden — leiser gestimmte Drumsets "
    "brauchen niedrigere Werte (0,2–0,3), harte Becken eher 0,4–0,5."
))
story.append(P(
    "<b>Latenzkompensation:</b> Der I²S-Buffer erzeugt eine konstante "
    "Verzögerung von etwa 12 ms. Sie wird in Software einmalig kalibriert "
    "(Klick gegen ein Referenz-Mikro messen) und vom gemessenen "
    "Onset-Zeitstempel abgezogen, damit die Phasenabweichung absolut "
    "ehrlich bleibt."
))
story.append(P(
    "<b>Mögliche Erweiterungen:</b> RGB-LED statt einfacher weißer LED "
    "(rot/weiß für Beat-1-Unterscheidung); Aufzeichnung der Phase-"
    "Statistik pro Song für späteres Üben; Bluetooth-Anbindung an ein "
    "Tablet für detaillierte Trend-Analyse; zusätzlicher Footswitch-"
    "Eingang für Start/Stop ohne Hände-Einsatz."
))

# Build the PDF
doc = SimpleDocTemplate(
    OUTPUT, pagesize=A4,
    leftMargin=20*mm, rightMargin=20*mm,
    topMargin=18*mm, bottomMargin=18*mm,
    title="Drum Tempo Monitor — Bauanleitung",
    author="Drum Tempo Monitor Project",
)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#888"))
    canvas.drawString(20*mm, 10*mm, "Drum Tempo Monitor — Bauanleitung")
    canvas.drawRightString(190*mm, 10*mm, f"Seite {doc.page}")
    canvas.restoreState()


doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"PDF erstellt: {OUTPUT}")
