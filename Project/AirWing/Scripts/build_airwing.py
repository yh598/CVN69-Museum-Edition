#!/usr/bin/env python3
"""Build Milestone 5 aircraft as new parametric FreeCAD/OpenCascade solids.

No STL or source triangle is opened. Approved ship files are read only for
datums and later review assembly generation.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import FreeCAD as App
import Part


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
PROJECT = ROOT / "Project"
M5 = PROJECT / "AirWing"
sys.path.insert(0, str(M5 / "CAD" / "Python"))
from airwing_parameters import make_parameters  # noqa: E402


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = make_parameters()
UTIL = load_module("m5_freecad_utilities", PROJECT / "WeaponsDeckEdge" / "Scripts" / "build_weapons_deckedge.py")
UTIL.P = P
UTIL.UTIL.P = P

DIRS = {name: M5 / folder for name, folder in {
    "freecad": "CAD/FreeCAD", "step": "STEP", "stl": "STL", "3mf": "3MF",
    "obj": "OBJ", "render": "Render", "images": "Images", "layout": "Layout",
    "assembly": "Assembly", "docs": "Docs", "qa": "QA", "references": "References",
}.items()}
for directory in DIRS.values():
    directory.mkdir(parents=True, exist_ok=True)

MATERIALS = OrderedDict((
    ("blue_grey", ("Bambu PLA Basic Blue Grey", "#73818AFF")),
    ("charcoal", ("Bambu PLA Matte Charcoal", "#34383CFF")),
    ("ivory", ("Bambu PLA Matte Ivory White", "#ECE8D9FF")),
    ("silver", ("Bambu PLA Silk Silver", "#AEB4B8FF")),
))
UTIL.MATERIALS = MATERIALS
UTIL.UTIL.MATERIALS = MATERIALS

APPROVED_PATHS = (
    PROJECT / "Integration" / "CAD" / "FreeCAD" / "CVN69_Hull_Deck_Integration.FCStd",
    PROJECT / "Integration" / "CAD" / "Python" / "integration_parameters.py",
    PROJECT / "Integration" / "QA" / "Production_Interface_Freeze.json",
    PROJECT / "Island" / "CAD" / "FreeCAD" / "CVN69_Island.FCStd",
    PROJECT / "Island" / "CAD" / "Python" / "island_parameters.py",
    PROJECT / "WeaponsDeckEdge" / "CAD" / "FreeCAD" / "CVN69_Weapons_DeckEdge.FCStd",
    PROJECT / "WeaponsDeckEdge" / "CAD" / "Python" / "weapons_deckedge_parameters.py",
)


@dataclass
class PartSpec:
    name: str
    shape: object
    material: str
    role: str
    aircraft_code: str
    variant: str
    evidence: str
    classification: str
    minimum_feature_mm: float
    print_rotation: object = None
    print_override: object = None
    print_note: str = "Flat engineered support/bed face at z=0; no support required"
    allow_multiple: bool = False


v = UTIL.v
polygon_prism = UTIL.polygon_prism
fuse_all = UTIL.fuse_all
precise_bounds = UTIL.precise_bounds
validate_shape = UTIL.validate_shape
pack_plate = UTIL.pack_plate
write_3mf = UTIL.write_3mf
write_obj = UTIL.write_obj
write_binary_stl = UTIL.write_binary_stl
print_shape = UTIL.print_shape


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def vertical_plate(points_xz, y0, thickness):
    wire = Part.makePolygon([v(x, y0, z) for x, z in points_xz] + [v(points_xz[0][0], y0, points_xz[0][1])])
    return Part.Face(wire).extrude(v(0, thickness, 0))


def clean(shape):
    shape = shape.removeSplitter()
    if shape.isNull() or not shape.isValid() or not shape.Solids:
        raise RuntimeError("invalid generated shape")
    return shape


def jet_body(item, variant):
    length = item.model_length
    span = item.model_span if variant != "folded" else item.folded_span
    half_l, half_s = length / 2.0, span / 2.0
    gear = [
        Part.makeBox(P.minimum_gear, P.minimum_gear, 0.70, v(half_l - 5.0, -P.minimum_gear / 2, 0)),
        Part.makeBox(1.10, P.minimum_gear, 0.80, v(-1.2, -1.18, 0)),
        Part.makeBox(1.10, P.minimum_gear, 0.80, v(-1.2, 0.38, 0)),
    ]
    fuselage = polygon_prism((
        (-half_l, -0.55), (-half_l + 4.0, -0.82), (3.2, -0.82),
        (half_l - 2.0, -0.58), (half_l, 0.0), (half_l - 2.0, 0.58),
        (3.2, 0.82), (-half_l + 4.0, 0.82),
    ), 0.34, 1.22)
    wing_root_x = 0.3
    wings = polygon_prism((
        (-4.0, -1.0), (-2.2, -half_s), (2.5, -half_s), (4.0, -1.0),
        (4.0, 1.0), (2.5, half_s), (-2.2, half_s), (-4.0, 1.0),
    ), 0.60, P.wing_thickness)
    tail_span = 5.0 if variant != "folded" else 4.2
    tailplane = polygon_prism((
        (-half_l + 1.0, -0.60), (-half_l + 2.7, -tail_span / 2),
        (-half_l + 4.5, -tail_span / 2), (-half_l + 4.0, -0.60),
        (-half_l + 4.0, 0.60), (-half_l + 4.5, tail_span / 2),
        (-half_l + 2.7, tail_span / 2), (-half_l + 1.0, 0.60),
    ), 0.78, P.stabilizer_thickness)
    fin_points = ((-half_l + 2.1, 1.10), (-half_l + 5.0, 1.10), (-half_l + 3.2, 3.05), (-half_l + 2.2, 3.05))
    fins = [vertical_plate(fin_points, offset - P.fin_thickness / 2, P.fin_thickness) for offset in (-1.05, 1.05)]
    pieces = [*gear, fuselage, wings, tailplane, *fins]
    # Enlarged, printable twin exhaust blocks and main-gear shoulders preserve
    # the family silhouette and create continuous layers from the bed.
    pieces += [
        Part.makeBox(2.6, 0.82, 0.72, v(-half_l + 0.2, -1.10, 0.28)),
        Part.makeBox(2.6, 0.82, 0.72, v(-half_l + 0.2, 0.28, 0.28)),
    ]
    if item.code.startswith("EA18G"):
        pieces += [
            Part.makeBox(3.0, 0.80, 0.80, v(-0.2, -half_s, 0.58)),
            Part.makeBox(3.0, 0.80, 0.80, v(-0.2, half_s - 0.80, 0.58)),
            Part.makeBox(2.4, 0.70, 0.65, v(-2.0, -0.35, 1.42)),
        ]
    if variant == "launch":
        pieces += [
            Part.makeBox(3.2, P.minimum_gear, 0.30, v(half_l - 4.4, -P.minimum_gear / 2, 0)),
            Part.makeBox(0.90, 2.20, 0.30, v(half_l - 1.5, -1.10, 0)),
        ]
    return clean(fuse_all(pieces))


def fixed_wing_body(item, variant, hawkeye=False):
    length = item.model_length
    span = item.model_span if variant != "folded" else item.folded_span
    half_l, half_s = length / 2.0, span / 2.0
    cargo = item.code.startswith("C2A")
    fuselage_half = 1.35 if cargo else 1.05
    gear = [
        Part.makeBox(P.minimum_gear, P.minimum_gear, 0.76, v(half_l - 4.6, -P.minimum_gear / 2, 0)),
        Part.makeBox(1.10, P.minimum_gear, 0.82, v(-0.5, -1.20, 0)),
        Part.makeBox(1.10, P.minimum_gear, 0.82, v(-0.5, 0.40, 0)),
    ]
    fuselage = polygon_prism((
        (-half_l, -0.65), (-half_l + 2.0, -fuselage_half), (half_l - 3.2, -fuselage_half),
        (half_l - 0.8, -0.75), (half_l, 0), (half_l - 0.8, 0.75),
        (half_l - 3.2, fuselage_half), (-half_l + 2.0, fuselage_half),
    ), 0.38, 1.45 if cargo else 1.35)
    wing = polygon_prism((
        (-2.8, -1.0), (-1.3, -half_s), (2.1, -half_s), (3.2, -1.0),
        (3.2, 1.0), (2.1, half_s), (-1.3, half_s), (-2.8, 1.0),
    ), 0.72, P.wing_thickness)
    pieces = [*gear, fuselage, wing]
    nacelle_y = min(5.6, max(3.3, half_s * 0.44))
    for y0 in (-nacelle_y, nacelle_y):
        pieces.append(Part.makeBox(4.8, 1.35, 1.25, v(-0.3, y0 - 0.675, 0.38)))
        # Four-blade FDM-safe propeller cross integrated into the nacelle.
        pieces.append(Part.makeBox(0.72, 5.0, 0.70, v(4.0, y0 - 2.5, 0.68)))
        pieces.append(Part.makeBox(0.72, 0.80, 3.6, v(4.0, y0 - 0.40, 0.10)))
    tailplane = polygon_prism((
        (-half_l + 0.5, -0.8), (-half_l + 2.0, -4.3), (-half_l + 4.1, -4.3), (-half_l + 3.5, -0.8),
        (-half_l + 3.5, 0.8), (-half_l + 4.1, 4.3), (-half_l + 2.0, 4.3), (-half_l + 0.5, 0.8),
    ), 1.02, P.stabilizer_thickness)
    pieces.append(tailplane)
    if hawkeye:
        fin_x = -half_l + 2.5
        for y0 in (-3.2, -1.1, 1.1, 3.2):
            pieces.append(vertical_plate(((fin_x, 1.10), (fin_x + 2.6, 1.10), (fin_x + 1.5, 3.40), (fin_x + 0.5, 3.40)), y0 - P.fin_thickness / 2, P.fin_thickness))
        pieces.append(Part.makeCylinder(0.45, 1.7, v(-0.6, 0, 1.30)))
    else:
        fin_x = -half_l + 1.6
        pieces.append(vertical_plate(((fin_x, 1.10), (fin_x + 3.5, 1.10), (fin_x + 1.8, 4.10), (fin_x + 0.7, 4.10)), -P.fin_thickness / 2, P.fin_thickness))
    if variant == "launch":
        pieces.append(Part.makeBox(3.0, P.minimum_gear, 0.30, v(half_l - 4.2, -P.minimum_gear / 2, 0)))
        pieces.append(Part.makeBox(0.90, 2.2, 0.30, v(half_l - 1.4, -1.1, 0)))
    return clean(fuse_all(pieces))


def helo_body(item):
    length = item.model_length
    half_l = length / 2
    r_variant = item.code.startswith("MH60R")
    body_half = 1.55 if r_variant else 1.75
    gear = [
        Part.makeBox(P.minimum_gear, P.minimum_gear, 0.78, v(half_l - 4.6, -P.minimum_gear / 2, 0)),
        Part.makeBox(1.10, P.minimum_gear, 0.82, v(-0.4, -1.48, 0)),
        Part.makeBox(1.10, P.minimum_gear, 0.82, v(-0.4, 0.68, 0)),
    ]
    cabin = polygon_prism((
        (-2.8, -body_half), (4.2, -body_half), (half_l - 1.5, -1.05), (half_l, 0),
        (half_l - 1.5, 1.05), (4.2, body_half), (-2.8, body_half),
    ), 0.42, 1.65)
    boom = polygon_prism(((-half_l, -0.38), (-2.0, -0.70), (-2.0, 0.70), (-half_l, 0.38)), 0.80, 0.82)
    fin = vertical_plate(((-half_l, 0.75), (-half_l + 3.0, 0.75), (-half_l + 1.25, 4.0), (-half_l + 0.25, 4.0)), -P.fin_thickness / 2, P.fin_thickness)
    stabilizer = Part.makeBox(3.2, 5.0, P.stabilizer_thickness, v(-half_l + 2.0, -2.5, 1.05))
    pieces = [*gear, cabin, boom, fin, stabilizer]
    if r_variant:
        pieces.append(Part.makeBox(1.0, 1.0, 0.80, v(half_l - 3.0, -0.50, 0.25)))
    return clean(fuse_all(pieces))


def canopy(item):
    if item.code.startswith("FA18") or item.code.startswith("EA18"):
        length = 5.4 if item.code.startswith("FA18F") or item.code.startswith("EA18") else 4.2
        points = ((-length / 2, -0.55), (length / 2 - 0.6, -0.55), (length / 2, 0), (length / 2 - 0.6, 0.55), (-length / 2, 0.55))
        return polygon_prism(points, 0, P.insert_thickness)
    if item.code.startswith(("E2C", "C2A")):
        return polygon_prism(((-2.2, -0.75), (1.6, -0.75), (2.2, 0), (1.6, 0.75), (-2.2, 0.75)), 0, P.insert_thickness)
    return polygon_prism(((-2.0, -1.0), (1.0, -1.0), (2.0, 0), (1.0, 1.0), (-2.0, 1.0)), 0, P.insert_thickness)


def rotodome(item):
    radius = item.dome_diameter / 2.0
    return clean(fuse_all((Part.makeCylinder(radius, P.insert_thickness), Part.makeCylinder(0.55, 1.20, v(0, 0, 0)))))


def rotor(item, variant):
    radius = item.rotor_diameter / 2.0
    hub = Part.makeCylinder(0.70, P.rotor_blade_thickness)
    pieces = [hub]
    if variant == "deployed":
        blade = Part.makeBox(radius - 0.35, P.rotor_blade_width, P.rotor_blade_thickness, v(0.35, -P.rotor_blade_width / 2, 0))
        for angle in (0, 90, 180, 270):
            part = blade.copy()
            part.rotate(v(0, 0, 0), v(0, 0, 1), angle)
            pieces.append(part)
    else:
        blade_length = radius - 0.35
        for index, y0 in enumerate((-1.05, -0.35, 0.35, 1.05)):
            part = Part.makeBox(2 * blade_length, P.rotor_blade_width, P.rotor_blade_thickness, v(-blade_length, y0 - P.rotor_blade_width / 2, 0))
            pieces.append(part)
    return clean(fuse_all(pieces))


def marking_tile(item, index):
    base = Part.makeBox(2.6, 1.20, P.marking_height)
    pieces = [base]
    for stripe in range(1 + index % 3):
        pieces.append(Part.makeBox(P.marking_width, 1.20, P.marking_height, v(0.35 + stripe * 0.75, 0, P.marking_height)))
    return clean(fuse_all(pieces))


def supported_print_body(shape, item, variant):
    """Add removable bed-connected rails without changing assembly geometry."""
    half_l = item.model_length / 2.0
    supports = []
    if item.code.startswith(("FA18", "EA18")):
        supports.append(Part.makeBox(item.model_length - 2.8, P.minimum_gear, 0.66, v(-half_l + 1.4, -P.minimum_gear / 2, 0)))
        if item.code.startswith("EA18"):
            span = item.model_span if variant != "folded" else item.folded_span
            half_s = span / 2.0
            supports.append(Part.makeBox(3.0, P.minimum_gear, 0.66, v(-0.2, -half_s, 0)))
            supports.append(Part.makeBox(3.0, P.minimum_gear, 0.66, v(-0.2, half_s - P.minimum_gear, 0)))
    elif item.code.startswith(("E2C", "C2A")):
        supports.append(Part.makeBox(item.model_length - 2.4, P.minimum_gear, 0.72, v(-half_l + 1.2, -P.minimum_gear / 2, 0)))
        span = item.model_span if variant != "folded" else item.folded_span
        nacelle_y = min(5.6, max(3.3, span * 0.44 / 2.0))
        for y0 in (-nacelle_y, nacelle_y):
            supports.append(Part.makeBox(6.2, P.minimum_gear, 0.76, v(-1.0, y0 - P.minimum_gear / 2, 0)))
    else:
        supports.append(Part.makeBox(item.model_length - 2.2, P.minimum_gear, 0.70, v(-half_l + 1.2, -P.minimum_gear / 2, 0)))
    return clean(fuse_all((shape, *supports)))


def plate_margin(shapes, margin):
    result = []
    for shape in shapes:
        shifted = shape.copy()
        shifted.translate(v(margin, margin, 0))
        result.append(shifted)
    return result


def build_parts():
    parts = []
    for type_index, item in enumerate(P.aircraft_types):
        for variant in item.variants:
            if item.code.startswith(("FA18", "EA18")):
                shape = jet_body(item, variant)
            elif item.code.startswith("E2C"):
                shape = fixed_wing_body(item, variant, hawkeye=True)
            elif item.code.startswith("C2A"):
                shape = fixed_wing_body(item, variant, hawkeye=False)
            else:
                shape = helo_body(item)
            parts.append(PartSpec(
                f"{item.code}_{variant.title()}_Body", shape, "blue_grey", "aircraft_body",
                item.code, variant, item.evidence_url,
                "official-dimension envelope; photo-informed silhouette; FDM-safe parametric reconstruction",
                P.wing_thickness, print_override=supported_print_body(shape, item, variant),
                print_note="Assembly BRep plus removable 0.80 mm bed-connected belly/engine rails; z=0 continuous slice support",
            ))
        parts.append(PartSpec(
            f"{item.code}_Canopy_Insert", canopy(item), "charcoal", "canopy_insert", item.code, "universal",
            item.evidence_url, "no-paint glue-on insert; silhouette simplified", P.insert_thickness,
        ))
        if item.dome_diameter:
            parts.append(PartSpec(
                f"{item.code}_Rotodome", rotodome(item), "ivory", "rotodome", item.code, "universal",
                item.dimension_url, "official 24 ft diameter; thickness enlarged to FDM minimum", P.insert_thickness,
            ))
        if item.rotor_diameter:
            for variant in item.variants:
                parts.append(PartSpec(
                    f"{item.code}_{variant.title()}_Main_Rotor", rotor(item, variant), "silver", "main_rotor",
                    item.code, variant, item.dimension_url,
                    "official rotor diameter for deployed state; blade chord/thickness enlarged for FDM", P.rotor_blade_thickness,
                ))
        parts.append(PartSpec(
            f"{item.code}_Squadron_ID_Insert", marking_tile(item, type_index), "ivory", "squadron_id_insert",
            item.code, "universal", item.evidence_url,
            "confirmed unit identity; neutral bar-code tile, not invented insignia artwork", P.marking_height,
        ))
    if len(parts) != 48:
        raise RuntimeError(f"expected 48 production objects, got {len(parts)}")
    for spec in parts:
        validate_shape(spec.name, spec.shape, spec.allow_multiple)
    return parts


def family_parts(parts, code):
    return [spec for spec in parts if spec.aircraft_code == code]


def export_step(path, specs, shapes=None):
    shapes = shapes or [spec.shape for spec in specs]
    doc = App.newDocument(path.stem)
    objects = []
    try:
        for spec, shape in zip(specs, shapes):
            obj = doc.addObject("Part::Feature", spec.name)
            obj.Shape = shape
            objects.append(obj)
        doc.recompute()
        Part.export(objects, str(path))
    finally:
        App.closeDocument(doc.Name)


def add_spreadsheet(doc):
    sheet = doc.addObject("Spreadsheet::Sheet", "AirWingParameters")
    rows = (
        ("Parameter", "Value", "Unit / source"),
        ("Scale", "1:700", "fixed"),
        ("Ship length", P.overall_length, "mm approved baseline"),
        ("Deck top", P.deck_top_z, "mm approved baseline"),
        ("Frozen interface clearance", P.integration.interface_clearance_per_side, "mm/side immutable"),
        ("Aircraft glue clearance", P.assembly_clearance_per_side, "mm/side"),
        ("Wing/stabilizer", P.wing_thickness, "mm minimum"),
        ("Rotor blade", f"{P.rotor_blade_width} × {P.rotor_blade_thickness}", "mm"),
        ("Configuration", P.configuration_period, "official-source freeze"),
        ("Production objects", 48, "25 bodies + inserts/details"),
    )
    for r, row in enumerate(rows, 1):
        for c, value in enumerate(row, 1):
            sheet.set(f"{chr(64+c)}{r}", str(value))
    sheet.setStyle("A1:C1", "bold", "add")
    sheet.setColumnWidth("A", 220)
    sheet.setColumnWidth("B", 280)
    sheet.setColumnWidth("C", 300)


def add_part(doc, group, spec, shape):
    obj = doc.addObject("Part::Feature", spec.name)
    obj.Label = spec.name.replace("_", " ")
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "AirWingRole").AirWingRole = spec.role
    obj.addProperty("App::PropertyString", "AircraftCode").AircraftCode = spec.aircraft_code
    obj.addProperty("App::PropertyString", "Variant").Variant = spec.variant
    obj.addProperty("App::PropertyString", "Material").Material = MATERIALS[spec.material][0]
    obj.addProperty("App::PropertyString", "EvidenceBasis").EvidenceBasis = spec.evidence
    obj.addProperty("App::PropertyString", "AccuracyClassification").AccuracyClassification = spec.classification
    obj.addProperty("App::PropertyLength", "MinimumDesignedFeature").MinimumDesignedFeature = spec.minimum_feature_mm
    obj.addProperty("App::PropertyString", "PrintOrientation").PrintOrientation = spec.print_note
    colors = {"blue_grey": (0.45, 0.51, 0.55), "charcoal": (0.20, 0.22, 0.24), "ivory": (0.92, 0.90, 0.84), "silver": (0.68, 0.71, 0.73)}
    try:
        obj.ViewObject.ShapeColor = colors[spec.material]
    except Exception:
        pass
    group.addObject(obj)
    return obj


def create_document(parts, gallery_shapes):
    doc = App.newDocument("CVN69_AirWing_Master")
    info = doc.addObject("App::FeaturePython", "MilestoneInformation")
    for prop, value in (
        ("ProjectName", "USS Dwight D. Eisenhower (CVN-69) 1:700 Museum Edition"),
        ("Milestone", P.milestone), ("Version", P.version),
        ("ConfigurationPeriod", P.configuration_period),
        ("CoordinateSystem", "Master objects use local aircraft coordinates; layout uses x=0 bow to x=476 stern"),
        ("GeometryStatus", "New parametric OpenCascade BReps; no mesh triangles used"),
        ("ScopeBoundary", "Carrier air wing only; approved ship geometry unchanged"),
        ("Generator", str(SCRIPT.relative_to(ROOT))),
    ):
        info.addProperty("App::PropertyString", prop)
        setattr(info, prop, value)
    add_spreadsheet(doc)
    root_group = doc.addObject("App::DocumentObjectGroup", "ProductionAircraft")
    groups = {}
    objects = []
    for spec, shape in zip(parts, gallery_shapes):
        if spec.aircraft_code not in groups:
            groups[spec.aircraft_code] = doc.addObject("App::DocumentObjectGroup", spec.aircraft_code)
            root_group.addObject(groups[spec.aircraft_code])
        objects.append(add_part(doc, groups[spec.aircraft_code], spec, shape))
    doc.recompute()
    return doc, objects


def shape_record(spec, printed):
    bounds = precise_bounds(spec.shape)
    pb = precise_bounds(printed)
    messages = []
    try:
        spec.shape.check(True)
    except ValueError as exc:
        messages = [line.strip() for line in str(exc).splitlines() if line.strip()]
    return {
        "name": spec.name, "role": spec.role, "aircraft_code": spec.aircraft_code,
        "variant": spec.variant, "material": MATERIALS[spec.material][0],
        "evidence": spec.evidence, "classification": spec.classification,
        "valid_brep": spec.shape.isValid(), "closed_solids": all(s.isClosed() for s in spec.shape.Solids),
        "solid_count": len(spec.shape.Solids), "volume_mm3": round(float(spec.shape.Volume), 6),
        "strict_messages": messages, "assembly_bounds_mm": [round(x, 5) for x in bounds],
        "print_bounds_mm": [round(x, 5) for x in pb],
        "print_size_mm": [round(pb[3]-pb[0], 5), round(pb[4]-pb[1], 5), round(pb[5]-pb[2], 5)],
        "minimum_feature_mm": spec.minimum_feature_mm, "print_note": spec.print_note,
    }


def approved_hashes():
    return {str(path.relative_to(ROOT)): {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in APPROVED_PATHS}


def clean_outputs():
    for directory, pattern in ((DIRS["stl"], "*.stl"), (DIRS["step"], "*.step"), (DIRS["3mf"], "*.3mf"), (DIRS["obj"], "CVN69_AirWing_Master.*")):
        for path in directory.glob(pattern):
            path.unlink()


def main():
    print("Building CVN-69 Milestone 5 air-wing production masters")
    clean_outputs()
    parts = build_parts()
    packed_specs, gallery_shapes = pack_plate(parts, max_size=P.preferred_print_envelope, gap=2.5)
    doc, objects = create_document(parts, gallery_shapes)
    fcstd = DIRS["freecad"] / "CVN69_AirWing_Master.FCStd"
    doc.saveAs(str(fcstd))
    master_step = DIRS["step"] / "CVN69_AirWing_Master.step"
    export_step(master_step, packed_specs, gallery_shapes)
    master_3mf = DIRS["3mf"] / "CVN69_AirWing_Master.3mf"
    write_3mf(master_3mf, packed_specs, "CVN-69 Milestone 5 Air Wing Master", gallery_shapes)
    obj_path = DIRS["obj"] / "CVN69_AirWing_Master.obj"
    gallery_specs = [PartSpec(spec.name, shape, spec.material, spec.role, spec.aircraft_code, spec.variant, spec.evidence, spec.classification, spec.minimum_feature_mm) for spec, shape in zip(packed_specs, gallery_shapes)]
    write_obj(obj_path, gallery_specs)

    stl_paths = []
    print_versions = {}
    facets = {}
    for spec in parts:
        printed = print_shape(spec)
        print_versions[spec.name] = printed
        path = DIRS["stl"] / f"{spec.name}.stl"
        facets[path.name] = write_binary_stl(path, spec, printed)
        stl_paths.append(path)

    plate_paths = []
    step_paths = []
    for item in P.aircraft_types:
        group = family_parts(parts, item.code)
        plate_specs, plate_shapes = pack_plate(group, max_size=225.0, gap=3.0)
        plate_shapes = plate_margin(plate_shapes, 10.0)
        plate = DIRS["3mf"] / f"Print_Plate_{item.code}.3mf"
        write_3mf(plate, plate_specs, f"CVN-69 Air Wing — {item.code}", plate_shapes)
        plate_paths.append(plate)
        step = DIRS["step"] / f"{item.code}_Master.step"
        export_step(step, plate_specs, plate_shapes)
        step_paths.append(step)

    first_names = {
        "FA18E_VFA105_Folded_Body", "FA18F_VFA32_Launch_Body", "EA18G_VAQ130_Folded_Body",
        "E2C_VAW123_Folded_Body", "C2A_VRC40_Folded_Body", "MH60R_HSM74_Folded_Body",
        "MH60S_HSC7_Deployed_Body", "E2C_VAW123_Rotodome",
        "MH60R_HSM74_Folded_Main_Rotor", "MH60S_HSC7_Deployed_Main_Rotor",
        "FA18E_VFA105_Canopy_Insert", "E2C_VAW123_Canopy_Insert",
    }
    first = [spec for spec in parts if spec.name in first_names]
    first_specs, first_shapes = pack_plate(first, max_size=P.first_article_envelope - 10.0, gap=2.5)
    first_shapes = plate_margin(first_shapes, 5.0)
    first_plate = DIRS["3mf"] / "Print_Plate_00_First_Article.3mf"
    write_3mf(first_plate, first_specs, "CVN-69 Air Wing First Article", first_shapes)
    plate_paths.append(first_plate)

    approved = approved_hashes()
    inspection = {
        "generated_utc": datetime.now(timezone.utc).isoformat(), "freecad_version": ".".join(App.Version()[:3]),
        "coordinate_system": "x=0 bow to x=476 stern; y port negative; z deck top 34.5 mm",
        "deck_top_z_mm": P.deck_top_z, "frozen_interface_clearance_per_side_mm": P.integration.interface_clearance_per_side,
        "approved_inputs": approved, "policy": "approved inputs hashed/read-only; production builder opens no source mesh",
    }
    inspection_path = DIRS["qa"] / "Approved_Input_Inspection.json"
    inspection_path.write_text(json.dumps(inspection, indent=2) + "\n", encoding="utf-8")

    outputs = [fcstd, master_step, master_3mf, obj_path, obj_path.with_suffix(".mtl"), *stl_paths, *plate_paths, *step_paths, inspection_path]
    manifest = {
        "project": "USS Dwight D. Eisenhower (CVN-69) 1:700 Museum Edition",
        "milestone": P.milestone, "version": P.version, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "freecad_version": ".".join(App.Version()[:3]), "configuration_period": P.configuration_period,
        "source_geometry_policy": "new parametric BReps; no mesh opened or reused",
        "parameters_mm": {
            "ship_length": P.overall_length, "deck_top_z": P.deck_top_z,
            "frozen_ship_interface_clearance_per_side": P.integration.interface_clearance_per_side,
            "aircraft_clearance_per_side": P.assembly_clearance_per_side, "wing": P.wing_thickness,
            "stabilizer": P.stabilizer_thickness, "gear": P.minimum_gear,
            "rotor_blade_width": P.rotor_blade_width, "rotor_blade_thickness": P.rotor_blade_thickness,
            "fin": P.fin_thickness, "insert": P.insert_thickness, "marking": [P.marking_width, P.marking_height],
        },
        "counts": {"aircraft_types": len(P.aircraft_types), "body_variants": sum(p.role == "aircraft_body" for p in parts), "production_objects": len(parts)},
        "aircraft_types": [item.__dict__ for item in P.aircraft_types],
        "parts": [shape_record(spec, print_versions[spec.name]) for spec in parts],
        "stl_facets": facets, "approved_input_hashes": approved,
        "outputs": {str(path.relative_to(M5)): {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in outputs},
    }
    manifest_path = DIRS["qa"] / "build_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    App.closeDocument(doc.Name)
    print(json.dumps({"status": "ok", "production_objects": len(parts), "body_variants": 25, "first_article_objects": len(first)}, indent=2))


if __name__ == "__main__":
    main()
