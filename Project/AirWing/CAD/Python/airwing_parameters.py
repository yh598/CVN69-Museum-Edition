"""Authoritative Milestone 5 air-wing parameters.

All dimensions are millimetres at 1:700. Official full-scale dimensions are
converted here; sub-nozzle details are deliberately enlarged only to the
documented FDM minima. Approved ship geometry is imported, never duplicated.
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
    "approved_integration_parameters_m5",
    PROJECT / "Integration" / "CAD" / "Python" / "integration_parameters.py",
)
_ISLAND = _load(
    "approved_island_parameters_m5",
    PROJECT / "Island" / "CAD" / "Python" / "island_parameters.py",
)
_WEAPONS = _load(
    "approved_weapons_parameters_m5",
    PROJECT / "WeaponsDeckEdge" / "CAD" / "Python" / "weapons_deckedge_parameters.py",
)


@dataclass(frozen=True)
class AircraftType:
    code: str
    name: str
    squadron: str
    nickname: str
    full_length_m: float
    full_span_m: float
    model_length: float
    model_span: float
    folded_span: float
    variants: Tuple[str, ...]
    evidence_url: str
    dimension_url: str
    confidence: str = "high"
    rotor_diameter: float = 0.0
    dome_diameter: float = 0.0


TYPES: Tuple[AircraftType, ...] = (
    AircraftType("FA18E_VFA105", "F/A-18E Super Hornet", "VFA-105", "Gunslingers", 18.379, 13.686, 26.256, 19.551, 13.40, ("spread", "folded", "launch"), "https://www.dvidshub.net/news/476133/strike-fighter-squadron-vfa-105-returns-deployment", "https://www.navair.navy.mil/product/FA-18EF-Super-Hornet"),
    AircraftType("FA18F_VFA32", "F/A-18F Super Hornet", "VFA-32", "Fighting Swordsmen", 18.379, 13.686, 26.256, 19.551, 13.40, ("spread", "folded", "launch"), "https://www.dvidshub.net/image/8386769/fighting-swordsmen-strike-fighter-squadron-vfa-32-conduct-airborne-change-command-ceremony-red-sea", "https://www.navair.navy.mil/product/FA-18EF-Super-Hornet"),
    AircraftType("FA18E_VFA83", "F/A-18E Super Hornet", "VFA-83", "Rampagers", 18.379, 13.686, 26.256, 19.551, 13.40, ("spread", "folded", "launch"), "https://www.dvidshub.net/news/476132/strike-fighter-squadron-vfa-83-returns-deployment", "https://www.navair.navy.mil/product/FA-18EF-Super-Hornet"),
    AircraftType("FA18E_VFA131", "F/A-18E Super Hornet", "VFA-131", "Wildcats", 18.379, 13.686, 26.256, 19.551, 13.40, ("spread", "folded", "launch"), "https://www.dvidshub.net/image/8322956/uss-dwight-d-eisenhower-conducts-routine-flight-operations", "https://www.navair.navy.mil/product/FA-18EF-Super-Hornet"),
    AircraftType("EA18G_VAQ130", "EA-18G Growler", "VAQ-130", "Zappers", 18.349, 13.686, 26.213, 19.551, 13.40, ("spread", "folded", "launch"), "https://www.dvidshub.net/image/8317320/uss-dwight-d-eisenhower-conducts-flight-operations-red-sea", "https://www.navair.navy.mil/product/EA-18G-Growler"),
    AircraftType("E2C_VAW123", "E-2C Hawkeye", "VAW-123", "Screwtops", 17.526, 24.562, 25.037, 35.089, 13.20, ("spread", "folded", "launch"), "https://www.airlant.usff.navy.mil/Press-Room/News-Stories/Article/3955484/vaw-123-sends-their-last-e-2c-hawkeye-to-the-boneyard/", "https://www.navair.navy.mil/product/E-2C-Hawkeye", dome_diameter=10.450),
    AircraftType("C2A_VRC40", "C-2A Greyhound", "VRC-40", "Rawhides", 17.323, 24.562, 24.747, 35.089, 13.20, ("spread", "folded", "launch"), "https://www.dvidshub.net/image/8479217/uss-dwight-d-eisenhower-render-assistance-distressed-mariners", "https://www.navair.navy.mil/product/C-2"),
    AircraftType("MH60R_HSM74", "MH-60R Seahawk", "HSM-74", "Swamp Foxes", 19.761, 16.358, 28.230, 23.368, 6.20, ("deployed", "folded"), "https://www.dvidshub.net/image/8461915/uss-dwight-d-eisenhower-carrier-strike-group-conducts-photoex-with-its-cavour-carrier-strike-group-red-sea", "https://www.navy.mil/Resources/Fact-Files/Display-FactFiles/Article/2166679/mh-60r-seahawk/", rotor_diameter=23.368),
    AircraftType("MH60S_HSC7", "MH-60S Seahawk", "HSC-7", "Dusty Dogs", 19.761, 16.358, 28.230, 23.368, 6.20, ("deployed", "folded"), "https://www.dvidshub.net/image/8278107/uss-dwight-d-eisenhower-conducts-cast-and-recovery-exercise-red-sea", "https://www.navair.navy.mil/product/MH-60S-Seahawk", rotor_diameter=23.368),
)


@dataclass(frozen=True)
class AirWingParameters:
    integration: object = field(default_factory=_INTEGRATION.make_parameters)
    island: object = field(default_factory=_ISLAND.make_parameters)
    weapons: object = field(default_factory=_WEAPONS.make_parameters)
    version: str = "0.5.0-review"
    milestone: str = "Milestone 5 — Frozen-period Carrier Air Wing"
    configuration_period: str = "2023-10-14 through 2024-07-14"
    scale_denominator: int = 700
    nozzle: float = 0.40
    preferred_layer: float = 0.12
    validation_layers: Tuple[float, float] = (0.12, 0.16)
    wing_thickness: float = 0.70
    stabilizer_thickness: float = 0.70
    minimum_fuselage: float = 0.80
    minimum_gear: float = 0.80
    rotor_blade_thickness: float = 0.60
    rotor_blade_width: float = 0.70
    fin_thickness: float = 0.60
    antenna_thickness: float = 0.60
    marking_width: float = 0.50
    marking_height: float = 0.30
    insert_thickness: float = 0.60
    assembly_clearance_per_side: float = 0.20
    preferred_print_envelope: float = 240.0
    first_article_envelope: float = 120.0
    tessellation_deflection: float = 0.045
    interference_threshold_mm3: float = 0.10
    aircraft_types: Tuple[AircraftType, ...] = TYPES

    def __post_init__(self):
        if abs(self.integration.overall_length - 476.0) > 1.0e-9:
            raise ValueError("Approved 476 mm baseline changed")
        if self.integration.interface_clearance_per_side != 0.25:
            raise ValueError("Frozen production interface clearance changed")
        if self.wing_thickness < 0.60 or self.rotor_blade_thickness < 0.60:
            raise ValueError("FDM thickness minimum violated")

    @property
    def overall_length(self) -> float:
        return float(self.integration.overall_length)

    @property
    def deck_top_z(self) -> float:
        return float(self.integration.deck_top_z)

    @property
    def island_bounds(self):
        return tuple(self.island.opening_bounds)

    def aircraft(self, code: str) -> AircraftType:
        return next(item for item in self.aircraft_types if item.code == code)


def make_parameters() -> AirWingParameters:
    return AirWingParameters()
