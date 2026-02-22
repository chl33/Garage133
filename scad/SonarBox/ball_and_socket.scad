// Copyright (c) 2026 Chris Lee and contributors.
// Licensed under the MIT license. See LICENSE file in the project root for details.

include <MCAD/units.scad>

ball_radius = 15/2;
socket_gap = 0.0;
socket_wall = 0.8;
stalk_radius = 10/2;
stalk_height = 10;

socket_stalk_height = 5;
// This is the amount of the socket past half-sphere to lock in the ball
socket_lock = 2.5;

socket_cut_depth = 4;
socket_cut_width = 1.0;

mount_dims = [20, 20, 0.6];

module ball_stalk_test() {
  union() {
    cube(mount_dims);
    translate([mount_dims[0]/2, mount_dims[1]/2, mount_dims[2]-epsilon])
      ball_stalk(ball_radius, stalk_height, stalk_radius);
  }
}

module ball_stalk(ball_radius, stalk_height, stalk_radius) {
  $fn = 80;
  union() {
    cylinder(stalk_height, stalk_radius, stalk_radius);
    translate([0, 0, stalk_height + ball_radius - stalk_radius])
      sphere(ball_radius);
  }
}

module ball_socket_test() {

  union() {
    cube(mount_dims);
    translate([mount_dims[0]/2, mount_dims[1]/2, mount_dims[2]-epsilon])
      ball_socket(ball_radius, socket_stalk_height, stalk_radius, socket_lock);
  }
}

module ball_socket(ball_radius, socket_stak_height, stalk_radius, socket_lock) {
  $fn = 80;

  in_r = ball_radius + socket_gap;
  out_r = in_r + socket_wall;

  socket_center_z = (mount_dims[2]-epsilon + socket_stalk_height
		     + out_r - stalk_radius);

  difference() {
    union() {
      cylinder(socket_stalk_height+out_r, stalk_radius, stalk_radius);
      translate([0, 0, socket_stalk_height + out_r - stalk_radius]) {
	sphere(out_r);
      }
    }
    // Carve-out socket "bowl"
    translate(socket_center_z*Z) sphere(in_r);

    d = out_r*2+2;
    // Cut off top of socket sphere.
    translate([-d/2-1, -d/2-1, socket_center_z+socket_lock]) cube([d, d,out_r]);

    // Cuts in top of socket for flexibility.
    cd = socket_cut_depth;
    cw = socket_cut_width;
    translate([-cw/2, -d/2-1, socket_center_z+socket_lock-cd])
      cube([cw, d+2, cd+1]);
    translate([-d/2-1, -cw/2, socket_center_z+socket_lock-cd])
      cube([d+2, cw, cd+1]);
  }
}

//ball_stalk_test();
//translate([25, 0, 0]) ball_socket_test();
