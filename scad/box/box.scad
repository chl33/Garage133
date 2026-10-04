// Copyright (c) 2026 Chris Lee and contributors.
// Licensed under the MIT license. See LICENSE file in the project root for details.

include <ProjectBox/project_box.scad>
include <ProjectBox/mounts.scad>
include <ProjectBox/oled91.scad>
include <ProjectBox/shtc3_window.scad>
include <board.scad>

ones = [1, 1, 1];

wall_thickness = 1;
gap = 0.2;
corner_radius = 2;

mount_offset = pad_space;
total_space_above_board = 4;
space_above_board = 0;
main_hump_above_board = total_space_above_board - space_above_board;
space_below_board = 3;
inner_dims = (board_dims
	      + Z*(space_above_board+space_below_board)
	      + 2*gap*ones);
outer_dims = (inner_dims
	      + 2*ones*wall_thickness
	      + [2, 2, 0] * corner_radius);

// -- Cutouts
//    OLED screen cutout
oled_o = [15.5, 8];
oled_d = [12, 28];
//    Sonar connector cutout
sonar_co1_o = [39.5, 25];
sonar_co1_d = [29, 17];
//    Relay connectors cutout
relay1_co_o = [34.5, 2.5];
relay1_co_d = [33.5, 7];

top_cutouts = [[sonar_co1_o, sonar_co1_d],
       	       [relay1_co_o, relay1_co_d],
	       ];

// humps is a list of [offset-xy, outer_dims]

// board through relay box has space for USB-C connector & esp module.
relay_end_offset = 8.5;
main_ho = [0, 0, 0];
main_hd = [outer_dims[0]-relay_end_offset, outer_dims[1], main_hump_above_board];

// OLED hump
oled_off = [13.5, 0, 0];
oled_out = [15.5, outer_dims[1], 10 + main_hump_above_board];

// relay hump
relay_hd = [30-relay_end_offset, outer_dims[1], 12 + main_hump_above_board];
relay_ho = [outer_dims[0]-relay_hd[0]-relay_end_offset, 0];
humps = [[main_ho, main_hd], [oled_off, oled_out], [relay_ho, relay_hd]];

module in_Garage133_board_frame(board_height=false) {
  zoffset = wall_thickness + (board_height ? space_below_board + 2*gap + board_thickness : 0);
  //  zoffset = wall_thickness + (board_height ? space_below_board : 0);
  in_board_frame(outer_dims, board_dims, zoffset) children();
}
module Garage133_box(top) {
  wall = wall_thickness;
  shtc3_loc = [88.6, 16, 0];

  module write(x, y, msg) {
    color("black") linear_extrude(0.5) translate([x, y, 0]) text(msg, size=4);
  }

  difference() {
    union() {
      project_box(outer_dims,
		  wall_thickness=wall_thickness,
		  gap=gap,
		  snaps_on_sides=true,
		  top_cutouts=top_cutouts,
		  corner_radius=corner_radius,
		  humps=humps,
		  hump_corner_radius=[corner_radius, 0, 1],
		  top=top);
      if (top) {
	in_Garage133_board_frame(board_height=true)
	  shtc3_window(shtc3_loc, space_above_board+wall, wall, false, z_gap=-1);
	screw_tab_d = 10;
	translate([outer_dims[0]/2+15, outer_dims[1], 0])
	  screw_tab(tab_width=screw_tab_d, thickness=2*wall, screw_radius=2);

	// Raised lettering
	translate([0, 0, outer_dims[2]+main_hump_above_board-epsilon]) {
	  translate([8, 9, 0]) rotate([0, 0, 90]) write(0, 0, "Garage133");
	  translate([sonar_co1_o[0] - 6, sonar_co1_o[1]+11, 0]) {
	    write(0, 0, "L");
	    write(0, -10, "R");
	  }
	  translate([sonar_co1_o[0] + 4, sonar_co1_o[1]-6, 0]) {
	    write(0, 0, "FT");
	    write(13, 0, "BK");
	  }
	  translate([relay1_co_o[0]+ 1, relay1_co_o[1]+8, 0]) {
	    write(0, 0, "PIRL");
	    write(15, 0, "FT");
	    write(25, 0, "BK");
	  }
	}

      } else {
	// Stuff to add on bottom.
	in_Garage133_board_frame() {
	  at_corners(board_dims+1.0*X, mount_offset, x_extra=-1.2, y_extra=-0.2)
	    screw_mount(space_below_board, wall, 2.5/2);
	}
	translate([12.4, outer_dims[1]-pad_space*2.33, 0])
	  screw_mount(space_below_board, wall, 2.5/2);
      }
    }
    // Cut outs.
    if (top) {
      translate(oled_off + [2, 9, outer_dims[2]+oled_out[2]-3*wall-0.01])
	cube([12, 29, wall_thickness+2]);
      in_Garage133_board_frame(board_height=true)
	shtc3_window(shtc3_loc, space_above_board+wall, wall, true, z_gap=-1);
      // usb
      translate([27.9,
		 outer_dims[1]-wall_thickness-1,
		 wall_thickness+space_below_board+board_thickness-2])
	cube([11, wall_thickness+2, 6]);
    }
  }
}
