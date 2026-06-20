// Muon detector setup - revised OpenSCAD model v9
// Units in source are inches; OpenSCAD geometry is generated in mm.
//
// Changes in this version:
// 1) Bottom slab guide is now flush with the slab (no extra rise above slab top).
// 2) Middle PMTs now use the same hull-based oblique construction idea as the guide.
// 3) Middle PMTs still start at the end of the guide, with their bottoms flush
//    to the guide bottom at the exit face.

IN = 25.4;
EPS = 0.01 * IN;

function inch(x) = x * IN;
function deg(x) = x * 180 / PI;

// ---------- Display toggles ----------
SHOW_SHELF = true;
EXPLODED_VIEW = false;   // true = place assemblies side-by-side for inspection
SHOW_AXES = false;
ROTATE_DETECTORS_90 = true;

// ---------- Shelf parameters (from Amazon listing) ----------
SHELF_W = 36;
SHELF_D = 14;
SHELF_H = 36;
SHELF_THICK = 1;
POST_SIZE = 1;

// Middle shelf lowered so the middle assembly clears the top detector.
SHELF_ZS = [0, 13, 30];

// ---------- Top slab ----------
TOP_SLAB_L = 43.625;
TOP_SLAB_W = 25.875;
TOP_SLAB_H = 2.25;
TOP_PMT_L = 6.25;
TOP_PMT_W = 3.25;
TOP_PMT_H = 3.5;

// ---------- Bottom slab ----------
BOT_SLAB_L = 49.5;
BOT_SLAB_W = 30.125;
BOT_SLAB_H = 2.125;
BOT_GUIDE_L = 13.125;
BOT_GUIDE_W1 = 30.125;
BOT_GUIDE_W2 = 4.0;
BOT_GUIDE_H = 2.125;               // guide thickness; now flush with slab thickness
BOT_GUIDE_RISE = 0.0;              // no vertical rise; guide is flush with slab
BOT_PMT_L = 6.5;
BOT_PMT_W = 4.0;
BOT_PMT_H = 2.625;

// ---------- Middle slab ----------
MID_SLAB_L = 48.0;
MID_SLAB_W = 30.625;
MID_SLAB_H = 2.125;
MID_GUIDE_L = 14.75;
MID_GUIDE_W1 = 30.625;
MID_GUIDE_W2 = 2.625;
MID_GUIDE_H = 2.125;               // constant tunnel thickness per latest instruction
MID_PMT_L = 5.5;
MID_PMT_W = 2.625;
MID_PMT_H = 2.125;
MID_PMT_GAP_Y = 0.0;

// --- Middle detector slope control ---
// User requested a steeper shared angle for the middle light tunnel and PMT,
// with the total middle component reaching 15.5 in overall height.
// Here, "total height" is interpreted as the vertical distance from the
// bottom of the middle slab / guide to the highest point of the last PMT.
MID_TOTAL_HEIGHT = 15.5;

// The current middle PMT layout is a 2x2 cluster built as two PMT columns
// in the x-direction, so the sloped run extends across:
//   guide length + first PMT length + second PMT length
MID_TOTAL_RUN = MID_GUIDE_L + 2 * MID_PMT_L;

// Because the guide and PMTs all keep the same constant thickness, the bottom
// surface must rise by (target top height - thickness) over the full run.
MID_TOTAL_RISE = MID_TOTAL_HEIGHT - MID_PMT_H;
MID_SLOPE_PER_IN = MID_TOTAL_RISE / MID_TOTAL_RUN;

// Rise of the guide bottom from its start to its exit face.
MID_GUIDE_RISE = MID_GUIDE_L * MID_SLOPE_PER_IN;
MID_GUIDE_ANGLE = deg(atan(MID_SLOPE_PER_IN));

// Rise of each PMT section so each one follows the same slope as the guide.
MID_PMT_RISE = MID_PMT_L * MID_SLOPE_PER_IN;

// ---------- Utility modules ----------
module centered_box_xy(l, w, h) {
    translate([-inch(l)/2, -inch(w)/2, 0])
        cube([inch(l), inch(w), inch(h)]);
}
//
module slab_body(l, w, h) {
    centered_box_xy(l, w, h);
}
//
module pmt_block(l, w, h, x_start, z_start, y_center=0) {
    translate([inch(x_start), inch(y_center - w/2), inch(z_start)])
        cube([inch(l), inch(w), inch(h)]);
}
//
// Oblique PMT made the same basic way as the guide: a hull between two equal-size
// rectangular end faces, with the far face shifted upward. This keeps the PMT
// pointing in the same direction as the guide without the odd rotation behavior
// seen in the previous version.
module oblique_pmt_same_as_guide(l, w, h, rise, x_start, z_start, y_center=0) {
    hull() {
        translate([inch(x_start), inch(y_center - w/2), inch(z_start)])
            cube([EPS, inch(w), inch(h)]);

        translate([inch(x_start + l) - EPS, inch(y_center - w/2), inch(z_start + rise)])
            cube([EPS, inch(w), inch(h)]);
    }
}

// Constant-thickness guide that can rise diagonally as it extends outward.
// The attached face starts at z_base_start and the outer face is shifted up by `rise`.
module side_attached_constant_thickness_guide(l, w1, w2, thickness, rise, x_attach, z_base_start=0) {
    hull() {
        translate([inch(x_attach), -inch(w1)/2, inch(z_base_start)])
            cube([EPS, inch(w1), inch(thickness)]);

        translate([inch(x_attach + l) - EPS, -inch(w2)/2, inch(z_base_start + rise)])
            cube([EPS, inch(w2), inch(thickness)]);
    }
}

module axes(len=8) {
    color("red")   cube([inch(len), inch(0.15), inch(0.15)]);
    color("green") cube([inch(0.15), inch(len), inch(0.15)]);
    color("blue")  cube([inch(0.15), inch(0.15), inch(len)]);
}

module shelf_unit() {
    color("silver") {
        for (xsign = [-1, 1], ysign = [-1, 1]) {
            translate([
                xsign * (inch(SHELF_W)/2 - inch(POST_SIZE)/2),
                ysign * (inch(SHELF_D)/2 - inch(POST_SIZE)/2),
                0
            ])
                cube([inch(POST_SIZE), inch(POST_SIZE), inch(SHELF_H)]);
        }

        for (z0 = SHELF_ZS) {
            translate([-inch(SHELF_W)/2, -inch(SHELF_D)/2, inch(z0)])
                cube([inch(SHELF_W), inch(SHELF_D), inch(SHELF_THICK)]);
        }
    }
}

module maybe_rotate_detector() {
    if (ROTATE_DETECTORS_90)
        rotate([0, 0, 90]) children();
    else
        children();
}

// ---------- Detector assemblies ----------
module top_slab_assembly() {
    maybe_rotate_detector() {
        color([0.2, 0.55, 0.95, 0.65])
            slab_body(TOP_SLAB_L, TOP_SLAB_W, TOP_SLAB_H);

        // Top PMT attached at the slab edge, with its bottom flush to slab bottom.
        color([0.22, 0.22, 0.22, 0.95])
            pmt_block(
                TOP_PMT_L,
                TOP_PMT_W,
                TOP_PMT_H,
                TOP_SLAB_L/2,
                0,
                0
            );
    }
}

module bottom_slab_assembly() {
    maybe_rotate_detector() {
        color([0.15, 0.70, 0.80, 0.65])
            slab_body(BOT_SLAB_L, BOT_SLAB_W, BOT_SLAB_H);

        // Bottom guide is flush with the slab: same bottom, same top, no extra rise.
        color([0.70, 0.70, 0.75, 0.90])
            side_attached_constant_thickness_guide(
                BOT_GUIDE_L,
                BOT_GUIDE_W1,
                BOT_GUIDE_W2,
                BOT_GUIDE_H,
                BOT_GUIDE_RISE,
                BOT_SLAB_L/2,
                0
            );

        // Bottom PMT begins at the outer edge of the guide.
        // Its bottom is flush with the guide bottom.
        color([0.22, 0.22, 0.22, 0.95])
            pmt_block(
                BOT_PMT_L,
                BOT_PMT_W,
                BOT_PMT_H,
                BOT_SLAB_L/2 + BOT_GUIDE_L,
                0,
                0
            );
    }
}

module middle_slab_assembly() {
    maybe_rotate_detector() {
        color([0.25, 0.82, 0.55, 0.65])
            slab_body(MID_SLAB_L, MID_SLAB_W, MID_SLAB_H);

        // Constant-thickness diagonal guide attached to slab outer edge.
        color([0.78, 0.78, 0.83, 0.90])
            side_attached_constant_thickness_guide(
                MID_GUIDE_L,
                MID_GUIDE_W1,
                MID_GUIDE_W2,
                MID_GUIDE_H,
                MID_GUIDE_RISE,
                MID_SLAB_L/2,
                0
            );

        // Best-effort 2x2 PMT cluster at the guide exit.
        // Do the PMTs the same way as the guide: use oblique prisms built with hull().
        // That keeps them visually parallel to the guide in side view.
        // The bottoms start flush with the guide bottom at the exit face.
        x_front = MID_SLAB_L/2 + MID_GUIDE_L;
        z_front = MID_GUIDE_RISE;
        y_top =  MID_PMT_W/2 + MID_PMT_GAP_Y/2;
        y_bot = -MID_PMT_W/2 - MID_PMT_GAP_Y/2;

        color([0.18, 0.18, 0.18, 0.95]) {
            oblique_pmt_same_as_guide(MID_PMT_L, MID_PMT_W, MID_PMT_H, MID_PMT_RISE, x_front,             z_front, y_top);
            oblique_pmt_same_as_guide(MID_PMT_L, MID_PMT_W, MID_PMT_H, MID_PMT_RISE, x_front,             z_front, y_bot);
            oblique_pmt_same_as_guide(MID_PMT_L, MID_PMT_W, MID_PMT_H, MID_PMT_RISE, x_front + MID_PMT_L, z_front + MID_PMT_RISE, y_top);
            oblique_pmt_same_as_guide(MID_PMT_L, MID_PMT_W, MID_PMT_H, MID_PMT_RISE, x_front + MID_PMT_L, z_front + MID_PMT_RISE, y_bot);
        }
    }
}

// ---------- Scene placement ----------
module exploded_layout() {
    dx = inch(85);
    translate([-dx, 0, 0]) bottom_slab_assembly();
    middle_slab_assembly();
    translate([ dx, 0, 0]) top_slab_assembly();
}

module shelf_layout() {
    if (SHOW_SHELF) shelf_unit();

    translate([0, 0, inch(SHELF_ZS[0] + SHELF_THICK)]) bottom_slab_assembly();
    translate([0, 0, inch(SHELF_ZS[1] + SHELF_THICK)]) middle_slab_assembly();
    translate([0, 0, inch(SHELF_ZS[2] + SHELF_THICK)]) top_slab_assembly();
}

if (SHOW_AXES) axes();

if (EXPLODED_VIEW)
    exploded_layout();
else
    shelf_layout();
