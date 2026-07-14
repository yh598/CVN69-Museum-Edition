"""Master parameters for USS Dwight D. Eisenhower (CVN-69) Milestone 1.

All dimensions returned by :func:`make_parameters` are model millimetres.
The section table is intentionally dimensionless so a single definition can
generate the supported 1:1000, 1:700, and 1:350 editions.
"""

from dataclasses import dataclass
from math import ceil
from typing import Tuple


SUPPORTED_SCALES = (1000, 700, 350)


@dataclass(frozen=True)
class Station:
    x_ratio: float
    top_beam_factor: float
    waterline_beam_factor: float
    lower_beam_factor: float
    keel_rise_ratio: float = 0.0


# Print-oriented reconstruction of the Nimitz-class hull envelope.  The
# stations are ratios, not embedded millimetres.  They are deliberately dense
# at the bulbous bow and cruiser stern where curvature changes most quickly.
STATIONS: Tuple[Station, ...] = (
    Station(0.000, 0.014, 0.026, 0.205, 0.155),
    Station(0.010, 0.055, 0.050, 0.390, 0.090),
    Station(0.022, 0.165, 0.125, 0.520, 0.045),
    Station(0.040, 0.390, 0.315, 0.645, 0.018),
    Station(0.070, 0.665, 0.585, 0.755, 0.004),
    Station(0.110, 0.855, 0.800, 0.855, 0.000),
    Station(0.160, 0.955, 0.930, 0.930, 0.000),
    Station(0.230, 0.995, 0.985, 0.975, 0.000),
    Station(0.350, 1.000, 1.000, 1.000, 0.000),
    Station(0.500, 1.000, 1.000, 1.000, 0.000),
    Station(0.680, 1.000, 0.995, 0.985, 0.000),
    Station(0.800, 0.995, 0.975, 0.955, 0.000),
    Station(0.880, 0.965, 0.930, 0.900, 0.006),
    Station(0.930, 0.915, 0.850, 0.815, 0.014),
    Station(0.970, 0.835, 0.750, 0.700, 0.026),
    Station(1.000, 0.735, 0.655, 0.595, 0.040),
)


@dataclass(frozen=True)
class HullParameters:
    scale_denominator: int
    scale_factor: float
    overall_length: float
    maximum_hull_beam: float
    molded_depth: float
    waterline_height: float
    design_draft: float
    module_max_length: float
    module_count: int
    joint_clearance: float
    joint_length: float
    waterline_groove_depth: float
    waterline_groove_height: float
    anchor_recess_radius: float
    shaft_radius: float
    propeller_radius: float
    rudder_thickness: float
    tessellation_deflection: float
    stations: Tuple[Station, ...]


def make_parameters(scale_denominator: int = 700) -> HullParameters:
    """Return the complete model parameter set for a supported scale."""
    if scale_denominator not in SUPPORTED_SCALES:
        raise ValueError(
            f"Unsupported scale 1:{scale_denominator}; choose one of {SUPPORTED_SCALES}"
        )

    factor = 700.0 / float(scale_denominator)
    overall_length = 476.0 * factor
    # Hull beam is intentionally distinct from the much wider flight deck.
    maximum_hull_beam = 58.30 * factor
    molded_depth = 31.50 * factor
    waterline_height = 15.90 * factor
    design_draft = 16.10 * factor

    # 160 mm keeps every main module inside the A1 Mini's 180 mm axis while
    # leaving room for adhesion aids.  Larger printers can combine objects.
    module_max_length = 160.0
    module_count = max(2, int(ceil(overall_length / module_max_length)))

    # Functional FDM features are clamped so the smaller 1:1000 edition still
    # respects a 0.4 mm nozzle.
    return HullParameters(
        scale_denominator=scale_denominator,
        scale_factor=factor,
        overall_length=overall_length,
        maximum_hull_beam=maximum_hull_beam,
        molded_depth=molded_depth,
        waterline_height=waterline_height,
        design_draft=design_draft,
        module_max_length=module_max_length,
        module_count=module_count,
        joint_clearance=max(0.22, 0.25 * factor),
        joint_length=max(4.6, 6.0 * factor),
        waterline_groove_depth=max(0.30, 0.36 * factor),
        waterline_groove_height=max(0.45, 0.55 * factor),
        anchor_recess_radius=max(2.8, 4.0 * factor),
        shaft_radius=max(0.60, 0.78 * factor),
        propeller_radius=max(3.0, 4.15 * factor),
        rudder_thickness=max(0.90, 1.20 * factor),
        tessellation_deflection=max(0.055, 0.075 * factor),
        stations=STATIONS,
    )

