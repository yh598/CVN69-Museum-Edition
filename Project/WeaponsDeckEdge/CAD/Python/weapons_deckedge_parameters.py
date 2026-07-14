"""Authoritative parameters for Milestone 4 defensive/deck-edge reconstruction.

All values are model millimetres at 1:700.  Approved hull, deck, integration,
and island datums are imported rather than duplicated.  Installation locations
are public-photo-derived display-model coordinates; no source-mesh triangles
are used by the production build.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


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
    "approved_integration_parameters_m4",
    PROJECT / "Integration" / "CAD" / "Python" / "integration_parameters.py",
)
_ISLAND_MODULE = _load_module(
    "approved_island_parameters_m4",
    PROJECT / "Island" / "CAD" / "Python" / "island_parameters.py",
)


@dataclass(frozen=True)
class Installation:
    name: str
    family: str
    x: float
    y: float
    platform: str
    heading_deg: float
    evidence: str
    confidence: str


@dataclass(frozen=True)
class Platform:
    name: str
    x0: float
    x1: float
    y0: float
    y1: float
    top_z_offset: float
    interface_names: Tuple[str, ...] = ()
    evidence: str = "official-photo-derived envelope"


INSTALLATIONS: Tuple[Installation, ...] = (
    Installation(
        "CIWS_01_Forward_Port", "CIWS", 93.0, -24.0,
        "Sponson_Forward_Port", 180.0,
        "2024-06-30 DVIDS port-bow imagery; Phalanx silhouette visible", "high family / medium placement",
    ),
    Installation(
        "RAM_01_Forward_Starboard", "RAM", 84.5, 25.0,
        "Sponson_Forward_Starboard", 0.0,
        "2024-06-30 DVIDS starboard-bow imagery; launcher silhouette", "medium-high",
    ),
    Installation(
        "SeaSparrow_01_Forward_Starboard", "SeaSparrow", 111.0, 27.0,
        "Sponson_Forward_Starboard", 0.0,
        "2024 official starboard-bow imagery and NAVSEA CVN Mk 29 evidence", "medium-high",
    ),
    Installation(
        "CIWS_02_Aft_Port", "CIWS", 431.0, -37.0,
        "Sponson_Aft_Port_CIWS", 180.0,
        "2024-07-14 official port-side imagery; Phalanx dome silhouette visible", "high family / medium placement",
    ),
    Installation(
        "RAM_02_Aft_Port", "RAM", 459.0, -37.0,
        "Sponson_Aft_Port_RAM", 180.0,
        "2024-07-14 official port-side imagery; aft launcher silhouette", "medium-high",
    ),
    Installation(
        "SeaSparrow_02_Aft_Starboard", "SeaSparrow", 424.0, 40.0,
        "Sponson_Aft_Starboard", 0.0,
        "2024 official aerial imagery and frozen-period system audit", "medium",
    ),
)


PLATFORMS: Tuple[Platform, ...] = (
    Platform("Sponson_Forward_Port", 82.0, 104.0, -30.0, -20.1, 0.0, ("CIWS_01_Forward_Port",)),
    Platform("Sponson_Forward_Starboard", 75.0, 122.0, 19.6, 32.5, 0.0, ("RAM_01_Forward_Starboard", "SeaSparrow_01_Forward_Starboard")),
    Platform("Sponson_Aft_Port_CIWS", 420.0, 442.0, -43.0, -34.2, 0.0, ("CIWS_02_Aft_Port",)),
    Platform("Sponson_Aft_Port_RAM", 449.0, 472.0, -43.0, -32.0, 0.0, ("RAM_02_Aft_Port",)),
    Platform("Sponson_Aft_Starboard", 414.0, 436.0, 36.0, 45.0, 0.0, ("SeaSparrow_02_Aft_Starboard",)),
    Platform("Boat_Access_Platform_Port", 292.0, 311.0, -43.0, -34.7, -5.5, (), "2024 port-side photo-derived major access platform"),
)


LIFERAFT_GROUPS = (
    ("LifeRaft_Group_01_Forward_Port", 132.0, -38.2, 6, 0.0),
    ("LifeRaft_Group_02_Mid_Port", 225.0, -43.0, 6, 0.0),
    ("LifeRaft_Group_03_Aft_Port", 376.0, -41.0, 6, 0.0),
    ("LifeRaft_Group_04_Forward_Starboard", 145.0, 42.0, 6, 180.0),
    ("LifeRaft_Group_05_Mid_Starboard", 255.0, 39.5, 6, 180.0),
    ("LifeRaft_Group_06_Aft_Starboard", 383.0, 41.0, 6, 180.0),
)


@dataclass(frozen=True)
class WeaponsDeckEdgeParameters:
    integration: object = field(default_factory=_INTEGRATION_MODULE.make_parameters)
    island: object = field(default_factory=_ISLAND_MODULE.make_parameters)
    version: str = "0.4.0-review"
    milestone: str = "Milestone 4 — Defensive Systems and Deck-Edge Equipment"
    configuration_period: str = "2023-10-14 through 2024-07-14 deployment; June 2024 visible fit preferred"

    # Glue-only interfaces and FDM limits.
    interface_clearance_per_side: float = 0.25
    key_depth: float = 1.20
    platform_thickness: float = 2.40
    glue_channel_width: float = 0.60
    glue_channel_depth: float = 0.35
    minimum_structural_wall: float = 1.20
    minimum_fragile_diameter: float = 0.80
    preferred_barrel_diameter: float = 1.00
    minimum_raised_width: float = 0.50
    minimum_raised_height: float = 0.35
    minimum_engraved_width: float = 0.50
    minimum_engraved_depth: float = 0.30
    minimum_railing: float = 0.60
    minimum_ladder: float = 0.60
    minimum_insert: float = 0.60
    preferred_print_envelope: float = 240.0
    tessellation_deflection: float = 0.055

    # Common keyed footprint is deliberately asymmetric and cannot be reversed.
    key_width: float = 4.00
    key_depth_xy: float = 5.00
    key_chamfer: float = 1.10
    foundation_pedestal_height: float = 2.00
    upper_key_depth: float = 0.80

    # FDM-safe display representations.
    ciws_body_height: float = 4.20
    ciws_dome_height: float = 2.20
    ciws_barrel_length: float = 4.60
    ram_launcher_height: float = 5.80
    seasparrow_launcher_height: float = 4.80
    liferaft_canister_diameter: float = 1.20
    liferaft_canister_length: float = 3.10
    coupon_width: float = 48.0
    coupon_depth: float = 24.0
    coupon_base_thickness: float = 3.0

    installations: Tuple[Installation, ...] = INSTALLATIONS
    platforms: Tuple[Platform, ...] = PLATFORMS
    liferaft_groups: tuple = LIFERAFT_GROUPS

    def __post_init__(self):
        if self.interface_clearance_per_side != self.integration.interface_clearance_per_side:
            raise ValueError("Milestone 4 clearance must match the approved integration convention")
        if self.minimum_structural_wall < 1.20:
            raise ValueError("Structural wall cannot be below 1.20 mm")
        if self.platform_thickness - self.key_depth < self.minimum_structural_wall:
            raise ValueError("Platform socket would violate remaining-skin thickness")
        names = {item.name for item in self.installations}
        if len(names) != len(self.installations):
            raise ValueError("Installation names must be unique")
        platform_names = {item.name for item in self.platforms}
        if any(item.platform not in platform_names for item in self.installations):
            raise ValueError("Every installation must reference a declared platform")

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
    def hull_seams(self) -> Tuple[float, ...]:
        return tuple(self.integration.hull_module_seams)

    @property
    def deck_seams(self) -> Tuple[float, ...]:
        return tuple(self.integration.deck_authoritative_seams)

    @property
    def island_bounds(self) -> Tuple[float, float, float, float]:
        return tuple(self.island.opening_bounds)

    def installation(self, name: str) -> Installation:
        return next(item for item in self.installations if item.name == name)

    def platform(self, name: str) -> Platform:
        return next(item for item in self.platforms if item.name == name)


def make_parameters() -> WeaponsDeckEdgeParameters:
    return WeaponsDeckEdgeParameters()
