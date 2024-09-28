include <ball_and_socket.scad>

brace_len = 30;
brace_width = 70;
brace_hole_d = 4;
brace_wall = 1;

module corner_leg() {
  $fn = 20;
  difference() {
    cube([brace_len, brace_width, brace_wall]);
    translate([brace_len/2, brace_width-8, -brace_wall])
      cylinder(3*brace_wall, brace_hole_d/2, brace_hole_d/2);
  }
}

union() {
  corner_leg();
  rotate(-90, Y) corner_leg();

  difference() {
    $fn=40;
    translate([-brace_wall, stalk_radius+3, 0])
      rotate(-45, Z) rotate (135, X) union() {
      ball_socket(ball_radius, socket_stalk_height, stalk_radius, socket_lock);
      difference() {
	sphere(stalk_radius);
	translate([-ball_radius, -ball_radius, 0])
	  cube([2*ball_radius, 2*ball_radius, ball_radius]);
      }
    }
    translate([-epsilon, -stalk_radius-1, brace_wall-epsilon])
      cube([stalk_radius, 2+brace_width, stalk_radius]);
  }
}

//ball_socket();
