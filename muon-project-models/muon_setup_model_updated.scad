// =============================================================
// MUON DETECTOR SETUP
// =============================================================
//
// IMPORTANT IDEA:
// OpenSCAD does NOT force any real-world unit system.
// 1 OpenSCAD unit = 1 inch
//
// -------------------------------------------------------------
// COORDINATE SYSTEM USED IN THIS MODEL
// -------------------------------------------------------------
// x = length direction (left/right in the side view)
// y = width direction  (into/out of the screen in the side view)
// z = vertical direction (up/down)
//
// Every slab is centered in x and y, and starts at z = 0.
// So a slab with height 2.125 goes from z = 0 up to z = 2.125.
//
// -------------------------------------------------------------
// WHAT THIS FILE CONTAINS
// -------------------------------------------------------------
// 1. A simple 3-shelf rack
// 2. Top detector: slab + PMT
// 3. Bottom detector: slab + flush light tunnel + PMT
// 4. Middle detector: slab + diagonal light tunnel + diagonal PMTs
//
// The middle detector PMTs are still a best-effort 2x2 arrangement,
// because exact side-to-side PMT positions were not provided.
// =============================================================


// -------------------------------------------------------------
// SMALL HELPER VALUE
// -------------------------------------------------------------
// EPS is a tiny length used when making hull()-based shapes.
// If we used a face with exactly zero thickness, OpenSCAD would not
// have a real 3D object to hull together.
// So we use a very tiny thickness instead.
EPS = 0.01;


// -------------------------------------------------------------
// DISPLAY TOGGLES
// -------------------------------------------------------------
// Turn these true/false depending on what you want to see.
SHOW_SHELF = true;
EXPLODED_VIEW = false;   // true = separate the detectors for inspection
SHOW_AXES = false;       // true = show x/y/z guide axes
ROTATE_DETECTORS_90 = true;


// -------------------------------------------------------------
// SHELF DIMENSIONS
// -------------------------------------------------------------
// All numbers below are treated directly as inches.
SHELF_W = 36;
SHELF_D = 14;
SHELF_H = 36;
SHELF_THICK = 1;
POST_SIZE = 1;

// Shelf z-heights.
// These are the heights of the shelf BOARDS themselves.
// The actual detectors sit on top of those boards.
SHELF_ZS = [0, 13, 30];


// -------------------------------------------------------------
// TOP DETECTOR DIMENSIONS
// -------------------------------------------------------------
TOP_SLAB_L = 43.625;
TOP_SLAB_W = 25.875;
TOP_SLAB_H = 2.25;

TOP_PMT_L = 6.25;
TOP_PMT_W = 3.25;
TOP_PMT_H = 3.5;


// -------------------------------------------------------------
// BOTTOM DETECTOR DIMENSIONS
// -------------------------------------------------------------
BOT_SLAB_L = 49.5;
BOT_SLAB_W = 30.125;
BOT_SLAB_H = 2.125;

BOT_GUIDE_L = 13.125;
BOT_GUIDE_W1 = 30.125;
BOT_GUIDE_W2 = 4.0;
BOT_GUIDE_H = 2.125;
BOT_GUIDE_RISE = 0.0;   // guide stays flush with slab, so no upward rise

BOT_PMT_L = 6.5;
BOT_PMT_W = 4.0;
BOT_PMT_H = 2.625;


// -------------------------------------------------------------
// MIDDLE DETECTOR DIMENSIONS
// -------------------------------------------------------------
MID_SLAB_L = 48.0;
MID_SLAB_W = 30.625;
MID_SLAB_H = 2.125;

MID_GUIDE_L = 14.75;
MID_GUIDE_W1 = 30.625;
MID_GUIDE_W2 = 3;
MID_GUIDE_H = 2.125;

MID_PMT_L = 2;
MID_PMT_W = 1.6;
MID_PMT_H = 2.125;
MID_PMT_GAP_Y = 0.0;

// You asked for the middle add-on assembly to reach a total height of 15.5 in.
// Here that means:
//   from z = 0 at the bottom of the slab/guide
//   up to the highest point of the outermost PMT
MID_TOTAL_HEIGHT = 15.5;

// The guide and PMTs all follow the same slope.
// The sloped run goes across:
//   guide length + first PMT length + second PMT length
MID_TOTAL_RUN = MID_GUIDE_L + 2 * MID_PMT_L;

// Since the PMT thickness itself is 2.125, the bottom surface must rise by:
//   total desired top height - PMT thickness
MID_TOTAL_RISE = MID_TOTAL_HEIGHT - MID_PMT_H;

// Rise per inch of horizontal run
MID_SLOPE_PER_IN = MID_TOTAL_RISE / MID_TOTAL_RUN;

// Rise from the start of the guide to the end of the guide
MID_GUIDE_RISE = MID_GUIDE_L * MID_SLOPE_PER_IN;

// Rise across one PMT length
MID_PMT_RISE = MID_PMT_L * MID_SLOPE_PER_IN;


// =============================================================
// BASIC BUILDING BLOCK MODULES
// =============================================================

// -------------------------------------------------------------
// centered_box_xy(l, w, h)
// -------------------------------------------------------------
// Makes a rectangular box centered in x and y.
// z starts at 0.
//
// So:
//   x goes from -l/2 to +l/2
//   y goes from -w/2 to +w/2
//   z goes from 0 to h
module centered_box_xy(l, w, h) {
    translate([-l/2, -w/2, 0])
        cube([l, w, h]);
}


// A slab is just a centered box.
module slab_body(l, w, h) {
    centered_box_xy(l, w, h);
}


// -------------------------------------------------------------
// pmt_block(l, w, h, x_start, z_start, y_center)
// -------------------------------------------------------------
// Makes a simple rectangular PMT block.
//
// x_start = where the PMT begins in x
// z_start = where the PMT bottom begins in z
// y_center = centerline of the PMT in y
module pmt_block(l, w, h, x_start, z_start, y_center = 0) {
    translate([x_start, y_center - w/2, z_start])
        cube([l, w, h]);
}
//

// -------------------------------------------------------------
// side_attached_constant_thickness_guide(...)
// -------------------------------------------------------------
// This makes the light tunnel / trapezoid.
//
// It uses hull() between two thin rectangular end faces:
// - the first face is the wide face attached to the slab
// - the second face is the narrow face at the outer end
//
// If rise = 0, the guide is flat and flush.
// If rise > 0, the guide slopes upward as it goes outward.
module side_attached_constant_thickness_guide(
    l,
    w1,
    w2,
    thickness,
    rise,
    x_attach,
    z_base_start = 0
) {
    hull() {
        // Wide face where the guide touches the slab
        translate([x_attach, -w1/2, z_base_start])
            cube([EPS, w1, thickness]);

        // Narrow outer face, shifted upward by "rise"
        translate([x_attach + l - EPS, -w2/2, z_base_start + rise])
            cube([EPS, w2, thickness]);
    }
}


// -------------------------------------------------------------
// oblique_pmt_same_as_guide(...)
// -------------------------------------------------------------
// This makes a PMT the same way the guide is made.
//
// Why do it this way?
// Because simply rotating a rectangular PMT looked wrong in the side view.
// Building it with hull() keeps it visually aligned with the guide.
module oblique_pmt_same_as_guide(
    l,
    w,
    h,
    rise,
    x_start,
    z_start,
    y_center = 0
) {
    hull() {
        // Starting PMT face
        translate([x_start, y_center - w/2, z_start])
            cube([EPS, w, h]);

        // Ending PMT face, moved upward by "rise"
        translate([x_start + l - EPS, y_center - w/2, z_start + rise])
            cube([EPS, w, h]);
    }
}


// -------------------------------------------------------------
// axes(len)
// -------------------------------------------------------------
// Optional helper axes to understand orientation.
module axes(len = 8) {
    color("red")   cube([len, 0.15, 0.15]);
    color("green") cube([0.15, len, 0.15]);
    color("blue")  cube([0.15, 0.15, len]);
}


// =============================================================
// SHELF MODULE
// =============================================================

module shelf_unit() {
    color("silver") {

        // Four vertical corner posts
        for (xsign = [-1, 1], ysign = [-1, 1]) {
            translate([
                xsign * (SHELF_W/2 - POST_SIZE/2),
                ysign * (SHELF_D/2 - POST_SIZE/2),
                0
            ])
                cube([POST_SIZE, POST_SIZE, SHELF_H]);
        }

        // Three shelf boards
        for (z0 = SHELF_ZS) {
            translate([-SHELF_W/2, -SHELF_D/2, z0])
                cube([SHELF_W, SHELF_D, SHELF_THICK]);
        }
    }
}


// =============================================================
// ORIENTATION HELPER
// =============================================================

// This rotates each detector assembly by 90 degrees in the x-y plane.
// If you set ROTATE_DETECTORS_90 = false, the detectors go back to their
// unrotated orientation.
module maybe_rotate_detector() {
    if (ROTATE_DETECTORS_90)
        rotate([0, 0, 90]) children();
    else
        children();
}


// =============================================================
// DETECTOR ASSEMBLIES
// =============================================================

// -------------------------------------------------------------
// TOP DETECTOR
// -------------------------------------------------------------
module top_slab_assembly() {
    maybe_rotate_detector() {

        // Top slab
        color([0.2, 0.55, 0.95, 0.65])
            slab_body(TOP_SLAB_L, TOP_SLAB_W, TOP_SLAB_H);

        // Top PMT
        // Starts at the slab edge in +x direction.
        // Bottom of PMT is flush with bottom of slab (z = 0).
        color([0.22, 0.22, 0.22, 0.95])
            pmt_block(
                TOP_PMT_L,
                TOP_PMT_W,
                TOP_PMT_H,
                TOP_SLAB_L / 2,
                0,
                0
            );
    }
}


// -------------------------------------------------------------
// BOTTOM DETECTOR
// -------------------------------------------------------------
module bottom_slab_assembly() {
    maybe_rotate_detector() {

        // Bottom slab
        color([0.15, 0.70, 0.80, 0.65])
            slab_body(BOT_SLAB_L, BOT_SLAB_W, BOT_SLAB_H);

        // Bottom guide / light tunnel
        // This is attached at the slab edge and stays flush with the slab.
        color([0.70, 0.70, 0.75, 0.90])
            side_attached_constant_thickness_guide(
                BOT_GUIDE_L,
                BOT_GUIDE_W1,
                BOT_GUIDE_W2,
                BOT_GUIDE_H,
                BOT_GUIDE_RISE,
                BOT_SLAB_L / 2,
                0
            );

        // Bottom PMT
        // Starts at the outer end of the guide.
        // PMT bottom is flush with guide bottom.
        color([0.22, 0.22, 0.22, 0.95])
            pmt_block(
                BOT_PMT_L,
                BOT_PMT_W,
                BOT_PMT_H,
                BOT_SLAB_L / 2 + BOT_GUIDE_L,
                0,
                0
            );
    }
}


// -------------------------------------------------------------
// MIDDLE DETECTOR
// -------------------------------------------------------------
module middle_slab_assembly() {
    maybe_rotate_detector() {

        // Middle slab
        color([0.25, 0.82, 0.55, 0.65])
            slab_body(MID_SLAB_L, MID_SLAB_W, MID_SLAB_H);

        // Middle guide / light tunnel
        // This one slopes upward and has constant thickness.
        color([0.78, 0.78, 0.83, 0.90])
            side_attached_constant_thickness_guide(
                MID_GUIDE_L,
                MID_GUIDE_W1,
                MID_GUIDE_W2,
                MID_GUIDE_H,
                MID_GUIDE_RISE,
                MID_SLAB_L / 2,
                0
            );

        // Where the guide ends in x and z.
        // The PMTs begin exactly there.
        x_front = MID_SLAB_L / 2 + MID_GUIDE_L;
        z_front = MID_GUIDE_RISE;

        // Two PMTs in +y / -y for the first row
        y_top =  MID_PMT_W / 2 + MID_PMT_GAP_Y / 2;
        y_bot = -MID_PMT_W / 2 - MID_PMT_GAP_Y / 2;

        // Middle PMTs
        // Built the same way as the guide so they point the same direction.
        // Current layout = 2x2 cluster, best estimate.
        color([0.18, 0.18, 0.18, 0.95]) {

            // First pair of PMTs, starting directly at the guide exit
            oblique_pmt_same_as_guide(
                MID_PMT_L, MID_PMT_W, MID_PMT_H,
                MID_PMT_RISE,
                x_front, z_front, y_top
            );

            oblique_pmt_same_as_guide(
                MID_PMT_L, MID_PMT_W, MID_PMT_H,
                MID_PMT_RISE,
                x_front, z_front, y_bot
            );

            // Second pair of PMTs, continuing the same slope farther outward
            oblique_pmt_same_as_guide(
                MID_PMT_L, MID_PMT_W, MID_PMT_H,
                MID_PMT_RISE,
                x_front + MID_PMT_L,
                z_front + MID_PMT_RISE,
                y_top
            );

            oblique_pmt_same_as_guide(
                MID_PMT_L, MID_PMT_W, MID_PMT_H,
                MID_PMT_RISE,
                x_front + MID_PMT_L,
                z_front + MID_PMT_RISE,
                y_bot
            );
        }
    }
}


// =============================================================
// WHOLE-SCENE LAYOUT
// =============================================================

// Exploded view: detectors spread apart so you can inspect them individually.
module exploded_layout() {
    dx = 85;

    translate([-dx, 0, 0]) bottom_slab_assembly();
    middle_slab_assembly();
    translate([ dx, 0, 0]) top_slab_assembly();
}


//

// Shelf view: detectors placed on the 3 shelves.
module shelf_layout() {

    if (SHOW_SHELF)
        translate([0,-12,0]) shelf_unit();
        translate([0,12,0]) shelf_unit();

    // Put each detector on top of its shelf board.
    translate([0, 0, SHELF_ZS[0] + SHELF_THICK]) bottom_slab_assembly();
    translate([0, 0, SHELF_ZS[1] + SHELF_THICK]) middle_slab_assembly();
    translate([0, 0, SHELF_ZS[2] + SHELF_THICK]) top_slab_assembly();
}


// =============================================================
// FINAL DRAW CALLS
// =============================================================

if (SHOW_AXES)
    axes();

if (EXPLODED_VIEW)
    exploded_layout();
else
    shelf_layout();
