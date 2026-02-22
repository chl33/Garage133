// Copyright (c) 2026 Chris Lee and contributors.
// Licensed under the MIT license. See LICENSE file in the project root for details.

include <sonar_box.scad>

top = true;
show_vitamins = true;
pad_dist = 2.54;

module board() {
  dims = board_dims;
  r = board_corner_hole_radius;
  o = board_corner_hole_offset;
  difference() {
    $fn = 20;
    color("green") cube(dims);
    translate([o, o, -1]) cylinder(2+dims[2], r, r);
    translate([dims[0]-o, o, -1]) cylinder(2+dims[2], r, r);
    translate([dims[0]-o, dims[1]-o, -1]) cylinder(2+dims[2], r, r);
    translate([o, dims[1]-o, -1]) cylinder(2+dims[2], r, r);
  }

  wire_dist = pad_dist * 3;
  translate([(dims[0]-wire_dist)/2, 1, dims[2]]) {
    for (i = [0:3]) translate(i*pad_dist*X) {
	d = pad_dist * 0.1;
	translate(-3*Z) { cube([d, d, 3]); }
	translate([0, -10+epsilon, -3+epsilon]) cube([d, 10, d]);
      }
  }
}

sonar_box(top);

if (show_vitamins) {
  offset = board_offset + wall_thickness;
  translate([offset, offset,
	     outer[2]-(2*wall_thickness+above_board+board_dims[2])])
  board();
}
