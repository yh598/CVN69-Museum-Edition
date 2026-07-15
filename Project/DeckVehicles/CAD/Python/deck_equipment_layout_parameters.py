"""Milestone 6 support-equipment layout rules tied to approved datums."""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class LayoutParameters:
    coordinate_system: str = "x=0 bow to x=476 stern; y port(-)/starboard(+); z uses approved hull datum; heading clockwise from +x"
    interference_threshold_mm3: float = 0.10
    deck_edge_margin: float = 0.30
    aircraft_clearance: float = 0.30
    vehicle_clearance: float = 0.30
    fixed_obstacle_margin: float = 0.20
    light_count_range: Tuple[int, int] = (10, 18)
    default_count_range: Tuple[int, int] = (20, 35)
    full_count_range: Tuple[int, int] = (30, 50)
    target_counts: Tuple[int, int, int] = (14, 24, 32)


def make_parameters() -> LayoutParameters:
    return LayoutParameters()
