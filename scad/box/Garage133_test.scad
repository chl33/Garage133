// Copyright (c) 2025 Chris Lee and contibuters.
// Licensed under the MIT license. See LICENSE file in the project root for details.

include <board.scad>
include <box.scad>
include <gui.scad>

union() {
  if (show_box) Garage133_box(top);
  if (show_vitamins) {
    translate([wall_thickness+corner_radius,
	       wall_thickness+corner_radius,
	       space_below_board])
      Garage133_board();
  }
}
