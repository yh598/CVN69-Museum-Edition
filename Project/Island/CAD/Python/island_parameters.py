"""Authoritative parameters for Milestone 3 CVN-69 island reconstruction.

All values are model millimetres at 1:700.  Hull/deck datums and the island
opening are imported from the approved Milestone 2 parameter module.  The
source STL is not imported here and contributes no production triangles.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


Point2 = Tuple[float, float]
THIS_FILE = Path(__file__).resolve()
PROJECT = THIS_FILE.parents[3]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_INTEGRATION_MODULE = _load_module(
    "approved_integration_parameters_m3",
    PROJECT / "Integration" / "CAD" / "Python" / "integration_parameters.py",
)


def polygon_area(points: Tuple[Point2, ...]) -> float:
    return 0.5 * sum(
        x0 * y1 - x1 * y0
        for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1])
    )


def inset_polygon(points: Tuple[Point2, ...], distance: float) -> Tuple[Point2, ...]:
    """Miter-offset a simple polygon inward by ``distance``.

    The approved opening is a small, non-self-intersecting orthogonal/oblique
    polygon.  A line-intersection offset is deterministic and avoids relying on
    platform-dependent 2-D offset behaviour in OpenCascade.
    """

    if len(points) < 3:
        raise ValueError("A polygon needs at least three points")
    ccw = polygon_area(points) > 0.0
    shifted = []
    for left, right in zip(points, points[1:] + points[:1]):
        dx, dy = right[0] - left[0], right[1] - left[1]
        length = math.hypot(dx, dy)
        if length <= 1.0e-12:
            raise ValueError("Polygon contains a zero-length edge")
        if ccw:
            nx, ny = -dy / length, dx / length
        else:
            nx, ny = dy / length, -dx / length
        shifted.append(((left[0] + distance * nx, left[1] + distance * ny), (dx, dy)))

    result = []
    for index in range(len(points)):
        point_a, direction_a = shifted[index - 1]
        point_b, direction_b = shifted[index]
        cross = direction_a[0] * direction_b[1] - direction_a[1] * direction_b[0]
        if abs(cross) <= 1.0e-12:
            raise ValueError("Adjacent polygon edges are parallel")
        delta = (point_b[0] - point_a[0], point_b[1] - point_a[1])
        scale = (delta[0] * direction_b[1] - delta[1] * direction_b[0]) / cross
        result.append(
            (
                point_a[0] + scale * direction_a[0],
                point_a[1] + scale * direction_a[1],
            )
        )
    return tuple(result)


@dataclass(frozen=True)
class IslandParameters:
    integration: object = field(default_factory=_INTEGRATION_MODULE.make_parameters)
    version: str = "0.3.0-review"
    milestone: str = "Milestone 3 — Island Reconstruction and Integration"
    configuration_period: str = "2023-10-14 through 2024-07-14 deployment; visible fit frozen at 2024-06-30"

    # Glue-only deck interface.
    interface_clearance_per_side: float = 0.25
    interface_plug_depth: float = 2.40
    foundation_flange_offset: float = 0.90
    foundation_flange_height: float = 1.50
    glue_channel_width: float = 0.60
    glue_channel_depth: float = 0.35

    # FDM rules.
    minimum_structural_wall: float = 1.20
    minimum_freestanding_mast: float = 0.80
    preferred_fragile_mast: float = 1.00
    minimum_raised_width: float = 0.50
    minimum_raised_height: float = 0.35
    minimum_engraved_width: float = 0.50
    minimum_engraved_depth: float = 0.30
    minimum_railing: float = 0.60
    minimum_antenna: float = 0.60
    preferred_print_envelope: float = 240.0
    tessellation_deflection: float = 0.055

    # Photo/source-reference-informed proportions above the approved deck top.
    lower_body_height: float = 9.50
    bridge_top_height: float = 16.50
    prifly_top_height: float = 15.20
    uptake_top_height: float = 20.00
    mast_platform_height: float = 29.20
    mast_yardarm_height: float = 35.60
    mast_top_height: float = 43.50
    secondary_mast_top_height: float = 25.00
    window_insert_thickness: float = 0.50
    marking_thickness: float = 0.35
    radar_panel_thickness: float = 0.80
    radar_rib_height: float = 0.35
    radar_rib_width: float = 0.50

    # Coupon envelope and structure.
    coupon_width: float = 40.0
    coupon_depth: float = 24.0
    coupon_base_thickness: float = 3.0
    coupon_female_thickness: float = 3.0

    def __post_init__(self):
        if self.interface_clearance_per_side != self.integration.deck.fit_clearance_per_side:
            raise ValueError("Island interface clearance must match the approved deck fit convention")
        if self.minimum_structural_wall < 1.20:
            raise ValueError("Structural wall minimum cannot be below 1.20 mm")
        if self.glue_channel_width < self.minimum_raised_width:
            raise ValueError("Glue channel is narrower than the printable line rule")
        if self.glue_channel_depth < self.minimum_engraved_depth:
            raise ValueError("Glue channel is shallower than the engraving rule")
        if self.mast_top_height <= self.mast_yardarm_height:
            raise ValueError("Mast top must be above the yardarm")

    @property
    def overall_length(self) -> float:
        return float(self.integration.overall_length)

    @property
    def deck_base_z(self) -> float:
        return float(self.integration.deck_base_z)

    @property
    def deck_top_z(self) -> float:
        return float(self.integration.deck_top_z)

    @property
    def opening_authoritative(self) -> Tuple[Point2, ...]:
        return tuple(
            (self.integration.deck_x_to_authoritative(x), float(y))
            for x, y in self.integration.deck.island_opening
        )

    @property
    def opening_bounds(self) -> Tuple[float, float, float, float]:
        xs = [point[0] for point in self.opening_authoritative]
        ys = [point[1] for point in self.opening_authoritative]
        return min(xs), min(ys), max(xs), max(ys)

    @property
    def opening_center(self) -> Point2:
        x0, y0, x1, y1 = self.opening_bounds
        return (0.5 * (x0 + x1), 0.5 * (y0 + y1))

    @property
    def interface_plug_points(self) -> Tuple[Point2, ...]:
        return inset_polygon(self.opening_authoritative, self.interface_clearance_per_side)

    @property
    def foundation_flange_points(self) -> Tuple[Point2, ...]:
        return inset_polygon(self.opening_authoritative, -self.foundation_flange_offset)

    @property
    def island_reference_height_above_deck(self) -> float:
        return 71.33544 - 27.80


def make_parameters() -> IslandParameters:
    return IslandParameters()
