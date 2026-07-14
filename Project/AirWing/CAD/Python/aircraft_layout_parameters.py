"""Milestone 5 layout rules tied to approved ship datums."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class LayoutParameters:
    coordinate_system: str = "x=0 bow to x=476 stern; y port(-)/starboard(+); heading clockwise from +x"
    deck_contact_z_offset: float = 0.0
    aircraft_clearance_per_side: float = 0.20
    interference_threshold_mm3: float = 0.10
    deck_edge_margin: float = 0.30
    island_margin: float = 0.50
    weapons_margin: float = 0.50
    elevator_margin: float = 0.30
    catapult_margin: float = 0.20
    arresting_wire_margin: float = 0.20
    default_count_range: Tuple[int, int] = (28, 40)
    light_count_range: Tuple[int, int] = (12, 20)
    full_count_range: Tuple[int, int] = (36, 48)


def make_parameters() -> LayoutParameters:
    return LayoutParameters()
