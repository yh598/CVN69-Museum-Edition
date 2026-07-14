#!/usr/bin/env python3
"""Build the Milestone 3 CVN-69 island as new parametric FreeCAD BReps.

The approved Milestone 2 hull/deck model is read only for datums, review
assembly export, and interference context.  No source STL is opened here.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
import zipfile
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import FreeCAD as App
import Part


SCRIPT = Path(__file__).resolve()
ISLAND = SCRIPT.parents[1]
PROJECT = ISLAND.parent
REPO = PROJECT.parent
sys.path.insert(0, str(ISLAND / "CAD" / "Python"))
from island_parameters import make_parameters  # noqa: E402


P = make_parameters()
DIRS = {
    "freecad": ISLAND / "CAD" / "FreeCAD",
    "step": ISLAND / "STEP",
    "stl": ISLAND / "STL",
    "3mf": ISLAND / "3MF",
    "obj": ISLAND / "OBJ",
    "render": ISLAND / "Render",
    "images": ISLAND / "Images",
    "docs": ISLAND / "Docs",
    "assembly": ISLAND / "Assembly",
    "references": ISLAND / "References",
    "qa": ISLAND / "QA",
}
for directory in DIRS.values():
    directory.mkdir(parents=True, exist_ok=True)


MATERIALS = OrderedDict(
    (
        ("ash_gray", ("Bambu PLA Matte Ash Gray", "#969890FF")),
        ("charcoal", ("Bambu PLA Matte Charcoal", "#34383CFF")),
        ("silk_silver", ("Bambu PLA Silk Silver", "#AEB4B8FF")),
        ("ivory_white", ("Bambu PLA Matte Ivory White", "#ECE8D9FF")),
        ("basic_black", ("Bambu PLA Basic Black", "#151719FF")),
    )
)


APPROVED_PATHS = (
    PROJECT / "CAD" / "FreeCAD" / "Hull.FCStd",
    PROJECT / "CAD" / "Python" / "hull_parameters.py",
    PROJECT / "FlightDeck" / "CAD" / "FreeCAD" / "CVN69_Flight_Deck_Reconstruction.FCStd",
    PROJECT / "FlightDeck" / "CAD" / "Python" / "deck_parameters.py",
    PROJECT / "Integration" / "CAD" / "FreeCAD" / "CVN69_Hull_Deck_Integration.FCStd",
    PROJECT / "Integration" / "CAD" / "Python" / "integration_parameters.py",
    PROJECT / "Integration" / "STEP" / "CVN69_Hull_Deck_Assembly.step",
)
INTEGRATION_FCSTD = PROJECT / "Integration" / "CAD" / "FreeCAD" / "CVN69_Hull_Deck_Integration.FCStd"


@dataclass
class PartSpec:
    name: str
    shape: object
    material: str
    role: str
    evidence: str
    print_rotation: Optional[object] = None
    print_override: Optional[object] = None
    print_note: str = "Base down; exported STL minimum z = 0"


def v(x: float, y: float, z: float) -> App.Vector:
    return App.Vector(float(x), float(y), float(z))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def precise_bounds(shape):
    points, _faces = shape.tessellate(P.tessellation_deflection)
    if not points:
        raise RuntimeError("Cannot measure empty shape")
    xs, ys, zs = ([getattr(point, axis) for point in points] for axis in ("x", "y", "z"))
    return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)


def validate_shape(name: str, shape, allow_multiple=False):
    solids = list(shape.Solids)
    valid = not shape.isNull() and shape.isValid() and bool(solids) and all(solid.isClosed() for solid in solids)
    if not valid or (not allow_multiple and len(solids) != 1):
        raise RuntimeError(
            f"{name} is not the expected closed BRep: valid={shape.isValid()} "
            f"closed={[solid.isClosed() for solid in solids]} solids={len(solids)}"
        )
    return shape


def polygon_wire(points, z_value):
    vectors = [v(x, y, z_value) for x, y in points]
    return Part.makePolygon(vectors + [vectors[0]])


def polygon_prism(points, z0, height):
    return Part.Face(polygon_wire(points, z0)).extrude(v(0, 0, height))


def loft_solid(lower_points, lower_z, upper_points, upper_z):
    return Part.makeLoft(
        [polygon_wire(lower_points, lower_z), polygon_wire(upper_points, upper_z)],
        True,
        False,
    )


def fuse_all(shapes):
    usable = [shape for shape in shapes if shape is not None and not shape.isNull() and shape.Volume > 1.0e-8]
    if not usable:
        raise RuntimeError("No shapes supplied to fuse")
    result = usable[0]
    for shape in usable[1:]:
        result = result.fuse(shape)
    return result.removeSplitter()


def compound(shapes):
    usable = [shape for shape in shapes if shape is not None and not shape.isNull() and shape.Volume > 1.0e-8]
    return Part.makeCompound(usable)


def bar_between(start, end, diameter):
    start_vector = v(*start)
    direction = v(end[0] - start[0], end[1] - start[1], end[2] - start[2])
    length = direction.Length
    if length <= 1.0e-8:
        raise ValueError("Bar endpoints coincide")
    return Part.makeCylinder(diameter / 2.0, length, start_vector, direction)


def transform_shape(shape, rotation=None, target_min=(0.0, 0.0, 0.0)):
    result = shape.copy()
    if rotation is not None:
        result.Placement = App.Placement(v(0, 0, 0), rotation)
    bounds = precise_bounds(result)
    result.translate(v(target_min[0] - bounds[0], target_min[1] - bounds[1], target_min[2] - bounds[2]))
    return result


def make_foundation_lower_body():
    x0, y0, x1, y1 = P.opening_bounds
    plug_z = P.deck_top_z - P.interface_plug_depth
    plug = polygon_prism(
        P.interface_plug_points,
        plug_z,
        P.interface_plug_depth + P.foundation_flange_height,
    )
    flange = polygon_prism(P.foundation_flange_points, P.deck_top_z, P.foundation_flange_height)
    lower_z = P.deck_top_z + P.foundation_flange_height
    upper_z = P.deck_top_z + P.lower_body_height
    upper_points = (
        (x0 + 1.10, y0 + 0.85),
        (x0 + 1.10, y1 - 1.20),
        (x0 + 8.30, y1 - 1.20),
        (x0 + 9.50, y1 - 2.40),
        (x1 - 2.00, y1 - 2.40),
        (x1 - 1.10, y1 - 3.40),
        (x1 - 1.10, y0 + 0.85),
    )
    body = loft_solid(P.foundation_flange_points, lower_z, upper_points, upper_z)
    result = fuse_all((plug, flange, body))

    flange_bounds = precise_bounds(flange)
    cx, cy = P.opening_center
    channel_z = P.deck_top_z
    channel_h = P.glue_channel_depth
    tools = (
        Part.makeBox(x0 - flange_bounds[0] + 0.65, P.glue_channel_width, channel_h, v(flange_bounds[0] - 0.05, cy - P.glue_channel_width / 2.0, channel_z)),
        Part.makeBox(flange_bounds[3] - x1 + 0.65, P.glue_channel_width, channel_h, v(x1 - 0.60, cy - P.glue_channel_width / 2.0, channel_z)),
        Part.makeBox(P.glue_channel_width, y0 - flange_bounds[1] + 0.65, channel_h, v(cx - P.glue_channel_width / 2.0, flange_bounds[1] - 0.05, channel_z)),
        Part.makeBox(P.glue_channel_width, flange_bounds[4] - y1 + 0.65, channel_h, v(cx - P.glue_channel_width / 2.0, y1 - 0.60, channel_z)),
    )
    for tool in tools:
        result = result.cut(tool)
    return validate_shape("Foundation_Lower_Island", result.removeSplitter())


def window_recess(core, tools):
    inserts = []
    result = core
    for tool in tools:
        insert = core.common(tool)
        if not insert.isNull() and insert.Volume > 1.0e-7:
            inserts.append(insert)
        result = result.cut(tool)
    insert_shape = fuse_all(inserts) if len(inserts) > 1 else inserts[0]
    return result.removeSplitter(), insert_shape.removeSplitter()


def make_bridge():
    x0, y0, _x1, y1 = P.opening_bounds
    base_z = P.deck_top_z + P.lower_body_height
    top_z = P.deck_top_z + P.bridge_top_height
    lower = (
        (x0 + 0.60, y0 + 0.55),
        (x0 + 13.00, y0 + 0.55),
        (x0 + 13.00, y1 + 1.55),
        (x0 + 0.60, y1 + 1.55),
    )
    upper = (
        (x0 + 1.00, y0 + 0.90),
        (x0 + 12.50, y0 + 0.90),
        (x0 + 12.50, y1 + 1.20),
        (x0 + 1.00, y1 + 1.20),
    )
    core = loft_solid(lower, base_z, upper, top_z)
    band_z = P.deck_top_z + 13.0
    band_h = 1.85
    tools = (
        Part.makeBox(1.20, y1 - y0 + 3.5, band_h, v(x0 + 0.30, y0 - 0.20, band_z)),
        Part.makeBox(13.0, 1.10, band_h, v(x0 + 0.50, y0 + 0.20, band_z)),
        Part.makeBox(13.0, 1.10, band_h, v(x0 + 0.50, y1 + 0.65, band_z)),
    )
    body, windows = window_recess(core, tools)

    wing_z = P.deck_top_z + 11.25
    wing = Part.makeBox(14.5, y1 - y0 + 3.3, 0.80, v(x0 + 0.10, y0 - 0.10, wing_z))
    rail_y = y1 + 2.60
    rail = [Part.makeBox(14.5, P.minimum_railing, P.minimum_railing, v(x0 + 0.10, rail_y, wing_z + 2.20))]
    for x_value in (x0 + 0.10, x0 + 4.70, x0 + 9.30, x0 + 14.0):
        rail.append(Part.makeBox(P.minimum_railing, P.minimum_railing, 2.20, v(x_value, rail_y, wing_z + 0.75)))
    body = fuse_all((body, wing, *rail))
    return validate_shape("Navigation_Bridge", body), validate_shape("Bridge_Window_Insert", windows, True)


def make_prifly():
    _x0, y0, x1, y1 = P.opening_bounds
    platform_z = P.deck_top_z + P.lower_body_height
    platform = Part.makeBox(12.5, y1 - y0 - 1.0, 0.80, v(x1 - 4.0, y0 + 1.0, platform_z))
    lower_z = platform_z + 0.80
    top_z = P.deck_top_z + P.prifly_top_height
    lower = ((x1 - 2.0, y0 + 1.5), (x1 + 7.2, y0 + 1.5), (x1 + 7.2, y1 - 0.2), (x1 - 2.0, y1 - 0.2))
    upper = ((x1 - 1.6, y0 + 1.8), (x1 + 6.7, y0 + 1.8), (x1 + 6.7, y1 - 0.5), (x1 - 1.6, y1 - 0.5))
    core = loft_solid(lower, lower_z, upper, top_z)
    band_z = P.deck_top_z + 12.2
    tools = (
        Part.makeBox(1.0, y1 - y0, 1.55, v(x1 + 6.3, y0 + 1.2, band_z)),
        Part.makeBox(9.4, 0.9, 1.55, v(x1 - 2.0, y0 + 1.15, band_z)),
        Part.makeBox(9.4, 0.9, 1.55, v(x1 - 2.0, y1 - 0.85, band_z)),
    )
    body, windows = window_recess(core, tools)
    rail_x = x1 + 6.8
    rails = [Part.makeBox(P.minimum_railing, y1 - y0 - 1.0, P.minimum_railing, v(rail_x, y0 + 1.0, platform_z + 2.0))]
    for y_value in (y0 + 1.0, y0 + 4.7, y0 + 8.4, y1 - 0.6):
        rails.append(Part.makeBox(P.minimum_railing, P.minimum_railing, 2.0, v(rail_x, y_value, platform_z + 0.75)))
    body = fuse_all((body, platform, *rails))
    return validate_shape("Primary_Flight_Control", body), validate_shape("PriFly_Window_Insert", windows, True)


def make_exhaust_uptake():
    x0, y0, _x1, _y1 = P.opening_bounds
    base_z = P.deck_top_z + P.lower_body_height
    top_z = P.deck_top_z + P.uptake_top_height
    lower = ((x0 + 13.0, y0 + 2.8), (x0 + 20.5, y0 + 2.8), (x0 + 20.5, y0 + 12.7), (x0 + 13.0, y0 + 12.7))
    upper = ((x0 + 14.0, y0 + 3.5), (x0 + 19.2, y0 + 3.5), (x0 + 19.2, y0 + 11.8), (x0 + 14.0, y0 + 11.8))
    uptake = loft_solid(lower, base_z, upper, top_z)
    pedestal = Part.makeBox(4.3, 5.3, 7.0, v(x0 + 19.0, y0 + 4.7, base_z))
    caps = (
        Part.makeCylinder(1.15, 1.40, v(x0 + 15.7, y0 + 6.0, top_z)),
        Part.makeCylinder(1.15, 1.40, v(x0 + 18.0, y0 + 9.4, top_z)),
    )
    return validate_shape("Exhaust_Uptake", fuse_all((uptake, pedestal, *caps)))


def make_main_mast():
    x0, y0, _x1, _y1 = P.opening_bounds
    cx, cy = x0 + 21.2, y0 + 7.4
    base_z = P.deck_top_z + 16.5
    platform_z = P.deck_top_z + P.mast_platform_height
    lower = ((cx - 1.6, cy - 1.6), (cx + 1.6, cy - 1.6), (cx + 1.6, cy + 1.6), (cx - 1.6, cy + 1.6))
    upper = ((cx - 0.70, cy - 0.70), (cx + 0.70, cy - 0.70), (cx + 0.70, cy + 0.70), (cx - 0.70, cy + 0.70))
    mast = loft_solid(lower, base_z, upper, platform_z)
    upper_shaft = Part.makeCylinder(P.preferred_fragile_mast / 2.0, P.mast_top_height - P.mast_platform_height, v(cx, cy, platform_z))
    platforms = (
        Part.makeBox(7.0, 7.0, 0.70, v(cx - 3.5, cy - 3.5, P.deck_top_z + 23.8)),
        Part.makeBox(9.0, 8.0, 0.70, v(cx - 4.5, cy - 4.0, platform_z - 0.35)),
    )
    rail_z = P.deck_top_z + 26.1
    rail = [Part.makeBox(7.0, P.minimum_railing, P.minimum_railing, v(cx - 3.5, cy + 3.0, rail_z))]
    for x_value in (cx - 3.5, cx - 0.5, cx + 2.9):
        rail.append(Part.makeBox(P.minimum_railing, P.minimum_railing, 2.0, v(x_value, cy + 3.0, rail_z - 1.9)))
    return validate_shape("Main_Mast", fuse_all((mast, upper_shaft, *platforms, *rail)))


def make_secondary_mast():
    _x0, y0, x1, _y1 = P.opening_bounds
    cx, cy = x1 + 3.2, y0 + 7.0
    base_z = P.deck_top_z + P.prifly_top_height
    top_z = P.deck_top_z + P.secondary_mast_top_height
    # A prismatic shaft is deliberately used here.  The earlier tapered loft
    # was valid in the native document but produced invalid curve-on-surface
    # diagnostics after STEP round-trip at the crossarm intersection.
    mast = Part.makeBox(1.20, 1.20, top_z - base_z, v(cx - 0.60, cy - 0.60, base_z))
    yard = Part.makeBox(1.20, 7.0, 0.80, v(cx - 0.60, cy - 3.5, top_z - 0.80))
    return validate_shape("Secondary_Mast", fuse_all((mast, yard)))


def make_yardarm():
    x0, y0, _x1, _y1 = P.opening_bounds
    cx, cy = x0 + 21.2, y0 + 7.4
    z_value = P.deck_top_z + P.mast_yardarm_height
    transverse = Part.makeBox(0.80, 14.0, 0.80, v(cx - 0.40, cy - 7.0, z_value - 0.40))
    longitudinal = Part.makeBox(8.0, 0.80, 0.80, v(cx - 4.0, cy - 0.40, z_value - 0.40))
    center_support = Part.makeBox(0.80, 0.80, 2.60, v(cx - 0.40, cy - 0.40, z_value - 2.20))

    def transverse_gusset(y_end):
        vectors = [
            v(cx - 0.40, cy, z_value - 2.20),
            v(cx - 0.40, y_end, z_value - 0.25),
            v(cx - 0.40, cy, z_value - 0.25),
            v(cx - 0.40, cy, z_value - 2.20),
        ]
        return Part.Face(Part.makePolygon(vectors)).extrude(v(0.80, 0, 0))

    parts = (transverse, longitudinal, center_support, transverse_gusset(cy - 6.4), transverse_gusset(cy + 6.4))
    return validate_shape("Main_Yardarm", fuse_all(parts))


def make_radar_panel(width, height, thickness):
    panel = Part.makeBox(width, thickness, height, v(0, 0, 0))
    ribs = []
    for fraction in (0.22, 0.50, 0.78):
        ribs.append(Part.makeBox(width, P.radar_rib_height, P.radar_rib_width, v(0, thickness, fraction * height - P.radar_rib_width / 2.0)))
    ribs.extend(
        (
            Part.makeBox(P.radar_rib_width, P.radar_rib_height, height, v(0, thickness, 0)),
            Part.makeBox(P.radar_rib_width, P.radar_rib_height, height, v(width - P.radar_rib_width, thickness, 0)),
        )
    )
    return fuse_all((panel, *ribs))


def placed(shape, x, y, z, angle_y=0.0):
    result = shape.copy()
    if abs(angle_y) > 1.0e-9:
        result.rotate(v(0, 0, 0), v(0, 1, 0), angle_y)
    bounds = precise_bounds(result)
    result.translate(v(x - bounds[0], y - bounds[1], z - bounds[2]))
    return result


def make_radars():
    x0, y0, _x1, y1 = P.opening_bounds
    sps48 = placed(make_radar_panel(6.0, 7.0, P.radar_panel_thickness), x0 + 13.8, y1 - 1.0, P.deck_top_z + 14.0, -8.0)
    sps49 = placed(make_radar_panel(7.0, 4.2, P.radar_panel_thickness), x0 + 17.7, y0 + 8.0, P.deck_top_z + 30.0, 0.0)
    spn50_panel = make_radar_panel(3.4, 5.0, P.radar_panel_thickness)
    spn50 = placed(spn50_panel, x0 + 19.4, y0 + 9.0, P.deck_top_z + 22.0, 0.0)
    support = bar_between((x0 + 21.1, y0 + 8.9, P.deck_top_z + 20.0), (x0 + 21.1, y0 + 8.9, P.deck_top_z + 22.0), 0.80)
    spn50 = fuse_all((spn50, support))
    return (
        validate_shape("Radar_AN_SPS48G_Array", sps48),
        validate_shape("Radar_AN_SPS49_Array", sps49),
        validate_shape("Radar_AN_SPN50_Array", spn50),
    )


def make_ladder():
    _x0, y0, x1, _y1 = P.opening_bounds
    x_value = x1 + 7.2
    z0 = P.deck_top_z + 10.3
    rails = (
        Part.makeBox(0.60, 0.60, 5.0, v(x_value, y0 + 3.0, z0)),
        Part.makeBox(0.60, 0.60, 5.0, v(x_value, y0 + 6.2, z0)),
    )
    rungs = [Part.makeBox(0.60, 3.8, 0.60, v(x_value, y0 + 3.0, z0 + index * 1.1)) for index in range(5)]
    return validate_shape("Aft_Access_Ladder", fuse_all((*rails, *rungs)))


def make_antennas():
    x0, y0, x1, _y1 = P.opening_bounds
    locations = (
        (x0 + 17.0, y0 + 2.0, P.deck_top_z + P.mast_platform_height, 3.6),
        (x0 + 25.0, y0 + 12.0, P.deck_top_z + P.mast_platform_height, 3.1),
        (x1 + 3.2, y0 + 3.0, P.deck_top_z + P.secondary_mast_top_height, 3.0),
        (x1 + 3.2, y0 + 10.5, P.deck_top_z + P.secondary_mast_top_height, 3.0),
    )
    assembled = []
    printed = []
    for index, (x_value, y_value, z_value, height) in enumerate(locations):
        antenna = fuse_all(
            (
                Part.makeCylinder(0.70, 0.40, v(x_value, y_value, z_value)),
                Part.makeCylinder(P.minimum_freestanding_mast / 2.0, height, v(x_value, y_value, z_value + 0.35)),
            )
        )
        assembled.append(antenna)
        local = fuse_all(
            (
                Part.makeCylinder(0.70, 0.40, v(index * 3.2, 0, 0)),
                Part.makeCylinder(P.minimum_freestanding_mast / 2.0, height, v(index * 3.2, 0, 0.35)),
            )
        )
        printed.append(local)
    return validate_shape("Antenna_Detail_Set", compound(assembled), True), validate_shape("Antenna_Detail_Set_Print", compound(printed), True)


def make_signal_lights():
    x0, y0, _x1, _y1 = P.opening_bounds
    cx = x0 + 21.2
    z0 = P.deck_top_z + P.mast_yardarm_height + 0.25
    shapes = []
    for y_value in (y0 + 2.0, y0 + 5.6, y0 + 9.2, y0 + 12.8):
        shapes.append(fuse_all((Part.makeCylinder(0.55, 1.15, v(cx, y_value, z0)), Part.makeCylinder(0.72, 0.35, v(cx, y_value, z0)))))
    return validate_shape("Signal_Light_Housings", compound(shapes), True)


def digit_segments(number, x0, y0, width=2.4, height=3.6, stroke=0.60, depth=0.35):
    horizontal = lambda y: Part.makeBox(width, stroke, depth, v(x0, y, 0))
    vertical = lambda x, y: Part.makeBox(stroke, height / 2.0 + stroke / 2.0, depth, v(x, y, 0))
    middle_y = y0 + (height - stroke) / 2.0
    top_y = y0 + height - stroke
    segments = {
        "top": horizontal(top_y),
        "middle": horizontal(middle_y),
        "bottom": horizontal(y0),
        "ul": vertical(x0, middle_y),
        "ur": vertical(x0 + width - stroke, middle_y),
        "ll": vertical(x0, y0),
        "lr": vertical(x0 + width - stroke, y0),
    }
    names = ("top", "middle", "bottom", "ul", "ll", "lr") if number == 6 else ("top", "middle", "bottom", "ul", "ur", "lr")
    return fuse_all([segments[name] for name in names])


def make_marking(port=True):
    local = compound((digit_segments(6, 0, 0), digit_segments(9, 3.0, 0)))
    rotation = App.Rotation(v(1, 0, 0), 90 if port else -90)
    oriented = transform_shape(local, rotation)
    x0, y0, _x1, y1 = P.opening_bounds
    target_y = y0 - P.marking_thickness if port else y1 + 0.05
    target_z = P.deck_top_z + 3.4
    oriented = transform_shape(oriented, None, (x0 + 20.0, target_y, target_z))
    return validate_shape(f"Marking_69_{'Port' if port else 'Starboard'}", oriented, True)


def make_coupon():
    opening = P.opening_authoritative
    plug = P.interface_plug_points
    x0, y0, x1, y1 = P.opening_bounds
    dx = (P.coupon_width - (x1 - x0)) / 2.0 - x0
    dy = (P.coupon_depth - (y1 - y0)) / 2.0 - y0
    local_opening = tuple((x + dx, y + dy) for x, y in opening)
    local_plug = tuple((x + dx, y + dy) for x, y in plug)
    male_base = Part.makeBox(P.coupon_width, P.coupon_depth, P.coupon_base_thickness, v(0, 0, 0))
    male_plug = polygon_prism(local_plug, P.coupon_base_thickness, P.interface_plug_depth)
    male = fuse_all((male_base, male_plug))
    cx, cy = P.coupon_width / 2.0, P.coupon_depth / 2.0
    channels = (
        Part.makeBox(6.0, P.glue_channel_width, P.glue_channel_depth, v(0, cy - P.glue_channel_width / 2.0, P.coupon_base_thickness - P.glue_channel_depth)),
        Part.makeBox(6.0, P.glue_channel_width, P.glue_channel_depth, v(P.coupon_width - 6.0, cy - P.glue_channel_width / 2.0, P.coupon_base_thickness - P.glue_channel_depth)),
        Part.makeBox(P.glue_channel_width, 6.0, P.glue_channel_depth, v(cx - P.glue_channel_width / 2.0, 0, P.coupon_base_thickness - P.glue_channel_depth)),
        Part.makeBox(P.glue_channel_width, 6.0, P.glue_channel_depth, v(cx - P.glue_channel_width / 2.0, P.coupon_depth - 6.0, P.coupon_base_thickness - P.glue_channel_depth)),
    )
    for tool in channels:
        male = male.cut(tool)
    female = Part.makeBox(P.coupon_width, P.coupon_depth, P.coupon_female_thickness, v(0, 0, 0))
    female = female.cut(polygon_prism(local_opening, -0.05, P.coupon_female_thickness + 0.10)).removeSplitter()
    return validate_shape("Island_Interface_Coupon_Male", male.removeSplitter()), validate_shape("Island_Interface_Coupon_Female", female)


def build_parts():
    foundation = make_foundation_lower_body()
    bridge, bridge_windows = make_bridge()
    prifly, prifly_windows = make_prifly()
    uptake = make_exhaust_uptake()
    main_mast = make_main_mast()
    secondary_mast = make_secondary_mast()
    yardarm = make_yardarm()
    sps48, sps49, spn50 = make_radars()
    ladder = make_ladder()
    antennas, antenna_print = make_antennas()
    signals = make_signal_lights()
    mark_port = make_marking(True)
    mark_starboard = make_marking(False)
    rot_x90 = App.Rotation(v(1, 0, 0), 90)
    rot_y90 = App.Rotation(v(0, 1, 0), 90)
    parts = [
        PartSpec("Foundation_Lower_Island", foundation, "ash_gray", "foundation_body", "approved opening + source/photo-informed proportions"),
        PartSpec("Navigation_Bridge", bridge, "ash_gray", "navigation_bridge", "2024 official imagery; photo-informed proportions"),
        PartSpec("Primary_Flight_Control", prifly, "ash_gray", "primary_flight_control", "2024 official imagery; photo-informed proportions"),
        PartSpec("Exhaust_Uptake", uptake, "ash_gray", "exhaust_uptake", "2024 official imagery + source silhouette"),
        PartSpec("Main_Mast", main_mast, "ash_gray", "main_mast", "2024 official imagery + source height", rot_x90, print_note="Print mast flat on its aft face"),
        PartSpec("Secondary_Mast", secondary_mast, "ash_gray", "secondary_mast", "2024 official imagery", rot_x90, print_note="Print mast flat"),
        PartSpec("Main_Yardarm", yardarm, "ash_gray", "yardarm", "2024 official imagery", None, print_note="Print crossarm flat"),
        PartSpec("Radar_AN_SPS48G_Array", sps48, "silk_silver", "radar_array", "U.S. Navy SPS-48G CVN backfit + 2024 photo silhouette", rot_x90, print_note="Print detailed face upward"),
        PartSpec("Radar_AN_SPS49_Array", sps49, "silk_silver", "radar_array", "public photo silhouette; identification medium confidence", rot_x90, print_note="Print detailed face upward"),
        PartSpec("Radar_AN_SPN50_Array", spn50, "silk_silver", "radar_array", "NAVAIR-confirmed CVN-69 operational installation", rot_x90, print_note="Print detailed face upward"),
        PartSpec("Bridge_Window_Insert", bridge_windows, "charcoal", "window_insert", "recess-matched CAD insert"),
        PartSpec("PriFly_Window_Insert", prifly_windows, "charcoal", "window_insert", "recess-matched CAD insert"),
        PartSpec("Aft_Access_Ladder", ladder, "ash_gray", "ladder", "printable representative access ladder", rot_y90, print_note="Print ladder flat"),
        PartSpec("Antenna_Detail_Set", antennas, "silk_silver", "antenna_set", "major visible whip antennas; positions photo-informed", None, antenna_print, "Four antennas individually based on bed"),
        PartSpec("Signal_Light_Housings", signals, "basic_black", "signal_lights", "representative major signal housings"),
        PartSpec("Marking_69_Port", mark_port, "ivory_white", "identification_marking", "CVN-69 island identification", rot_x90, print_note="Print marking face up"),
        PartSpec("Marking_69_Starboard", mark_starboard, "ivory_white", "identification_marking", "CVN-69 island identification", rot_x90, print_note="Print marking face up"),
    ]
    for spec in parts:
        validate_shape(spec.name, spec.shape, spec.role in {"window_insert", "antenna_set", "signal_lights", "identification_marking"})
    return parts


def material_key(material_name):
    for key, (name, _color) in MATERIALS.items():
        if material_name == name:
            return key
    if "Charcoal" in material_name:
        return "charcoal"
    if "Ivory" in material_name:
        return "ivory_white"
    if "Silver" in material_name:
        return "silk_silver"
    if "Black" in material_name:
        return "basic_black"
    return "ash_gray"


def load_review_baseline():
    doc = App.openDocument(str(INTEGRATION_FCSTD))
    records = []
    try:
        for obj in doc.Objects:
            if not hasattr(obj, "IntegrationRole") or not hasattr(obj, "Shape") or obj.Shape.isNull():
                continue
            if str(obj.IntegrationRole) == "test_coupon":
                continue
            material = material_key(str(getattr(obj, "Material", "Bambu PLA Matte Ash Gray")))
            records.append(PartSpec(f"Approved_{obj.Name}", obj.Shape.copy(), material, "approved_review_baseline", "approved Milestone 2 BRep"))
    finally:
        App.closeDocument(doc.Name)
    return records


def triangulate(shape, deflection=None):
    points, faces = shape.tessellate(deflection or P.tessellation_deflection)
    vertices = [(float(point.x), float(point.y), float(point.z)) for point in points]
    triangles = [(int(a), int(b), int(c)) for a, b, c in faces]
    return vertices, triangles


def triangle_normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    return (0.0, 0.0, 0.0) if length <= 1.0e-16 else (nx / length, ny / length, nz / length)


def write_binary_stl(path: Path, spec: PartSpec, shape):
    vertices, triangles = triangulate(shape)
    header = f"CVN-69 M3 {spec.name}".encode("ascii", "replace")[:80].ljust(80, b" ")
    with path.open("wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(triangles)))
        for triangle in triangles:
            a, b, c = (vertices[index] for index in triangle)
            normal = triangle_normal(a, b, c)
            handle.write(struct.pack("<12fH", *(normal + a + b + c), 0))
    return len(triangles)


def write_3mf(path: Path, specs, title: str, shapes=None):
    shapes = shapes or [spec.shape for spec in specs]
    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    ET.register_namespace("", ns)
    model = ET.Element(f"{{{ns}}}model", {"unit": "millimeter", "xml:lang": "en-US"})
    metadata = ET.SubElement(model, f"{{{ns}}}metadata", {"name": "Title"})
    metadata.text = title
    resources = ET.SubElement(model, f"{{{ns}}}resources")
    bases = ET.SubElement(resources, f"{{{ns}}}basematerials", {"id": "1"})
    material_index = {}
    for index, (key, (name, color)) in enumerate(MATERIALS.items()):
        material_index[key] = index
        ET.SubElement(bases, f"{{{ns}}}base", {"name": name, "displaycolor": color})
    build = ET.SubElement(model, f"{{{ns}}}build")
    for object_id, (spec, shape) in enumerate(zip(specs, shapes), 2):
        obj = ET.SubElement(resources, f"{{{ns}}}object", {"id": str(object_id), "type": "model", "name": spec.name})
        mesh = ET.SubElement(obj, f"{{{ns}}}mesh")
        vertices_node = ET.SubElement(mesh, f"{{{ns}}}vertices")
        triangles_node = ET.SubElement(mesh, f"{{{ns}}}triangles")
        vertices, triangles = triangulate(shape)
        for x, y, z in vertices:
            ET.SubElement(vertices_node, f"{{{ns}}}vertex", {"x": f"{x:.6f}", "y": f"{y:.6f}", "z": f"{z:.6f}"})
        for a, b, c in triangles:
            ET.SubElement(
                triangles_node,
                f"{{{ns}}}triangle",
                {"v1": str(a), "v2": str(b), "v3": str(c), "pid": "1", "p1": str(material_index[spec.material])},
            )
        ET.SubElement(build, f"{{{ns}}}item", {"objectid": str(object_id)})
    model_xml = ET.tostring(model, encoding="utf-8", xml_declaration=True)
    content_types = b'''<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'''
    rels = b'''<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'''
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("3D/3dmodel.model", model_xml)


def write_obj(path: Path, specs):
    mtl_path = path.with_suffix(".mtl")
    with mtl_path.open("w", encoding="utf-8") as handle:
        for key, (name, color) in MATERIALS.items():
            rgb = tuple(int(color[index:index + 2], 16) / 255.0 for index in (1, 3, 5))
            handle.write(f"newmtl {key}\n# {name}\nKd {rgb[0]:.6f} {rgb[1]:.6f} {rgb[2]:.6f}\n\n")
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f"mtllib {mtl_path.name}\n")
        offset = 1
        for spec in specs:
            vertices, triangles = triangulate(spec.shape)
            handle.write(f"o {spec.name}\nusemtl {spec.material}\n")
            for x, y, z in vertices:
                handle.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
            for a, b, c in triangles:
                handle.write(f"f {a + offset} {b + offset} {c + offset}\n")
            offset += len(vertices)


def print_shape(spec: PartSpec):
    source = spec.print_override if spec.print_override is not None else spec.shape
    return transform_shape(source, spec.print_rotation, (0.0, 0.0, 0.0))


def pack_plate(specs, max_size=235.0, gap=3.0):
    packed = []
    shapes = []
    cursor_x = cursor_y = row_height = 0.0
    for spec in specs:
        shape = print_shape(spec)
        bounds = precise_bounds(shape)
        width, depth = bounds[3] - bounds[0], bounds[4] - bounds[1]
        if width > max_size or depth > max_size:
            raise RuntimeError(f"{spec.name} exceeds print plate")
        if cursor_x > 0.0 and cursor_x + width > max_size:
            cursor_x = 0.0
            cursor_y += row_height + gap
            row_height = 0.0
        if cursor_y + depth > max_size:
            raise RuntimeError(f"Plate overflow while placing {spec.name}")
        shape.translate(v(cursor_x, cursor_y, 0))
        packed.append(spec)
        shapes.append(shape)
        cursor_x += width + gap
        row_height = max(row_height, depth)
    return packed, shapes


def add_spreadsheet(doc):
    sheet = doc.addObject("Spreadsheet::Sheet", "IslandParameters")
    rows = (
        ("Parameter", "Value", "Unit / provenance"),
        ("Overall length", P.overall_length, "mm; approved integration import"),
        ("Deck underside", P.deck_base_z, "mm; approved integration import"),
        ("Deck top", P.deck_top_z, "mm; approved integration import"),
        ("Opening bounds", ", ".join(f"{value:.3f}" for value in P.opening_bounds), "x0,y0,x1,y1 mm; transformed approved opening"),
        ("Interface clearance", P.interface_clearance_per_side, "mm per side"),
        ("Interface plug depth", P.interface_plug_depth, "mm"),
        ("Foundation flange", P.foundation_flange_offset, "mm hidden perimeter offset"),
        ("Glue channel", f"{P.glue_channel_width} × {P.glue_channel_depth}", "mm"),
        ("Minimum wall", P.minimum_structural_wall, "mm"),
        ("Minimum freestanding mast", P.minimum_freestanding_mast, "mm"),
        ("Mast height above deck", P.mast_top_height, "mm; source/photo informed"),
        ("Configuration", P.configuration_period, "public-source freeze"),
    )
    for row_index, row in enumerate(rows, 1):
        for column_index, value in enumerate(row, 1):
            sheet.set(f"{chr(64 + column_index)}{row_index}", str(value))
    sheet.setStyle("A1:C1", "bold", "add")
    sheet.setColumnWidth("A", 190)
    sheet.setColumnWidth("B", 310)
    sheet.setColumnWidth("C", 310)


def add_part(doc, group, spec):
    obj = doc.addObject("Part::Feature", spec.name)
    obj.Label = spec.name.replace("_", " ")
    obj.Shape = spec.shape
    obj.addProperty("App::PropertyString", "IslandRole").IslandRole = spec.role
    obj.addProperty("App::PropertyString", "Material").Material = MATERIALS[spec.material][0]
    obj.addProperty("App::PropertyString", "EvidenceBasis").EvidenceBasis = spec.evidence
    obj.addProperty("App::PropertyString", "PrintOrientation").PrintOrientation = spec.print_note
    colors = {
        "ash_gray": (0.59, 0.60, 0.56),
        "charcoal": (0.20, 0.22, 0.24),
        "silk_silver": (0.68, 0.71, 0.73),
        "ivory_white": (0.92, 0.90, 0.84),
        "basic_black": (0.08, 0.09, 0.10),
    }
    try:
        obj.ViewObject.ShapeColor = colors[spec.material]
    except Exception:
        pass
    group.addObject(obj)
    return obj


def create_document(parts, coupon_specs):
    doc = App.newDocument("CVN69_Island")
    info = doc.addObject("App::FeaturePython", "MilestoneInformation")
    info.addProperty("App::PropertyString", "ProjectName").ProjectName = "USS Dwight D. Eisenhower (CVN-69) Museum Edition"
    info.addProperty("App::PropertyString", "Milestone").Milestone = P.milestone
    info.addProperty("App::PropertyString", "Version").Version = P.version
    info.addProperty("App::PropertyString", "ConfigurationPeriod").ConfigurationPeriod = P.configuration_period
    info.addProperty("App::PropertyString", "CoordinateSystem").CoordinateSystem = "X=0 bow to 476 stern; Y port(-)/starboard(+); Z keel datum"
    info.addProperty("App::PropertyString", "GeometryStatus").GeometryStatus = "New parametric BRep geometry; source STL used only for reference audit"
    info.addProperty("App::PropertyString", "ScopeBoundary").ScopeBoundary = "Island only; no weapons, aircraft, vehicles, ocean base, or final release"
    info.addProperty("App::PropertyString", "Generator").Generator = str(SCRIPT.relative_to(REPO))
    add_spreadsheet(doc)

    refs = doc.addObject("App::DocumentObjectGroup", "ConstructionReferences")
    opening = doc.addObject("Part::Feature", "Approved_Island_Opening")
    opening.Shape = polygon_wire(P.opening_authoritative, P.deck_top_z)
    opening.Visibility = False
    refs.addObject(opening)
    plug_ref = doc.addObject("Part::Feature", "Interface_Plug_Reference")
    plug_ref.Shape = polygon_prism(P.interface_plug_points, P.deck_top_z - P.interface_plug_depth, P.interface_plug_depth)
    plug_ref.Visibility = False
    refs.addObject(plug_ref)
    deck_datum = doc.addObject("Part::Feature", "Approved_Deck_Top_Datum")
    deck_datum.Shape = Part.makePlane(55, 35, v(P.opening_bounds[0] - 10, P.opening_bounds[1] - 10, P.deck_top_z))
    deck_datum.Visibility = False
    refs.addObject(deck_datum)

    assembly = doc.addObject("App::DocumentObjectGroup", "IslandAssembly")
    structures = doc.addObject("App::DocumentObjectGroup", "StructuralParts")
    sensors = doc.addObject("App::DocumentObjectGroup", "MastsSensorsDetails")
    inserts = doc.addObject("App::DocumentObjectGroup", "ColorInsertsMarkings")
    coupons = doc.addObject("App::DocumentObjectGroup", "InterfaceCoupon")
    for group in (structures, sensors, inserts, coupons):
        assembly.addObject(group)
    objects = []
    for spec in parts:
        if spec.role in {"foundation_body", "navigation_bridge", "primary_flight_control", "exhaust_uptake"}:
            group = structures
        elif spec.role in {"window_insert", "identification_marking"}:
            group = inserts
        else:
            group = sensors
        objects.append(add_part(doc, group, spec))
    coupon_objects = [add_part(doc, coupons, spec) for spec in coupon_specs]
    for obj in coupon_objects:
        obj.Visibility = False
    doc.recompute()
    return doc, objects, coupon_objects


def export_review_step(path: Path, baseline, parts):
    doc = App.newDocument("CVN69_Hull_Deck_Island_Review")
    objects = []
    try:
        for spec in baseline + parts:
            obj = doc.addObject("Part::Feature", spec.name)
            obj.Shape = spec.shape
            objects.append(obj)
        doc.recompute()
        Part.export(objects, str(path))
    finally:
        App.closeDocument(doc.Name)


def shape_record(spec, print_version):
    bounds = precise_bounds(spec.shape)
    print_bounds = precise_bounds(print_version)
    messages = []
    try:
        spec.shape.check(True)
    except ValueError as exc:
        messages = [line.strip() for line in str(exc).splitlines() if line.strip()]
    return {
        "name": spec.name,
        "role": spec.role,
        "material": MATERIALS[spec.material][0],
        "evidence_basis": spec.evidence,
        "valid": bool(spec.shape.isValid()),
        "closed_solids": all(solid.isClosed() for solid in spec.shape.Solids),
        "solid_count": len(spec.shape.Solids),
        "volume_mm3": round(float(spec.shape.Volume), 6),
        "strict_bop_messages": messages,
        "assembly_bounds_mm": [round(value, 5) for value in bounds],
        "print_bounds_mm": [round(value, 5) for value in print_bounds],
        "print_size_mm": [round(print_bounds[3] - print_bounds[0], 5), round(print_bounds[4] - print_bounds[1], 5), round(print_bounds[5] - print_bounds[2], 5)],
        "print_note": spec.print_note,
    }


def approved_input_records():
    paths = list(APPROVED_PATHS) + sorted((PROJECT / "Integration" / "QA").glob("*"))
    return {
        str(path.relative_to(REPO)): {"bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in paths
        if path.is_file()
    }


def main():
    print("Building CVN-69 Milestone 3 island reconstruction")
    for pattern_dir, pattern in ((DIRS["stl"], "*.stl"), (DIRS["step"], "*.step"), (DIRS["3mf"], "*.3mf"), (DIRS["obj"], "CVN69_Island_Assembly.*")):
        for stale in pattern_dir.glob(pattern):
            stale.unlink()

    parts = build_parts()
    male, female = make_coupon()
    coupon_specs = [
        PartSpec("Island_Interface_Coupon_Male", male, "ash_gray", "interface_coupon", "exact production male plug/clearance/glue channels"),
        PartSpec("Island_Interface_Coupon_Female", female, "charcoal", "interface_coupon", "exact approved opening female geometry"),
    ]
    baseline = load_review_baseline()
    approved_records = approved_input_records()
    inspection = {
        "inspected_utc": datetime.now(timezone.utc).isoformat(),
        "freecad_version": ".".join(App.Version()[:3]),
        "coordinate_system": {"x": "0 bow to 476 stern", "y": "port negative / starboard positive", "z": "keel datum"},
        "deck_base_z_mm": P.deck_base_z,
        "deck_top_z_mm": P.deck_top_z,
        "opening_authoritative_mm": [list(point) for point in P.opening_authoritative],
        "opening_bounds_mm": list(P.opening_bounds),
        "approved_files": approved_records,
        "read_only_policy": "Approved Milestone 1 and 2 inputs are opened read-only and are not overwritten.",
    }
    inspection_path = DIRS["qa"] / "Approved_Input_Inspection.json"
    inspection_path.write_text(json.dumps(inspection, indent=2) + "\n", encoding="utf-8")

    doc, objects, coupon_objects = create_document(parts, coupon_specs)
    fcstd_path = DIRS["freecad"] / "CVN69_Island.FCStd"
    doc.saveAs(str(fcstd_path))
    assembly_step = DIRS["step"] / "CVN69_Island_Assembly.step"
    coupon_step = DIRS["step"] / "CVN69_Island_Interface_Coupon.step"
    Part.export(objects, str(assembly_step))
    Part.export(coupon_objects, str(coupon_step))

    obj_path = DIRS["obj"] / "CVN69_Island_Assembly.obj"
    write_obj(obj_path, parts)
    assembly_3mf = DIRS["3mf"] / "CVN69_Island_Assembly.3mf"
    write_3mf(assembly_3mf, parts, "CVN-69 Milestone 3 Island Assembly")

    plate_groups = (
        ("Print_Plate_01_Island_Body.3mf", parts[:4], "CVN-69 Island — Structural Body"),
        ("Print_Plate_02_Mast_Radar.3mf", parts[4:10], "CVN-69 Island — Masts and Radar"),
        ("Print_Plate_03_Antennas_Details.3mf", parts[10:], "CVN-69 Island — Inserts, Antennas, and Details"),
    )
    plate_paths = []
    for filename, group, title in plate_groups:
        packed_specs, packed_shapes = pack_plate(group)
        path = DIRS["3mf"] / filename
        write_3mf(path, packed_specs, title, packed_shapes)
        plate_paths.append(path)

    coupon_packed, coupon_shapes = pack_plate(coupon_specs, max_size=60.0, gap=3.0)
    coupon_3mf = DIRS["3mf"] / "Island_Interface_Test_Coupon.3mf"
    write_3mf(coupon_3mf, coupon_packed, "CVN-69 Island Interface Test Coupon", coupon_shapes)

    review_step = DIRS["step"] / "CVN69_Hull_Deck_Island_Review.step"
    export_review_step(review_step, baseline, parts)
    review_3mf = DIRS["3mf"] / "CVN69_Hull_Deck_Island_Review.3mf"
    write_3mf(review_3mf, baseline + parts, "CVN-69 Hull Deck Island Review")

    print_versions = {spec.name: print_shape(spec) for spec in parts + coupon_specs}
    stl_facets = {}
    stl_paths = []
    for spec in parts + coupon_specs:
        path = DIRS["stl"] / f"{spec.name}.stl"
        stl_facets[path.name] = write_binary_stl(path, spec, print_versions[spec.name])
        stl_paths.append(path)

    output_paths = [
        fcstd_path,
        assembly_step,
        coupon_step,
        review_step,
        obj_path,
        obj_path.with_suffix(".mtl"),
        assembly_3mf,
        *plate_paths,
        coupon_3mf,
        review_3mf,
        *stl_paths,
    ]
    reference_outputs = [
        DIRS["references"] / "Source_Mesh_Island_Measurements.json",
        DIRS["images"] / "Source_Mesh_Island_Reference.png",
    ]
    output_paths.extend(path for path in reference_outputs if path.exists())
    manifest = {
        "project": "USS Dwight D. Eisenhower (CVN-69) 1:700 Museum Edition",
        "milestone": P.milestone,
        "version": P.version,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "freecad_version": ".".join(App.Version()[:3]),
        "configuration_period": P.configuration_period,
        "coordinate_system": {"x": "0 mm bow to 476 mm stern", "y": "port negative / starboard positive", "z": "vertical from keel datum"},
        "parameters_mm": {
            "overall_length": P.overall_length,
            "deck_base_z": P.deck_base_z,
            "deck_top_z": P.deck_top_z,
            "opening_bounds": list(P.opening_bounds),
            "interface_clearance_per_side": P.interface_clearance_per_side,
            "interface_plug_depth": P.interface_plug_depth,
            "foundation_flange_offset": P.foundation_flange_offset,
            "glue_channel_width": P.glue_channel_width,
            "glue_channel_depth": P.glue_channel_depth,
            "minimum_structural_wall": P.minimum_structural_wall,
            "minimum_freestanding_mast": P.minimum_freestanding_mast,
            "minimum_railing": P.minimum_railing,
            "minimum_antenna": P.minimum_antenna,
            "mast_height_above_deck": P.mast_top_height,
        },
        "counts": {"production_parts": len(parts), "coupon_parts": len(coupon_specs), "review_baseline_objects": len(baseline)},
        "material_mapping": {spec.name: MATERIALS[spec.material][0] for spec in parts},
        "parts": [shape_record(spec, print_versions[spec.name]) for spec in parts],
        "coupon_parts": [shape_record(spec, print_versions[spec.name]) for spec in coupon_specs],
        "stl_facets": stl_facets,
        "approved_input_hashes": approved_records,
        "outputs": {
            str(path.relative_to(ISLAND)): {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in output_paths
        },
    }
    manifest_path = DIRS["qa"] / "build_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    App.closeDocument(doc.Name)
    print(json.dumps({"status": "ok", "production_parts": len(parts), "coupon_parts": 2, "stl_files": len(stl_paths), "manifest": str(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()
