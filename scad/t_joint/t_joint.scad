// Brace for joining two wood peices to make a T-frame for mounting sonars in the garage.
include <MCAD/units.scad>

dims1 = [1.5 * inch, 1.25 * inch];
dims2 = [1.25 * inch, 5/8 * inch];

width = 2;

inner1 = [dims1[0], dims1[1], dims1[0]];
outer1 = inner1 + 2*width*[1, 1, 1];

inner2 = [dims2[0], dims2[1], dims2[0]];
outer2 = inner2 + 2*width*[1, 1, 1];

module tjoint() {
  difference() {
    cube(outer1);
    translate([-1, width, width]) {
      cube(inner1 + [2 + width * 2, 0, 0]);
    }
    translate([outer1[0]/2, outer1[1]-width-1, outer1[2]/2]) rotate([-90,0,0]) cylinder(10, 2, 2);
  }
  tx = [(outer1[0] - outer2[0])/2, -outer2[1]+epsilon, (outer1[2]-outer2[2])/2];
  translate(tx) {
    difference() {
      cube(outer2);
      translate([width, width, -1]) {
	cube(inner2 + [0, 0, 2 + 2 * width]);
      }
      translate([1*outer2[0]/4, -1, outer2[2]/2]) rotate([-90,0,0]) cylinder(10, 2, 2);
      translate([3*outer2[0]/4, -1, outer2[2]/2]) rotate([-90,0,0]) cylinder(10, 2, 2);
    }
  }
}

tjoint();
