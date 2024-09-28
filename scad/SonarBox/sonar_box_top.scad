include <sonar_box.scad>

translate([0, outer[1], outer[2]]) rotate(180, X) sonar_box(true);
