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
space_above_board = 3;
space_below_board = 3;
inner_dims = (board_dims
	      + Z*(space_above_board+space_below_board)
	      + 2*gap*ones);
outer_dims = (inner_dims
	      + 2*ones*wall_thickness
	      + [2, 2, 0] * corner_radius);

// cutout for oled screen
oled_o = [15.5, 8];
oled_d = [12, 28];
sonar_co1_o = [39.5, 26];
sonar_co1_d = [29, 17];
relay1_co_o = [29.5, 3];
relay1_co_d = [33, 7];

top_cutouts = [[sonar_co1_o, sonar_co1_d],
       	       [relay1_co_o, relay1_co_d],
	       ];

//usb_cutout = [[63, wall_thickness+space_below_board+board_thickness-1], [9.5, 3.5]];
//yp_cutouts = [usb_cutout];

oled_off = [13.5, 0, outer_dims[2]-wall_thickness];
oled_out = [15.5, outer_dims[1], 10];
oled_inn = oled_out - wall_thickness * [2, 2, 1];

// humps is a list of [offset-xy, outer_dims]
relay_hd = [30, outer_dims[1], 14];
relay_ho = [outer_dims[0]-relay_hd[0], 0];
humps = [[relay_ho, relay_hd]];

module in_Garage133_board_frame(board_height=false) {
  zoffset = wall_thickness + (board_height ? space_below_board + 2*gap + board_thickness : 0);
  //  zoffset = wall_thickness + (board_height ? space_below_board : 0);
  in_board_frame(outer_dims, board_dims, zoffset) children();
}
module Garage133_box(top) {
  wall = wall_thickness;
  shtc3_loc = [9, 0.6, 0];

  difference() {
    union() {
      project_box(outer_dims,
		  wall_thickness=wall_thickness,
		  gap=gap,
		  snaps_on_sides=true,
		  top_cutouts=top_cutouts,
		  corner_radius=corner_radius,
		  humps=humps,
		  top=top);
      if (top) {
	translate(oled_off) cube(oled_out);
	// oled_inn
	in_Garage133_board_frame(board_height=true)
	  shtc3_window(shtc3_loc, space_above_board+wall, wall, false, z_gap=-1);
	screw_tab_d = 10;
	translate([outer_dims[0]/2+15, outer_dims[1], 0])
	  screw_tab(tab_width=screw_tab_d, thickness=2*wall, screw_radius=2);
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
      translate(oled_off + wall_thickness * [1, 1, -0.001]) cube(oled_inn);
      translate(oled_off + [2, 9, oled_inn[2]-0.01]) cube([12, 29, wall_thickness+2]);
      in_Garage133_board_frame(board_height=true)
	shtc3_window(shtc3_loc, space_above_board+wall, wall, true, z_gap=-1);
      // usb
      translate([27.9,
		 outer_dims[1]-wall_thickness-1,
		 wall_thickness+space_below_board+board_thickness-1])
	cube([11, wall_thickness+2, 4]);
    }
  }
}
