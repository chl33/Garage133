// Copyright (c) 2024 Chris Lee and contibuters.
// Licensed under the MIT license. See LICENSE file in the project root for details.

include <sonar_box.scad>

translate([0, outer[1], outer[2]]) rotate(180, X) sonar_box(true);
