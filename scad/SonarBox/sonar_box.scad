// Copyright (c) 2024 Chris Lee and contibuters.
// Licensed under the MIT license. See LICENSE file in the project root for details.

include <MCAD/units.scad>
include <ball_and_socket.scad>

board_dims = [45, 20, 1];
board_corner_hole_radius = 0.7;
board_corner_hole_offset = 1.4;

above_board = 3;
below_board = 5;
gap = 0.2;

hole_radius = 16.5/2;
between_holes = 9.5;

connector_x = 12;
connector_z = 3;
// space below board to connector.
connector_offset_z = 1;

wall_thickness = 1.4;
screw_diameter = 3;

mount_width = screw_diameter + wall_thickness;
board_offset = gap+mount_width;

inner = (board_dims + [2,2,0]*board_offset + Z*(below_board+above_board));
outer = inner + [2,2,2]*wall_thickness;


module sonar_box(top) {
  wall = wall_thickness;

  x_offset = (inner[0] - 4*hole_radius - between_holes) / 2;
  y_offset = inner[1]/2 - hole_radius;

  $fn = 40;

  module screw_mount(x, y, rot) {
    w = mount_width;
    o = board_corner_hole_offset;
    translate([wall+x, wall+y, wall-epsilon]) rotate(rot, Z)
      cube([w, w, inner[2]]);
  }
  module screw_hole(x, y, rot) {
    r = screw_diameter/2;
    l = 6;
    translate([wall+x, wall+y, -epsilon]) rotate(rot, Z) translate([r, r, 0])
      cylinder(l, r, r);
  }

  screw_mount_x = [-epsilon, inner[0]+epsilon];
  screw_mount_y = [-epsilon, inner[1]+epsilon];

  module board_mount(x, y) {
    r = board_corner_hole_radius-0.15;
    w = 2 * (r+wall);
    pin_h = board_dims[2] + 0.5;
    translate([x, y, inner[2]+epsilon-above_board]) union() {
      translate([-w/2, -w/2, 0]) cube([w, w, above_board]);
      translate([0, 0, -pin_h+epsilon]) cylinder(pin_h, r, r);
    }
  }

  difference() {
    union() {
      // Outer shell
      difference() {
	cube(outer);
	translate([1,1,1]*wall) {
	  cube(inner);
	  translate([inner[0]/2, inner[1]/2, inner[2]-wall]) {
	    dx = between_holes/2 + hole_radius;
	    // Speaker holes
	    translate([-dx, 0, 0]) cylinder(3*wall, hole_radius, hole_radius);
	    translate([+dx, 0, 0]) cylinder(3*wall, hole_radius, hole_radius);

	    // Connector slot.
	    gap_to_slot = above_board + board_dims[2] + connector_offset_z;
	    translate([-connector_x/2-gap, -outer[1]/2-wall,
		       -inner[2]+wall-epsilon])
	      cube([connector_x+2*gap, 3*wall, inner[2]-gap_to_slot]);
	  }
	}
      }  // difference

      // Corners for m3 bolts to screw into.
      screw_mount(screw_mount_x[0], screw_mount_y[0], 0);
      screw_mount(screw_mount_x[1], screw_mount_y[0], 90);
      screw_mount(screw_mount_x[1], screw_mount_y[1], 180);
      screw_mount(screw_mount_x[0], screw_mount_y[1], 270);

      // Board mounts
      translate([outer[0]/2, outer[1]/2, wall-epsilon]) {
	dx = board_dims[0]/2 - board_corner_hole_offset;
	dy = board_dims[1]/2 - board_corner_hole_offset;

	board_mount(-dx, -dy);
	board_mount(-dx, +dy);
	board_mount(+dx, +dy);
	board_mount(+dx, -dy);
      }

      if (!top) {
	translate([outer[0]/2, outer[1]/2, -epsilon]) rotate(180, X)
	  ball_stalk(ball_radius=7.5, stalk_height=6, stalk_radius=4);
      }
    } // Union

    // Screw holes
    screw_hole(screw_mount_x[0], screw_mount_y[0], 0);
    screw_hole(screw_mount_x[1], screw_mount_y[0], 90);
    screw_hole(screw_mount_x[1], screw_mount_y[1], 180);
    screw_hole(screw_mount_x[0], screw_mount_y[1], 270);

    // Cut off bottom or top.
    if (top) {
      translate([-1, -1, -1])
	cube([2+outer[0], 2+outer[1], 1+wall_thickness+epsilon]);
    } else {
      translate([-1, -1, wall_thickness])
	cube([2+outer[0], 2+outer[1], outer[2]]);
    }
  }  // difference
}
