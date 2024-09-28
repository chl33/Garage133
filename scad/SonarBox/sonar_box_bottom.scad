include <sonar_box.scad>

translate([0, outer[1], wall_thickness]) rotate(180, X) sonar_box(false);

