"""Parametric FDM correction for the four Milestone 2 propellers.

The approved hull propeller is retained as a dimensional reference.  This
module defines a clean replacement solid whose blade and hub faces share the
same print-bed datum.  Hull modules and the frozen hull/deck interface are not
modified.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class PropellerParameters:
    version: str = "1.0"
    blade_count: int = 5
    overall_diameter: float = 7.26
    blade_thickness: float = 0.60
    hub_length: float = 2.075
    shaft_bore_radius: float = 1.03
    hub_wall_thickness: float = 0.60
    hub_back_wall_thickness: float = 0.60
    scale_enlargement: float = 1.0
    removable_sprue_required: bool = False
    recommended_brim_width: float = 3.0

    # Swept five-blade silhouette, expressed as radius-normalized (y, z)
    # coordinates and inherited from the approved visual profile.
    blade_profile: Tuple[Tuple[float, float], ...] = (
        (0.22, -0.11),
        (0.92, 0.09),
        (0.68, 0.31),
        (0.165, 0.12),
    )

    # Exact maximum span factor of the five rotated blade polygons above.
    profile_span_factor: float = 1.7499439899830829

    @property
    def profile_radius(self) -> float:
        return self.overall_diameter / self.profile_span_factor

    @property
    def hub_radius(self) -> float:
        return self.shaft_bore_radius + self.hub_wall_thickness

    @property
    def shaft_bore_depth(self) -> float:
        return self.hub_length - self.hub_back_wall_thickness

    def validate(self) -> None:
        if self.blade_count != 5:
            raise ValueError("The approved visual configuration has five blades")
        if self.blade_thickness < 0.60:
            raise ValueError("FDM blade thickness must be at least 0.60 mm")
        if self.scale_enlargement != 1.0:
            raise ValueError("The production propeller must remain at 100% scale")
        if self.hub_wall_thickness < 0.60 or self.hub_back_wall_thickness < 0.60:
            raise ValueError("Hub walls must be at least 0.60 mm")
        if self.shaft_bore_depth <= 0.0:
            raise ValueError("The blind shaft bore must have positive depth")


def make_parameters() -> PropellerParameters:
    parameters = PropellerParameters()
    parameters.validate()
    return parameters
