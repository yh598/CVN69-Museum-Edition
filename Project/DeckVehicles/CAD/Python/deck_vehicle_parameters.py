"""Authoritative Milestone 6 vehicle/equipment parameters.

All production dimensions are millimetres at 1:700.  Controlled engineering
drawings were not used.  Full-scale public dimensions are converted where
available and every nozzle-driven enlargement is declared in ``enlargements``.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


THIS_FILE = Path(__file__).resolve()
PROJECT = THIS_FILE.parents[3]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_INTEGRATION = _load(
    "approved_integration_parameters_m6",
    PROJECT / "Integration" / "CAD" / "Python" / "integration_parameters.py",
)
_ISLAND = _load(
    "approved_island_parameters_m6",
    PROJECT / "Island" / "CAD" / "Python" / "island_parameters.py",
)
_WEAPONS = _load(
    "approved_weapons_parameters_m6",
    PROJECT / "WeaponsDeckEdge" / "CAD" / "Python" / "weapons_deckedge_parameters.py",
)


@dataclass(frozen=True)
class EquipmentFamily:
    code: str
    name: str
    category: str
    full_length_mm: float
    full_width_mm: float
    full_height_mm: float
    model_length: float
    model_width: float
    model_height: float
    material: str
    evidence_url: str
    dimension_url: str
    classification: str
    tolerance_mm: float
    confidence: str
    enlargements: Tuple[str, ...]


FAMILIES: Tuple[EquipmentFamily, ...] = (
    EquipmentFamily(
        "STT49", "A/S32A-49 Shipboard Tow Tractor", "tow_tractor",
        3528.06, 1859.28, 1020.06, 5.040, 3.400, 2.180, "gold",
        "https://www.navair.navy.mil/product/Shipboard-Tow-Tractor-STT",
        "https://sam.gov/opp/e2c470306bf64dc28a7a1df13b696f26/view",
        "manufacturer-dimension-derived; official-photo-informed silhouette; deliberately enlarged for FDM printability",
        0.06, "high",
        ("overall width 2.656 -> 3.400 mm to retain 0.70 mm wheel width", "overall height 1.457 -> 1.750 mm to retain wheel/body sections", "wheel diameter -> 1.10 mm minimum"),
    ),
    EquipmentFamily(
        "P25A", "A/S32P-25A Shipboard Firefighting Vehicle", "firefighting_vehicle",
        4826.00, 1778.00, 1625.60, 6.897, 3.250, 2.860, "gold",
        "https://www.navair.navy.mil/node/21206",
        "https://www.globalsecurity.org/military/library/policy/navy/ntsp/p25-a.htm",
        "official-dimension-derived; official-photo-informed silhouette; deliberately enlarged for FDM printability",
        0.08, "high",
        ("overall width 2.540 -> 3.250 mm for 0.70 mm wheels", "overall height 2.322 -> 2.650 mm for roof/turret continuity", "wheel diameter -> 1.10 mm minimum", "turret/nozzle diameter -> 0.80 mm"),
    ),
    EquipmentFamily(
        "MSU200", "MSU-200NAV Air Start Service Cart", "service_cart",
        1735.07, 929.89, 694.69, 3.600, 2.550, 1.900, "ash_gray",
        "https://www.navair.navy.mil/systems",
        "https://www.globalsecurity.org/military/library/policy/navy/ntsp/msu_200-p_2002.pdf",
        "official-dimension-derived module on photo-informed towable frame; deliberately enlarged for FDM printability",
        0.08, "medium-high",
        ("module/trailer length 2.479 -> 3.600 mm", "overall width 1.328 -> 2.550 mm", "overall height 0.992 -> 1.900 mm", "wheel diameter -> 1.00 mm", "hose representation -> 0.60 mm"),
    ),
    EquipmentFamily(
        "TOWBAR", "Carrier Aircraft Tow Bar", "tow_bar",
        3500.00, 450.00, 300.00, 4.725, 2.200, 0.800, "gold",
        "https://www.dvidshub.net/image/8063718/aircraft-handling",
        "https://www.dvidshub.net/image/8063718/aircraft-handling",
        "official-photo-derived; visually approximated; deliberately enlarged for FDM printability",
        0.35, "medium",
        ("bar thickness and width -> 0.80 mm", "fork spacing -> 2.20 mm for visible silhouette"),
    ),
    EquipmentFamily(
        "LADDER", "Portable Aircraft Maintenance Ladder", "maintenance_ladder",
        1800.00, 900.00, 2200.00, 3.600, 0.600, 3.850, "gold",
        "https://www.dvidshub.net/image/8278538/uss-dwight-d-eisenhower-conducts-routine-maintenance-in-the-red-sea",
        "https://www.dvidshub.net/image/8278538/uss-dwight-d-eisenhower-conducts-routine-maintenance-in-the-red-sea",
        "deployment-era official-photo-derived; visually approximated; deliberately enlarged for FDM printability",
        0.45, "medium",
        ("rail and rung thickness -> 0.60 mm", "flat-backed overall envelope enlarged to preserve four open steps and support-free printing"),
    ),
    EquipmentFamily(
        "CHOCK", "Aircraft Wheel Chock Group", "wheel_chock",
        850.00, 500.00, 300.00, 3.100, 1.100, 0.700, "gold",
        "https://www.dvidshub.net/news/153407/1-228th-aviation-regiment-joins-navy-for-qualification",
        "https://www.dvidshub.net/image/6811000/night-flying-operations",
        "official-photo-derived generic aviation safety form; visually approximated; deliberately enlarged for FDM printability",
        0.30, "medium",
        ("two chocks enlarged to 1.20 mm each", "connecting rope represented as a 0.80 mm bed-connected bar"),
    ),
    EquipmentFamily(
        "EXT", "Twin Portable Flight-Deck Extinguisher Cart", "extinguisher_group",
        1100.00, 650.00, 1200.00, 2.600, 2.300, 2.200, "red",
        "https://www.navair.navy.mil/node/21206",
        "https://www.navair.navy.mil/node/21206",
        "official-equipment-description-derived; visually approximated; deliberately enlarged for FDM printability",
        0.30, "medium",
        ("bottle diameters -> 0.90 mm", "cart rails/handle -> 0.70 mm", "wheels -> 1.00 x 0.70 mm"),
    ),
)


@dataclass(frozen=True)
class DeckVehicleParameters:
    integration: object = field(default_factory=_INTEGRATION.make_parameters)
    island: object = field(default_factory=_ISLAND.make_parameters)
    weapons: object = field(default_factory=_WEAPONS.make_parameters)
    version: str = "0.6.0-review"
    milestone: str = "Milestone 6 — Flight-Deck Vehicles and Aviation Support Equipment"
    configuration_period: str = "2023-10-14 through 2024-07-14"
    scale_denominator: int = 700
    nozzle: float = 0.40
    preferred_layer: float = 0.12
    validation_layers: Tuple[float, float] = (0.12, 0.16)
    minimum_structural_wall: float = 0.80
    preferred_body_section: float = 1.00
    minimum_wheel_diameter: float = 1.00
    minimum_wheel_width: float = 0.70
    minimum_axle: float = 0.80
    minimum_tow_bar: float = 0.80
    minimum_handle: float = 0.70
    minimum_ladder: float = 0.60
    minimum_hose: float = 0.60
    minimum_raised_width: float = 0.50
    minimum_raised_height: float = 0.30
    minimum_insert: float = 0.60
    small_part_clearance_per_side: float = 0.20
    preferred_print_envelope: float = 240.0
    first_article_envelope: float = 120.0
    interference_threshold_mm3: float = 0.10
    tessellation_deflection: float = 0.04
    families: Tuple[EquipmentFamily, ...] = FAMILIES

    def __post_init__(self):
        if abs(float(self.integration.overall_length) - 476.0) > 1.0e-9:
            raise ValueError("Approved 476 mm baseline changed")
        if float(self.integration.interface_clearance_per_side) != 0.25:
            raise ValueError("Frozen production interface clearance changed")
        if self.minimum_structural_wall < 0.80 or self.minimum_ladder < 0.60:
            raise ValueError("FDM minimum violated")

    @property
    def overall_length(self) -> float:
        return float(self.integration.overall_length)

    @property
    def deck_top_z(self) -> float:
        return float(self.integration.deck_top_z)

    @property
    def island_bounds(self):
        return tuple(self.island.opening_bounds)

    def family(self, code: str) -> EquipmentFamily:
        return next(item for item in self.families if item.code == code)


def make_parameters() -> DeckVehicleParameters:
    return DeckVehicleParameters()
