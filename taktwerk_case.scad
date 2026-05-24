// ────────────────────────────────────────────────────────────────────────
//  Taktwerk — 3D-Druck-Gehäuse
//  Parametrisch. Druckorientierung: Display nach oben.
//  Material: PETG empfohlen (UV-stabil, schlagfest).
//  Druckzeit: ~6 h bei 0.2 mm Schichthöhe, ~80 g Filament.
// ────────────────────────────────────────────────────────────────────────

$fn = 80;                // Auflösung der Kreise

// ─── Hauptmaße ─────────────────────────────────────────────
case_w        = 140;     // Breite (mm)
case_h        = 75;      // Tiefe (mm) — entlang Hi-Hat-Achse
case_d        = 32;      // Höhe (mm) — Display-Tiefe
wall          = 2.0;     // Wandstärke
corner_r      = 4;       // Eckenrundung

// Layout (Aufsicht Frontseite, Maße in mm):
//
//   y=75 ┌────────────────────────────────────────────┐
//        │                                            │
//   60   │   [  Display 32×42  ]      ◉ Lautsprecher  │
//        │                              (Wabengrill)  │
//   40   │   ● LED      ▭ Mic-Schlitz                 │
//        │                                            │
//   20   │   ⊙ Encoder    ⬜ TAP     ⬜ ▶ Start       │
//    0   └────────────────────────────────────────────┘
//        0      30      60      90      120         140

// ─── Display-Ausschnitt (ST7789 2.0") ─────────────────────
display_w     = 32;
display_h     = 42;
display_x     = 10;
display_y     = 30;

// ─── Bedienelemente (Unterzeile) ──────────────────────────
encoder_x     = 15;
encoder_y     = 10;
encoder_dia   = 7;

button1_x     = 50;
button1_y     = 10;
button_dia    = 12.5;

button2_x     = 85;
button2_y     = 10;

// ─── LED ──────────────────────────────────────────────────
led_x         = 15;
led_y         = 20;
led_dia       = 5.3;

// ─── Lautsprecher (Wabenmuster) ──────────────────────────
speaker_x     = 100;
speaker_y     = 55;
speaker_dia   = 30;
grille_hole_d = 2.4;

// ─── Mikrofon-Schlitz ────────────────────────────────────
mic_x         = 35;
mic_y         = 20;
mic_slot_w    = 10;
mic_slot_h    = 3;

// ─── USB-C Ausschnitt (Strom) ────────────────────────────
usb_y         = 15;      // vom unteren Rand der Seitenwand
usb_z         = 8;       // von der Bodenfläche
usb_w         = 10;
usb_h         = 5;

// ─── Hi-Hat-Klemme ───────────────────────────────────────
pipe_inner    = 13;      // Innen-Ø für Hi-Hat-Rohr (12–13 mm typisch)
pipe_outer    = pipe_inner + 8;   // Außen-Ø der Klemme
clamp_length  = 65;      // Länge entlang des Rohrs
clamp_slit    = 1.0;     // Schlitz-Breite
m4_screw_dia  = 4.5;
m4_head_dia   = 8;

// ─── Verschraubung Deckel-Boden ─────────────────────────
m3_screw_dia  = 3.4;     // Durchgangsloch für M3
m3_insert_dia = 4.2;     // für M3-Einschlagmutter
boss_dia      = 8;       // Außen-Ø der Befestigungssäulen
boss_h        = case_d - wall - 2;

// ─── Helfer-Module ───────────────────────────────────────

module rounded_box(w, h, d, r) {
    hull() for (x = [r, w-r], y = [r, h-r])
        translate([x, y, 0]) cylinder(r=r, h=d);
}

module speaker_holes(diameter, depth) {
    // Konzentrische Ring-Anordnung. Zylinder ragen 1 mm über die Wand
    // hinaus auf beiden Seiten → vermeidet Z-Fighting beim Rendern.
    hole_d = 3;
    h = depth + 2;     // 1 mm Überstand jeweils
    z = -1;
    translate([0, 0, z]) cylinder(d=hole_d, h=h);
    for (angle = [0:60:359])
        translate([6 * cos(angle), 6 * sin(angle), z])
            cylinder(d=hole_d, h=h);
    for (angle = [0:30:359])
        translate([10.5 * cos(angle), 10.5 * sin(angle), z])
            cylinder(d=hole_d, h=h);
    if (diameter >= 30) {
        for (angle = [0:20:359])
            translate([14 * cos(angle), 14 * sin(angle), z])
                cylinder(d=hole_d, h=h);
    }
}

module pipe_clamp() {
    // Vertikales Rohr (Z-Achse) wird umschlossen.
    // Klemmschraube zieht Schlitz horizontal zu.
    pcw = pipe_outer + 8;    // Breite quer zum Rohr
    pcl = pipe_outer + 16;   // Länge in Schraub-Richtung
    difference() {
        translate([-pcl/2, 0, 0])
            cube([pcl, pcw, clamp_length]);
        // Rohr-Loch vertikal in der Mitte
        translate([0, pcw/2, -1])
            cylinder(d=pipe_inner, h=clamp_length+2);
        // Schlitz: GANZE Strecke vom Rohr durch die hintere Hälfte hinaus.
        // So sind die beiden Hälften wirklich getrennt und können sich
        // durch die Schraube zusammenziehen.
        translate([-clamp_slit/2, pcw/2, -1])
            cube([clamp_slit, pcw/2 + 1, clamp_length+2]);
        // Klemmschraube — horizontal durch beide Hälften
        translate([-pcl/2-1, pcw-4, clamp_length/2])
            rotate([0, 90, 0])
                cylinder(d=m4_screw_dia, h=pcl+2);
        // Senkkopf-Aussparung für M4
        translate([pcl/2-4, pcw-4, clamp_length/2])
            rotate([0, 90, 0])
                cylinder(d=m4_head_dia, h=5);
    }
}

// ─── Hauptgehäuse (mit Cutouts und Klemme) ───────────────
module main_case() {
    difference() {
        union() {
            // Außenform
            rounded_box(case_w, case_h, case_d, corner_r);
            // Hi-Hat-Klemme an der Rückseite — Klemmen-Body ragt nach +Y
            // (weg von der Frontseite) heraus. Slot+Schraube hinten.
            translate([case_w/2, case_h - 4, 0])
                pipe_clamp();
        }

        // Innen-Hohlraum: oben (Z=case_d-wall) bleibt eine Wand mit Cutouts,
        // unten (Z<0) offen, damit Elektronik von unten eingesetzt werden kann
        translate([wall, wall, -1])
            rounded_box(case_w - 2*wall, case_h - 2*wall,
                        case_d - wall + 1, corner_r-0.5);

        // ── Display-Ausschnitt (Frontseite, hier oben in Druck-Lage) ──
        translate([display_x, display_y, case_d - wall - 0.1])
            cube([display_w, display_h, wall + 0.5]);

        // ── Encoder ──
        translate([encoder_x, encoder_y, case_d - wall - 0.1])
            cylinder(d=encoder_dia, h=wall + 0.5);
        // Versenkung für KY-040-Platine (innen)
        translate([encoder_x-12.5, encoder_y-11, case_d - wall - 1.6])
            cube([25, 22, 2]);

        // ── Drucktaster ──
        translate([button1_x, button1_y, case_d - wall - 0.1])
            cylinder(d=button_dia, h=wall + 0.5);
        translate([button2_x, button2_y, case_d - wall - 0.1])
            cylinder(d=button_dia, h=wall + 0.5);

        // ── LED ──
        translate([led_x, led_y, case_d - wall - 0.1])
            cylinder(d=led_dia, h=wall + 0.5);

        // ── Lautsprecher-Grill ──
        translate([speaker_x, speaker_y, case_d - wall - 0.1])
            speaker_holes(diameter=speaker_dia, depth=wall);

        // ── Mikrofon-Schlitz ──
        translate([mic_x-mic_slot_w/2, mic_y-mic_slot_h/2, case_d-wall-0.1])
            cube([mic_slot_w, mic_slot_h, wall+0.5]);

        // ── USB-C an der Seite ──
        translate([case_w - wall - 0.1, usb_y, usb_z])
            cube([wall + 0.5, usb_w, usb_h]);

        // ── Verschraubungslöcher (4 Ecken im Boden) ──
        boss_inset = 6;
        for (cx = [boss_inset, case_w - boss_inset])
            for (cy = [boss_inset, case_h - boss_inset])
                translate([cx, cy, -0.1])
                    cylinder(d=m3_screw_dia, h=wall + 0.5);
    }

    // ── Verschraubungs-Säulen mit Einschlagmutter-Aufnahme ──
    boss_inset = 6;
    for (cx = [boss_inset, case_w - boss_inset])
        for (cy = [boss_inset, case_h - boss_inset])
            translate([cx, cy, wall])
                difference() {
                    cylinder(d=boss_dia, h=boss_h);
                    translate([0, 0, boss_h - 6])
                        cylinder(d=m3_insert_dia, h=6.5);
                }
}

// ─── Deckel / Bodenplatte ────────────────────────────────
module base_plate() {
    plate_thickness = 2.5;
    difference() {
        rounded_box(case_w, case_h, plate_thickness, corner_r);
        // Schraubenlöcher
        boss_inset = 6;
        for (cx = [boss_inset, case_w - boss_inset])
            for (cy = [boss_inset, case_h - boss_inset])
                translate([cx, cy, -0.1])
                    cylinder(d=m3_screw_dia, h=plate_thickness + 0.2);
        // Senkungen für die Schraubköpfe
        for (cx = [boss_inset, case_w - boss_inset])
            for (cy = [boss_inset, case_h - boss_inset])
                translate([cx, cy, plate_thickness - 1.5])
                    cylinder(d1=m3_screw_dia, d2=m3_screw_dia + 3, h=1.6);
    }
}

// ─── Ausgabe — beide Teile nebeneinander für Übersicht ───
// Zum Drucken nur eines auswählen (anderes auskommentieren)

main_case();
translate([0, -case_h - 10, 0]) base_plate();
