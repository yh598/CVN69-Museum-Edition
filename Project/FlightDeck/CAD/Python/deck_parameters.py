"""Master parameters for the CVN-69 1:700 flight-deck reconstruction.

All values are model millimetres.  The source STL is used only to trace the
planform and locate flight-deck features; none of its triangles are reused in
the production BRep geometry.
"""

from dataclasses import dataclass
from typing import Tuple


Point2 = Tuple[float, float]


# Clockwise planform trace, starting at the port side of the stern.  Control
# points follow the deck-cap silhouettes visible in the five v0.4 reference
# bands.  Empty intervals between those bands are fair linear transitions.
OUTLINE_POINTS: Tuple[Point2, ...] = (
    (0.0, -4.8),
    (2.6, -13.8),
    (7.0, -18.6),
    (13.0, -20.1),
    (39.0, -19.2),
    (39.6, -31.5),
    (43.0, -32.8),
    (70.0, -33.9),
    (105.0, -34.1),
    (165.0, -34.4),
    (198.0, -34.8),
    (261.0, -36.0),
    (304.0, -36.4),
    (326.0, -36.7),
    (355.0, -19.8),
    (405.0, -17.3),
    (424.0, -17.0),
    (451.0, -15.8),
    (472.0, -15.2),
    (476.0, -15.0),
    (476.0, 14.5),
    (472.0, 16.7),
    (451.0, 17.8),
    (424.0, 18.8),
    (405.0, 18.5),
    (355.0, 19.0),
    (327.0, 37.0),
    (304.0, 36.9),
    (261.0, 36.1),
    (198.0, 35.3),
    (165.0, 34.5),
    (105.0, 34.5),
    (70.0, 35.0),
    (43.0, 34.0),
    (42.0, 31.5),
    (16.0, 31.0),
    (12.0, 22.5),
    (6.0, 21.0),
    (4.0, 15.0),
    (0.0, 14.0),
)


# Island cut-out traced from the source island base at approximately
# x=121.3..150.4 and y=18.8..35.8.  The reconstructed opening deliberately
# leaves at least 1.2 mm of deck-edge wall after fit clearance.
ISLAND_OPENING: Tuple[Point2, ...] = (
    (121.0, 19.2),
    (149.9, 19.2),
    (151.0, 22.0),
    (150.6, 33.0),
    (143.0, 33.0),
    (141.8, 31.8),
    (123.0, 31.8),
    (121.0, 29.5),
)


@dataclass(frozen=True)
class Elevator:
    name: str
    x0: float
    x1: float
    y0: float
    y1: float
    source_note: str


ELEVATORS: Tuple[Elevator, ...] = (
    Elevator("Elevator_1_Port", 40.5, 66.5, -31.8, -19.0, "section_01 port platform cluster"),
    Elevator("Elevator_2_Starboard", 46.0, 68.0, 20.0, 33.8, "section_01 starboard platform cluster"),
    Elevator("Elevator_3_Starboard", 154.0, 180.0, 20.1, 33.8, "section_02 starboard platform continuation"),
    Elevator("Elevator_4_Starboard", 228.5, 254.0, 20.0, 34.8, "section_03 starboard platform cluster"),
)


@dataclass(frozen=True)
class LinearFeature:
    name: str
    start: Point2
    end: Point2


CATAPULTS: Tuple[LinearFeature, ...] = (
    LinearFeature("Catapult_1_Bow_Port", (336.0, -7.5), (465.0, -7.0)),
    LinearFeature("Catapult_2_Bow_Starboard", (336.0, 8.0), (464.0, 7.0)),
    LinearFeature("Catapult_3_Waist_Inner", (150.0, -8.5), (315.0, -22.5)),
    LinearFeature("Catapult_4_Waist_Outer", (144.0, -20.0), (302.0, -32.0)),
)


@dataclass(frozen=True)
class DeckParameters:
    scale_denominator: int = 700
    overall_length: float = 476.0
    deck_thickness: float = 3.0
    minimum_wall: float = 1.2
    elevator_shelf_thickness: float = 1.2
    elevator_plate_thickness: float = 1.8
    fit_clearance_per_side: float = 0.25
    split_seams: Tuple[float, float] = (190.0, 330.0)
    glue_tongue_length: float = 7.0
    glue_tongue_width: float = 8.0
    glue_tongue_thickness: float = 1.2
    glue_socket_depth: float = 1.45
    raised_marking_width: float = 0.60
    raised_marking_height: float = 0.35
    catapult_width: float = 0.80
    catapult_height: float = 0.40
    arresting_wire_width: float = 0.50
    arresting_wire_height: float = 0.35
    tessellation_deflection: float = 0.08
    outline_points: Tuple[Point2, ...] = OUTLINE_POINTS
    island_opening: Tuple[Point2, ...] = ISLAND_OPENING
    elevators: Tuple[Elevator, ...] = ELEVATORS
    catapults: Tuple[LinearFeature, ...] = CATAPULTS


def make_parameters() -> DeckParameters:
    return DeckParameters()
