"""Authoritative parameters for Milestone 2 hull/deck integration.

Hull and flight-deck dimensions are imported from their approved parameter
modules.  This module defines only the coordinate transform and new concealed
interface geometry; it does not duplicate either approved shape definition.
"""

from __future__ import annotations

import importlib.util
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
    spec.loader.exec_module(module)
    return module


_HULL_MODULE = _load_module(
    "approved_hull_parameters",
    PROJECT / "CAD" / "Python" / "hull_parameters.py",
)
_DECK_MODULE = _load_module(
    "approved_deck_parameters",
    PROJECT / "FlightDeck" / "CAD" / "Python" / "deck_parameters.py",
)


@dataclass(frozen=True)
class IntegrationParameters:
    hull: object = field(default_factory=lambda: _HULL_MODULE.make_parameters(700))
    deck: object = field(default_factory=_DECK_MODULE.make_parameters)
    version: str = "0.2.0-review"
    milestone: str = "Milestone 2 — Hull–Flight-Deck Integration"

    # New integration-only geometry.  Landing pads are separate printed parts
    # captured by shallow, open sockets in the approved hull top and deck
    # underside.  The deck still seats directly on the hull-top datum.
    interface_clearance_per_side: float = 0.25
    pad_length: float = 6.00
    pad_width: float = 6.00
    pad_total_height: float = 2.40
    pad_hull_insertion: float = 1.20
    pad_deck_insertion: float = 1.20
    hull_socket_depth: float = 1.20
    deck_socket_depth: float = 1.45
    socket_opening_allowance: float = 0.05
    pad_y_centers: Tuple[float, float] = (-8.0, 8.0)
    pad_x_stations: Tuple[float, ...] = (32.0, 105.0, 205.0, 270.0, 370.0, 445.0)
    seating_gap: float = 0.0
    minimum_structural_thickness: float = 1.20

    # Tessellation follows the tighter of the two approved packages.
    tessellation_deflection: float = 0.075
    preferred_print_envelope: float = 240.0

    def __post_init__(self):
        if abs(self.hull.overall_length - self.deck.overall_length) > 1.0e-9:
            raise ValueError("Approved hull and deck overall lengths differ")
        if self.pad_total_height != self.pad_hull_insertion + self.pad_deck_insertion:
            raise ValueError("Landing-pad height must equal the two insertion depths")
        if self.deck.deck_thickness - self.deck_socket_depth < self.minimum_structural_thickness:
            raise ValueError("Deck socket would violate the minimum top-skin thickness")

    @property
    def overall_length(self) -> float:
        return float(self.hull.overall_length)

    @property
    def deck_base_z(self) -> float:
        return float(self.hull.molded_depth + self.seating_gap)

    @property
    def deck_top_z(self) -> float:
        return self.deck_base_z + float(self.deck.deck_thickness)

    @property
    def socket_length(self) -> float:
        return self.pad_length + 2.0 * self.interface_clearance_per_side

    @property
    def socket_width(self) -> float:
        return self.pad_width + 2.0 * self.interface_clearance_per_side

    @property
    def hull_module_seams(self) -> Tuple[float, ...]:
        return tuple(
            self.overall_length * index / int(self.hull.module_count)
            for index in range(1, int(self.hull.module_count))
        )

    @property
    def deck_source_seams(self) -> Tuple[float, ...]:
        return tuple(float(value) for value in self.deck.split_seams)

    @property
    def deck_authoritative_seams(self) -> Tuple[float, ...]:
        return tuple(sorted(self.deck_x_to_authoritative(value) for value in self.deck_source_seams))

    @property
    def deck_top_skin_over_socket(self) -> float:
        return float(self.deck.deck_thickness) - self.deck_socket_depth

    @property
    def vertical_pad_tip_clearance(self) -> float:
        return self.deck_socket_depth - self.pad_deck_insertion

    def deck_x_to_authoritative(self, source_x: float) -> float:
        """Map approved deck x (stern→bow) into x=0 bow, x=L stern."""
        return self.overall_length - float(source_x)

    def deck_point_to_authoritative(self, source_x: float, source_y: float, source_z: float):
        return (
            self.deck_x_to_authoritative(source_x),
            float(source_y),
            self.deck_base_z + float(source_z),
        )


def make_parameters() -> IntegrationParameters:
    return IntegrationParameters()
