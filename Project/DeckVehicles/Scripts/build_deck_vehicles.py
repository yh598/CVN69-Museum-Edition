#!/usr/bin/env python3
"""Build Milestone 6 deck vehicles as new parametric OpenCascade solids.

The builder never imports STL/3MF/source triangles. Approved ship modules are
read only for datums and are used by the separate layout/review builder.
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
M6 = PROJECT / "DeckVehicles"
sys.path.insert(0, str(M6 / "CAD" / "Python"))
from deck_vehicle_parameters import make_parameters  # noqa: E402


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = make_parameters()
BASE = load_module("m6_freecad_utilities", PROJECT / "WeaponsDeckEdge" / "Scripts" / "build_weapons_deckedge.py")
BASE.P = P
BASE.UTIL.P = P

DIRS = {name: M6 / folder for name, folder in {
    "freecad": "CAD/FreeCAD", "step": "STEP", "stl": "STL", "3mf": "3MF",
    "obj": "OBJ", "render": "Render", "images": "Images", "layout": "Layout",
    "assembly": "Assembly", "docs": "Docs", "qa": "QA", "references": "References",
}.items()}
for directory in DIRS.values():
    directory.mkdir(parents=True, exist_ok=True)

MATERIALS = OrderedDict((
    ("gold", ("Bambu PLA Basic Gold", "#D6A936FF")),
    ("black", ("Bambu PLA Basic Black", "#151719FF")),
    ("charcoal", ("Bambu PLA Matte Charcoal", "#34383CFF")),
    ("red", ("Bambu PLA Translucent Red", "#B83935FF")),
    ("ash_gray", ("Bambu PLA Matte Ash Gray", "#969890FF")),
    ("silver", ("Bambu PLA Silk Silver", "#AEB4B8FF")),
    ("ivory", ("Bambu PLA Matte Ivory White", "#ECE8D9FF")),
    ("marine_blue", ("Bambu PLA Matte Marine Blue", "#315B73FF")),
))
BASE.MATERIALS = MATERIALS
BASE.UTIL.MATERIALS = MATERIALS

APPROVED_PATHS = (
    PROJECT / "Integration" / "CAD" / "FreeCAD" / "CVN69_Hull_Deck_Integration.FCStd",
    PROJECT / "Integration" / "CAD" / "Python" / "integration_parameters.py",
    PROJECT / "Integration" / "QA" / "Production_Interface_Freeze.json",
    PROJECT / "Island" / "CAD" / "FreeCAD" / "CVN69_Island.FCStd",
    PROJECT / "Island" / "CAD" / "Python" / "island_parameters.py",
    PROJECT / "WeaponsDeckEdge" / "CAD" / "FreeCAD" / "CVN69_Weapons_DeckEdge.FCStd",
    PROJECT / "WeaponsDeckEdge" / "CAD" / "Python" / "weapons_deckedge_parameters.py",
    PROJECT / "AirWing" / "CAD" / "FreeCAD" / "CVN69_AirWing_Master.FCStd",
    PROJECT / "AirWing" / "CAD" / "Python" / "airwing_parameters.py",
    PROJECT / "AirWing" / "Layout" / "light_deck_layout.json",
    PROJECT / "AirWing" / "Layout" / "default_deployment_layout.json",
    PROJECT / "AirWing" / "Layout" / "full_deck_layout.json",
)


@dataclass
class PartSpec:
    name: str
    shape: object
    material: str
    role: str
    family: str
    evidence: str
    classification: str
    minimum_feature_mm: float
    assembly_offset: tuple = (0.0, 0.0, 0.0)
    print_rotation: object = None
    print_override: object = None
    print_note: str = "Engineered bed face at z=0; support-free"
    allow_multiple: bool = False
    production: bool = True


v = BASE.v
fuse_all = BASE.fuse_all
polygon_prism = BASE.polygon_prism
bar_between = BASE.bar_between
precise_bounds = BASE.precise_bounds
validate_shape = BASE.validate_shape
pack_plate = BASE.pack_plate
print_shape = BASE.print_shape
write_binary_stl = BASE.write_binary_stl
write_3mf = BASE.write_3mf
write_obj = BASE.write_obj


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(shape):
    result = shape.removeSplitter()
    if result.isNull() or not result.isValid() or len(result.Solids) != 1 or not result.Solids[0].isClosed():
        raise RuntimeError("invalid or disconnected generated solid")
    return result


def box(length, width, height, x=0.0, y=0.0, z=0.0):
    return Part.makeBox(length, width, height, v(x - length / 2.0, y - width / 2.0, z))


def bar_xy(start, end, thickness, z=0.0, height=None):
    height = thickness if height is None else height
    x0, y0 = start
    x1, y1 = end
    length = math.hypot(x1 - x0, y1 - y0)
    shape = Part.makeBox(length, thickness, height, v(0, -thickness / 2.0, z))
    shape.rotate(v(0, 0, 0), v(0, 0, 1), math.degrees(math.atan2(y1 - y0, x1 - x0)))
    shape.translate(v(x0, y0, 0))
    return shape


def wheel_insert(length, width, wheelbase, diameter=1.10, wheel_width=0.70):
    radius = diameter / 2.0
    pieces = [box(wheelbase + diameter, P.minimum_axle, 0.38, z=0.0)]
    for x_value in (-wheelbase / 2.0, wheelbase / 2.0):
        pieces.append(box(P.minimum_axle, width, 0.38, x=x_value, z=0.0))
        pieces.append(Part.makeCylinder(radius, wheel_width, v(x_value, -width / 2.0, radius), v(0, 1, 0)))
        pieces.append(Part.makeCylinder(radius, wheel_width, v(x_value, width / 2.0 - wheel_width, radius), v(0, 1, 0)))
    return clean(fuse_all(pieces))


def tractor_parts():
    f = P.family("STT49")
    length, width = f.model_length, f.model_width
    lower = box(length, width - 1.60, 0.62, z=0.38)
    hood = box(2.10, width - 1.54, 0.50, x=1.15, z=0.86)
    cabin = box(1.75, width - 1.62, 0.76, x=-1.15, z=0.82)
    ballast = box(0.70, width - 1.42, 0.55, x=2.12, z=0.70)
    body = clean(fuse_all((lower, hood, cabin, ballast)))
    wheels = wheel_insert(length, width, 3.15, 1.10, 0.70)
    window = clean(box(1.25, 1.55, P.minimum_insert, x=-1.10, z=1.58))
    return (
        PartSpec("Tow_Tractor_STT49_Body_Gold", body, "gold", "body", "STT49", f.evidence_url, f.classification, 0.80),
        PartSpec("Tow_Tractor_STT49_Wheel_Insert_Black", wheels, "black", "wheel_insert", "STT49", f.evidence_url, f.classification, 0.70),
        PartSpec("Tow_Tractor_STT49_Window_Insert_Charcoal", window, "charcoal", "window_insert", "STT49", f.evidence_url, f.classification, 0.60),
    )


def p25_parts():
    f = P.family("P25A")
    length, width = f.model_length, f.model_width
    lower = box(length, width - 1.55, 0.60, z=0.38)
    tank = box(4.35, width - 1.55, 1.50, x=-0.35, z=0.82)
    cab = polygon_prism(((1.82, -0.85), (3.20, -0.85), (3.45, -0.48), (3.45, 0.48), (3.20, 0.85), (1.82, 0.85)), 0.82, 1.28)
    body = clean(fuse_all((lower, tank, cab)))
    wheels = wheel_insert(length, width, 4.65, 1.10, 0.70)
    turret_base = Part.makeCylinder(0.52, 0.58, v(0, 0, 0))
    nozzle = bar_xy((0.0, 0.0), (1.65, 0.0), 0.80, z=0.0, height=0.58)
    turret = clean(fuse_all((turret_base, nozzle)))
    return (
        PartSpec("P25A_Firefighting_Vehicle_Body_Gold", body, "gold", "body", "P25A", f.evidence_url, f.classification, 0.80),
        PartSpec("P25A_Firefighting_Vehicle_Wheels_Black", wheels, "black", "wheel_insert", "P25A", f.evidence_url, f.classification, 0.70),
        PartSpec("P25A_Turret_Nozzle_Silver", turret, "silver", "turret", "P25A", f.evidence_url, f.classification, 0.80, assembly_offset=(-0.60, 0.0, 2.28)),
    )


def msu_parts():
    f = P.family("MSU200")
    length, width = f.model_length, f.model_width
    chassis = box(length, width - 1.65, 0.52, z=0.38)
    module = box(2.80, width - 1.68, 1.16, x=-0.15, z=0.76)
    grille = box(0.60, width - 1.52, 0.82, x=1.42, z=0.84)
    body = clean(fuse_all((chassis, module, grille)))
    wheels = wheel_insert(length, width, 2.40, 1.00, 0.70)
    reel = Part.makeCylinder(0.68, 0.60, v(0, 0, 0))
    hub = Part.makeCylinder(0.30, 0.72, v(0, 0, 0))
    hose = clean(fuse_all((reel, hub)))
    return (
        PartSpec("MSU200_Air_Start_Cart_Body_AshGray", body, "ash_gray", "body", "MSU200", f.evidence_url, f.classification, 0.80),
        PartSpec("MSU200_Air_Start_Cart_Wheels_Black", wheels, "black", "wheel_insert", "MSU200", f.evidence_url, f.classification, 0.70),
        PartSpec("MSU200_Hose_Reel_Silver", hose, "silver", "hose_reel", "MSU200", f.evidence_url, f.classification, 0.60, assembly_offset=(-0.25, -0.58, 1.15), print_note="Reel face down at z=0; glue to cart side"),
    )


def tow_bar_shape(offset_y=0.0):
    arms = (
        bar_xy((-2.25, offset_y), (1.15, offset_y - 0.70), 0.80),
        bar_xy((-2.25, offset_y), (1.15, offset_y + 0.70), 0.80),
        box(1.15, 2.20, 0.80, x=1.55, y=offset_y),
        box(0.90, 0.90, 0.80, x=-2.15, y=offset_y),
    )
    return clean(fuse_all(arms))


def towbar_parts():
    f = P.family("TOWBAR")
    single = tow_bar_shape()
    sprue_parts = [tow_bar_shape(offset) for offset in (-3.0, 0.0, 3.0)]
    sprue_parts += [box(0.80, 7.60, 0.80, x=-2.65), box(1.0, 0.80, 0.80, x=-2.35, y=-3.0), box(1.0, 0.80, 0.80, x=-2.35, y=3.0)]
    sprue = clean(fuse_all(sprue_parts))
    return (
        PartSpec("Aircraft_Tow_Bar_Type01_Gold", single, "gold", "tow_bar", "TOWBAR", f.evidence_url, f.classification, 0.80),
        PartSpec("Aircraft_Tow_Bar_Type01_Family_Sprue_Gold", sprue, "gold", "family_sprue", "TOWBAR", f.evidence_url, f.classification, 0.80, print_note="0.80 mm family-only removable sprue; gates on non-visible tow eyes"),
    )


def ladder_parts():
    f = P.family("LADDER")
    pieces = [box(0.60, 0.60, 3.60, x=-1.50), box(0.60, 0.60, 3.60, x=1.50)]
    for z_value in (0.25, 1.05, 1.85, 2.65, 3.25):
        pieces.append(box(3.60, 0.60, 0.60, z=z_value))
    ladder = clean(fuse_all(pieces))
    rotation = App.Rotation(v(1, 0, 0), 90)
    return (PartSpec("Maintenance_Ladder_Type01_Gold", ladder, "gold", "maintenance_ladder", "LADDER", f.evidence_url, f.classification, 0.60, print_rotation=rotation, print_note="Ladder prints flat on back; no bridges or supports"),)


def chock_shape(offset_y=0.0):
    wedge = polygon_prism(((-0.60, -0.55), (0.60, -0.55), (0.60, 0.55), (-0.60, 0.55)), 0.0, 0.70)
    left = wedge.copy(); left.translate(v(-0.95, offset_y, 0))
    right = wedge.copy(); right.translate(v(0.95, offset_y, 0))
    connector = box(2.10, 0.80, 0.55, y=offset_y)
    return clean(fuse_all((left, right, connector)))


def chock_parts():
    f = P.family("CHOCK")
    group = chock_shape()
    sprue_pieces = [chock_shape(offset) for offset in (-2.30, 0.0, 2.30)]
    sprue_pieces.append(box(0.80, 5.40, 0.80, x=-1.65))
    sprue = clean(fuse_all(sprue_pieces))
    return (
        PartSpec("Wheel_Chock_Group_Type01_Gold", group, "gold", "wheel_chock", "CHOCK", f.evidence_url, f.classification, 0.80),
        PartSpec("Wheel_Chock_Group_Type01_Family_Sprue_Gold", sprue, "gold", "family_sprue", "CHOCK", f.evidence_url, f.classification, 0.80),
    )


def extinguisher_parts():
    f = P.family("EXT")
    base = box(2.60, 0.80, 0.55, z=0.38)
    bottle1 = Part.makeCylinder(0.45, 1.45, v(-0.60, 0, 0.75))
    bottle2 = Part.makeCylinder(0.45, 1.45, v(0.60, 0, 0.75))
    rail = box(0.70, 0.80, 1.82, x=0.0, z=0.38)
    handle = bar_between((-0.95, 0.0, 1.85), (0.95, 0.0, 1.85), 0.70)
    bottles = clean(fuse_all((base, bottle1, bottle2, rail, handle)))
    wheels = wheel_insert(2.70, 2.30, 1.50, 1.00, 0.70)
    return (
        PartSpec("Firefighting_Extinguisher_Group_Type01_Red", bottles, "red", "extinguisher_group", "EXT", f.evidence_url, f.classification, 0.70),
        PartSpec("Firefighting_Extinguisher_Group_Wheels_Black", wheels, "black", "wheel_insert", "EXT", f.evidence_url, f.classification, 0.70),
    )


def coupon_parts():
    male = clean(fuse_all((box(3.60, 3.60, 0.80), box(1.00, 1.00, 0.60, z=0.80))))
    female = box(3.60, 3.60, 1.40)
    socket = box(1.40, 1.40, 0.64, z=0.80)
    female = clean(female.cut(socket))
    return (
        PartSpec("Vehicle_Alignment_Coupon_Male_Gold", male, "gold", "alignment_coupon", "COUPON", "engineering first-article interface", "new parametric glue-only test interface; 0.20 mm per side", 0.80, production=False),
        PartSpec("Vehicle_Alignment_Coupon_Female_Black", female, "black", "alignment_coupon", "COUPON", "engineering first-article interface", "new parametric glue-only test interface; 0.20 mm per side", 0.80, production=False),
    )


def build_parts(include_coupons=False):
    parts = [*tractor_parts(), *p25_parts(), *msu_parts(), *towbar_parts(), *ladder_parts(), *chock_parts(), *extinguisher_parts()]
    if include_coupons:
        parts.extend(coupon_parts())
    for spec in parts:
        validate_shape(spec.name, spec.shape, spec.allow_multiple)
        validate_shape(spec.name + "_Print", print_shape(spec), spec.allow_multiple)
    return parts


def family_parts(parts, code):
    return [spec for spec in parts if spec.family == code]


def assembled_parts(parts, code):
    result = []
    for spec in family_parts(parts, code):
        if spec.role == "family_sprue":
            continue
        shape = spec.shape.copy()
        shape.translate(v(*spec.assembly_offset))
        result.append((spec, shape))
    return result


def assembly_shape(parts, code):
    return Part.makeCompound([shape for _spec, shape in assembled_parts(parts, code)])


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
    sheet = doc.addObject("Spreadsheet::Sheet", "DeckVehicleParameters")
    rows = [
        ("Parameter", "Value", "Unit / provenance"),
        ("Scale", "1:700", "fixed"),
        ("Ship length", P.overall_length, "mm approved baseline"),
        ("Deck top", P.deck_top_z, "mm approved baseline"),
        ("Frozen interface", P.integration.interface_clearance_per_side, "mm/side immutable"),
        ("Vehicle glue clearance", P.small_part_clearance_per_side, "mm/side"),
        ("Minimum wall", P.minimum_structural_wall, "mm"),
        ("Wheel", f"{P.minimum_wheel_diameter} dia × {P.minimum_wheel_width} width", "mm minimum"),
        ("Tow bar", P.minimum_tow_bar, "mm minimum"),
        ("Ladder", P.minimum_ladder, "mm minimum"),
        ("Configuration", P.configuration_period, "public-reference freeze"),
        ("Confirmed families", len(P.families), "audit-supported only"),
    ]
    for r, row in enumerate(rows, 1):
        for c, value in enumerate(row, 1):
            sheet.set(f"{chr(64+c)}{r}", str(value))
    sheet.setStyle("A1:C1", "bold", "add")
    sheet.setColumnWidth("A", 220); sheet.setColumnWidth("B", 300); sheet.setColumnWidth("C", 330)


def create_document(parts):
    doc = App.newDocument("CVN69_Deck_Vehicles_Master")
    info = doc.addObject("App::FeaturePython", "MilestoneInformation")
    values = (
        ("ProjectName", "USS Dwight D. Eisenhower (CVN-69) 1:700 Museum Edition"),
        ("Milestone", P.milestone), ("Version", P.version),
        ("ConfigurationPeriod", P.configuration_period),
        ("GeometryStatus", "New parametric OpenCascade BReps; no mesh triangle imported"),
        ("ScopeBoundary", "Deck vehicles/support equipment only; M1-M5 immutable"),
        ("Generator", str(SCRIPT.relative_to(ROOT))),
    )
    for prop, value in values:
        info.addProperty("App::PropertyString", prop); setattr(info, prop, value)
    add_spreadsheet(doc)
    root = doc.addObject("App::DocumentObjectGroup", "ReusableEquipmentFamilies")
    colors = {"gold": (0.84, 0.66, 0.21), "black": (0.08, 0.09, 0.10), "charcoal": (0.20, 0.22, 0.24), "red": (0.72, 0.22, 0.20), "ash_gray": (0.59, 0.60, 0.56), "silver": (0.68, 0.71, 0.73), "ivory": (0.92, 0.90, 0.84), "marine_blue": (0.19, 0.36, 0.45)}
    x_cursor = 0.0
    for family in [item.code for item in P.families]:
        group = doc.addObject("App::DocumentObjectGroup", family); root.addObject(group)
        assembled = assembled_parts(parts, family)
        bounds = precise_bounds(Part.makeCompound([shape for _spec, shape in assembled]))
        for spec, shape in assembled:
            displayed = shape.copy(); displayed.translate(v(x_cursor - bounds[0], -bounds[1], 0))
            obj = doc.addObject("Part::Feature", spec.name); obj.Shape = displayed
            for prop, value in (("EquipmentFamily", family), ("Role", spec.role), ("Material", MATERIALS[spec.material][0]), ("EvidenceBasis", spec.evidence), ("AccuracyClassification", spec.classification), ("PrintOrientation", spec.print_note)):
                obj.addProperty("App::PropertyString", prop); setattr(obj, prop, value)
            obj.addProperty("App::PropertyLength", "MinimumDesignedFeature").MinimumDesignedFeature = spec.minimum_feature_mm
            try: obj.ViewObject.ShapeColor = colors[spec.material]
            except Exception: pass
            group.addObject(obj)
        x_cursor += bounds[3] - bounds[0] + 5.0
    sprue_group = doc.addObject("App::DocumentObjectGroup", "FamilySprues"); root.addObject(sprue_group)
    for spec in parts:
        if spec.role != "family_sprue": continue
        obj = doc.addObject("Part::Feature", spec.name); obj.Shape = print_shape(spec); sprue_group.addObject(obj)
    doc.recompute()
    return doc


def shape_record(spec):
    assembly = precise_bounds(spec.shape)
    printed = print_shape(spec)
    bounds = precise_bounds(printed)
    strict = []
    try: spec.shape.check(True)
    except ValueError as exc: strict = [line.strip() for line in str(exc).splitlines() if line.strip()]
    return {
        "name": spec.name, "family": spec.family, "role": spec.role,
        "material": MATERIALS[spec.material][0], "evidence": spec.evidence,
        "classification": spec.classification, "minimum_feature_mm": spec.minimum_feature_mm,
        "assembly_offset_mm": list(spec.assembly_offset), "print_note": spec.print_note,
        "valid_brep": spec.shape.isValid(), "solid_count": len(spec.shape.Solids),
        "closed": all(s.isClosed() for s in spec.shape.Solids), "strict_messages": strict,
        "volume_mm3": round(float(spec.shape.Volume), 6),
        "assembly_bounds_mm": [round(x, 5) for x in assembly],
        "print_bounds_mm": [round(x, 5) for x in bounds],
        "print_size_mm": [round(bounds[3]-bounds[0], 5), round(bounds[4]-bounds[1], 5), round(bounds[5]-bounds[2], 5)],
    }


def approved_hashes():
    missing = [path for path in APPROVED_PATHS if not path.exists()]
    if missing: raise FileNotFoundError(missing)
    return {str(path.relative_to(ROOT)): {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in APPROVED_PATHS}


def clean_outputs():
    for directory, patterns in ((DIRS["stl"], ("*.stl",)), (DIRS["step"], ("CVN69_Deck_Vehicles_Master.step",)), (DIRS["3mf"], ("CVN69_Deck_Vehicles_Master.3mf", "Print_Plate_*.3mf")), (DIRS["obj"], ("CVN69_Deck_Vehicles_Master.*",))):
        for pattern in patterns:
            for path in directory.glob(pattern): path.unlink()


def plate_with_margin(specs, max_size=225.0, gap=3.0, margin=5.0):
    packed, shapes = pack_plate(specs, max_size=max_size - 2 * margin, gap=gap)
    for shape in shapes: shape.translate(v(margin, margin, 0))
    return packed, shapes


def main():
    print("Building CVN-69 Milestone 6 parametric deck vehicles")
    clean_outputs()
    parts = build_parts(False)
    all_for_first = build_parts(True)
    production = [spec for spec in parts if spec.production]
    approved = approved_hashes()

    doc = create_document(parts)
    fcstd = DIRS["freecad"] / "CVN69_Deck_Vehicles_Master.FCStd"; doc.saveAs(str(fcstd))
    packed, gallery = plate_with_margin(production, max_size=230.0, gap=3.0, margin=5.0)
    master_step = DIRS["step"] / "CVN69_Deck_Vehicles_Master.step"; export_step(master_step, packed, gallery)
    master_3mf = DIRS["3mf"] / "CVN69_Deck_Vehicles_Master.3mf"; write_3mf(master_3mf, packed, "CVN-69 Milestone 6 Deck Vehicles Master", gallery)
    master_obj = DIRS["obj"] / "CVN69_Deck_Vehicles_Master.obj"
    gallery_specs = [PartSpec(spec.name, shape, spec.material, spec.role, spec.family, spec.evidence, spec.classification, spec.minimum_feature_mm) for spec, shape in zip(packed, gallery)]
    write_obj(master_obj, gallery_specs)

    stls = []
    for spec in production:
        path = DIRS["stl"] / f"{spec.name}.stl"
        write_binary_stl(path, spec, print_shape(spec)); stls.append(path)

    plate_groups = OrderedDict((
        ("Print_Plate_01_Tow_Tractors.3mf", [spec for spec in production if spec.family == "STT49"]),
        ("Print_Plate_02_Service_Carts.3mf", [spec for spec in production if spec.family == "MSU200"]),
        ("Print_Plate_03_Firefighting_Equipment.3mf", [spec for spec in production if spec.family in {"P25A", "EXT"}]),
        ("Print_Plate_04_Tow_Bars_Chocks.3mf", [spec for spec in production if spec.family in {"TOWBAR", "CHOCK"}]),
        ("Print_Plate_05_Ladders_Maintenance.3mf", [spec for spec in production if spec.family == "LADDER"]),
        ("Print_Plate_06_Wheels_Inserts_Details.3mf", [spec for spec in production if spec.role in {"wheel_insert", "window_insert", "turret", "hose_reel"}]),
    ))
    plates = []
    for filename, specs in plate_groups.items():
        if not specs: continue
        ps, shapes = plate_with_margin(specs, max_size=225.0, gap=3.0, margin=5.0)
        path = DIRS["3mf"] / filename; write_3mf(path, ps, filename.removesuffix(".3mf").replace("_", " "), shapes); plates.append(path)

    first_names = {
        "Tow_Tractor_STT49_Body_Gold", "Tow_Tractor_STT49_Wheel_Insert_Black", "Tow_Tractor_STT49_Window_Insert_Charcoal",
        "MSU200_Air_Start_Cart_Body_AshGray", "Aircraft_Tow_Bar_Type01_Gold", "Maintenance_Ladder_Type01_Gold",
        "Wheel_Chock_Group_Type01_Gold", "Firefighting_Extinguisher_Group_Type01_Red", "Aircraft_Tow_Bar_Type01_Family_Sprue_Gold",
        "Vehicle_Alignment_Coupon_Male_Gold", "Vehicle_Alignment_Coupon_Female_Black",
    }
    first = [spec for spec in all_for_first if spec.name in first_names]
    fs, fshapes = plate_with_margin(first, max_size=P.first_article_envelope, gap=3.0, margin=5.0)
    first_plate = DIRS["3mf"] / "Print_Plate_00_First_Article.3mf"; write_3mf(first_plate, fs, "CVN-69 Deck Vehicles First Article", fshapes); plates.append(first_plate)

    inspection = {
        "generated_utc": datetime.now(timezone.utc).isoformat(), "freecad_version": ".".join(App.Version()[:3]),
        "coordinate_system": "x=0 bow to x=476 stern; y port negative; z approved hull datum",
        "deck_top_z_mm": P.deck_top_z, "frozen_interface_clearance_per_side_mm": P.integration.interface_clearance_per_side,
        "approved_inputs": approved, "policy": "approved inputs hashed/read-only; builder opens no source mesh",
    }
    inspection_path = DIRS["qa"] / "Approved_Input_Inspection.json"; inspection_path.write_text(json.dumps(inspection, indent=2) + "\n", encoding="utf-8")
    enlargements = [{"family": item.code, "classification": item.classification, "records": list(item.enlargements)} for item in P.families]
    enlargement_path = DIRS["qa"] / "FDM_Enlargements.json"; enlargement_path.write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).isoformat(), "records": enlargements}, indent=2) + "\n", encoding="utf-8")
    dimensions_path = DIRS["qa"] / "External_Dimensions.json"
    dimensions_path.write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).isoformat(), "families": [item.__dict__ for item in P.families]}, indent=2) + "\n", encoding="utf-8")

    outputs = [fcstd, master_step, master_3mf, master_obj, master_obj.with_suffix(".mtl"), *stls, *plates, inspection_path, enlargement_path, dimensions_path]
    manifest = {
        "project": "USS Dwight D. Eisenhower (CVN-69) 1:700 Museum Edition", "milestone": P.milestone,
        "version": P.version, "generated_utc": datetime.now(timezone.utc).isoformat(), "freecad_version": ".".join(App.Version()[:3]),
        "configuration_period": P.configuration_period, "source_geometry_policy": "new parametric BReps; no mesh opened or reused",
        "parameters_mm": {"ship_length": P.overall_length, "deck_top_z": P.deck_top_z, "frozen_ship_interface_clearance_per_side": P.integration.interface_clearance_per_side, "vehicle_clearance_per_side": P.small_part_clearance_per_side, "minimum_wall": P.minimum_structural_wall, "wheel": [P.minimum_wheel_diameter, P.minimum_wheel_width], "tow_bar": P.minimum_tow_bar, "ladder": P.minimum_ladder, "hose": P.minimum_hose},
        "counts": {"equipment_families": len(P.families), "production_objects": len(production)},
        "families": [item.__dict__ for item in P.families], "parts": [shape_record(spec) for spec in production],
        "approved_input_hashes": approved,
        "outputs": {str(path.relative_to(M6)): {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in outputs},
    }
    manifest_path = DIRS["qa"] / "build_manifest.json"; manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    App.closeDocument(doc.Name)
    print(json.dumps({"status": "ok", "families": len(P.families), "production_objects": len(production), "first_article_objects": len(first), "plates": len(plates)}, indent=2))


if __name__ == "__main__":
    main()
