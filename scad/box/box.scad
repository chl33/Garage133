// Copyright (c) 2024 Chris Lee and contibuters.
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
space_above_board = 2;
space_below_board = 3;
inner_dims = (board_dims
	      + Z*(space_above_board+space_below_board)
	      + 2*gap*ones);
outer_dims = (inner_dims
	      + 2*ones*wall_thickness
	      + [2, 2, 0] * corner_radius);

// cutout for oled screen
oled_o = [16.5, 7];
oled_d = [12, 28];
sonar_co_o = [34, 26];
sonar_co_d = [15, 15];
relay1_co_o = [48, 29];
relay1_co_d = [10.5, 6.5];
relay2_co_o = [49, 11.5];
relay2_co_d = [9.5, 7];
pirl_co_o = [45.8, 4];
pirl_co_d = [13., 7];

top_cutouts = [[oled_o, oled_d],
	       [sonar_co_o, sonar_co_d],
	       [relay1_co_o, relay1_co_d],
	       [relay2_co_o, relay2_co_d],
	       [pirl_co_o, pirl_co_d],
	       ];

usb_cutout = [[30, wall_thickness+space_below_board+board_thickness-1], [9.5, 3.5]];
yp_cutouts = [usb_cutout];

// humps is a list of [offset-xy, outer_dims]
oled_ho = [14, 0];
oled_hd = [17, outer_dims[1], 12];
relay_hd = [30, outer_dims[1], 14];
relay_ho = [outer_dims[0]-relay_hd[0], 0];
humps = [[oled_ho, oled_hd], [relay_ho, relay_hd]];

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
		  yp_cutouts=yp_cutouts,
		  corner_radius=corner_radius,
		  humps=humps,
		  top=top,
		  screw_tab_d=10);
      if (top) {
	in_Garage133_board_frame(board_height=true)
	  shtc3_window(shtc3_loc, space_above_board+wall, wall, false, z_gap=-1);
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
      in_Garage133_board_frame(board_height=true)
	shtc3_window(shtc3_loc, space_above_board+wall, wall, true, z_gap=-1);
    }
  }
}
