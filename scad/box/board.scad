// Copyright (c) 2026 Chris Lee and contributors.
// Licensed under the MIT license. See LICENSE file in the project root for details.

include <ProjectBox/project_box.scad>

board_thickness = 1.6;
pad_space = 2.54;
board_dims = [93.345, 39.37, board_thickness];

module Garden133_to_oled_frame() {
  u = pad_space;
  translate([12.5, 0.8, 13]) children();
}

module oled() {
  s = inch * 0.1;
  pin_len = 4;
  color("silver") {
    for (i = [0: 3]) {
      translate([s*i+pad_space, pad_space/2, -pin_len]) cube([0.25, 0.25, pin_len]);
    }
  }
  color("gray") cube([12, 38, 1]);
  translate([0, 5.5, 1]) color("black") cube([12, 28, 1]);
}


module Garage133_board() {
  u = pad_space;

  // Board imported from KiCad (VRML) -> Blender
  translate([board_dims[0]/2, board_dims[1]/2, board_dims[2]/2]) color("white")
    import(file="../../KiCAD/Garage133.stl", convexity=3);

  Garden133_to_oled_frame() oled();
}
