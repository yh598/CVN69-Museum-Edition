#!/usr/bin/env python3
"""Build configurable M6 support layouts against approved ship/AirWing BReps."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
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
from deck_equipment_layout_parameters import make_parameters as make_layout_parameters  # noqa: E402


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


B = load_module("m6_build_for_layout", M6 / "Scripts" / "build_deck_vehicles.py")
AW = load_module("m6_approved_airwing_layout", PROJECT / "AirWing" / "Scripts" / "build_airwing_layout.py")
P = B.P
LP = make_layout_parameters()


@dataclass
class ReviewSpec:
    name: str
    shape: object
    material: str
    role: str
    family: str
    evidence: str
    classification: str
    minimum_feature_mm: float = 0.60
    print_rotation: object = None
    print_override: object = None
    print_note: str = "non-production integrated review object"
    allow_multiple: bool = False


def point_in_polygon(x, y, polygon):
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1.0e-12) + xi:
            inside = not inside
        j = i
    return inside


def deck_outline():
    return tuple((P.overall_length - x, y) for x, y in P.integration.deck.outline_points)


def transform(shape, x, y, z, heading):
    result = shape.copy()
    if abs(heading) > 1.0e-9:
        result.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), heading)
    result.translate(App.Vector(x, y, z))
    return result


def family_shape(parts, code):
    return B.assembly_shape(parts, code)


def placed_family_parts(parts, entry):
    result = []
    for spec, local in B.assembled_parts(parts, entry["equipment_family"]):
        shape = transform(local, entry["x"], entry["y"], entry["z"], entry["heading"])
        result.append(ReviewSpec(
            f"{entry['instance_id']}_{spec.name}", shape, spec.material, spec.role,
            spec.family, spec.evidence, spec.classification, spec.minimum_feature_mm,
        ))
    return result


def combined_shape(parts):
    return Part.makeCompound([part.shape for part in parts])


def bbox_inside(shape, outline):
    b = shape.BoundBox; m = LP.deck_edge_margin
    corners = ((b.XMin-m, b.YMin-m), (b.XMin-m, b.YMax+m), (b.XMax+m, b.YMin-m), (b.XMax+m, b.YMax+m))
    return all(point_in_polygon(x, y, outline) for x, y in corners)


def bbox_gap(left, right):
    a, b = left.BoundBox, right.BoundBox
    dx = max(0.0, max(a.XMin, b.XMin) - min(a.XMax, b.XMax))
    dy = max(0.0, max(a.YMin, b.YMin) - min(a.YMax, b.YMax))
    dz = max(0.0, max(a.ZMin, b.ZMin) - min(a.ZMax, b.ZMax))
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def exact_overlap(shape, targets):
    hits = []
    for target in targets:
        other = target.shape if hasattr(target, "shape") else target
        a, b = shape.BoundBox, other.BoundBox
        if a.XMax <= b.XMin or b.XMax <= a.XMin or a.YMax <= b.YMin or b.YMax <= a.YMin or a.ZMax <= b.ZMin or b.ZMax <= a.ZMin:
            continue
        common = shape.common(other)
        volume = 0.0 if common.isNull() else float(common.Volume)
        if volume > LP.interference_threshold_mm3:
            hits.append((getattr(target, "name", "target"), volume))
    return hits


def aircraft_for_layout(name):
    filename = {"light": "light_deck_layout.json", "default": "default_deployment_layout.json", "full": "full_deck_layout.json"}[name]
    payload = json.loads((PROJECT / "AirWing" / "Layout" / filename).read_text(encoding="utf-8"))
    production = AW.B.build_parts()
    records = []
    for entry in payload["entries"]:
        parts = AW.placed_aircraft(entry, production)
        records.append({"entry": entry, "parts": parts, "shape": AW.combined_shape(parts)})
    return records


def family_roster(name):
    counts = {
        "light": {"STT49": 3, "P25A": 2, "MSU200": 2, "TOWBAR": 2, "LADDER": 2, "CHOCK": 2, "EXT": 1},
        "default": {"STT49": 5, "P25A": 2, "MSU200": 4, "TOWBAR": 4, "LADDER": 3, "CHOCK": 4, "EXT": 2},
        "full": {"STT49": 7, "P25A": 2, "MSU200": 5, "TOWBAR": 5, "LADDER": 4, "CHOCK": 6, "EXT": 3},
    }[name]
    # Interleave large and small families for deterministic spatial variety.
    order = ("P25A", "STT49", "MSU200", "TOWBAR", "CHOCK", "LADDER", "EXT")
    result = []
    while any(counts.values()):
        for code in order:
            if counts[code] > 0:
                result.append(code); counts[code] -= 1
    return result


def candidates():
    values = []
    # Bow staging has the most open deck; edge rows then fill aft gaps.
    for y in (-26.0, 26.0, -20.0, 20.0, -9.0, 9.0, 0.0):
        for x in range(24, 145, 7):
            values += [(float(x), y, 0.0), (float(x), y, 180.0)]
    for y in (-33.0, 33.0, -28.0, 28.0, -23.0, 23.0, -5.0, 5.0):
        for x in range(145, 460, 7):
            values += [(float(x), y, 0.0), (float(x), y, 180.0), (float(x), y, 90.0)]
    # Preserve order while removing exact duplicates.
    seen, result = set(), []
    for item in values:
        if item not in seen: seen.add(item); result.append(item)
    return result


def build_layout(name, parts, baseline_targets):
    outline = deck_outline()
    aircraft = aircraft_for_layout(name)
    placed, entries = [], []
    rejected = {"outside_deck": 0, "fixed_obstacle": 0, "aircraft": 0, "vehicle_clearance": 0}
    primary_material = {item.code: B.MATERIALS[item.material][0] for item in P.families}
    for index, code in enumerate(family_roster(name), 1):
        source = P.family(code)
        local = family_shape(parts, code)
        chosen = None
        for x, y, heading in candidates():
            shape = transform(local, x, y, P.deck_top_z, heading)
            if not bbox_inside(shape, outline): rejected["outside_deck"] += 1; continue
            if exact_overlap(shape, baseline_targets): rejected["fixed_obstacle"] += 1; continue
            if exact_overlap(shape, [item["shape"] for item in aircraft]): rejected["aircraft"] += 1; continue
            if any(bbox_gap(shape, prior["shape"]) < LP.vehicle_clearance - 1.0e-6 for prior in placed):
                rejected["vehicle_clearance"] += 1; continue
            chosen = (x, y, heading, shape); break
        if chosen is None:
            raise RuntimeError(f"could not place {name} {code} {index}; rejected={rejected}")
        x, y, heading, shape = chosen
        entry = {
            "equipment_family": code, "equipment_name": source.name, "variant": "Type01",
            "instance_id": f"DV{index:03d}", "x": x, "y": y, "z": P.deck_top_z, "heading": heading,
            "material_assignment": primary_material[code],
            "intended_relationship_to_nearby_aircraft": "none; independent static staging with validated clearance",
            "confidence_or_display_rationale": f"{source.confidence}; representative deployment-era support distribution, not a photographed coordinate",
            "state": "firefighting" if code in {"P25A", "EXT"} else ("stored" if code in {"LADDER", "CHOCK"} else "staged"),
            "intentional_aircraft_link": None, "source": source.evidence_url,
        }
        entries.append(entry); placed.append({"entry": entry, "shape": shape, "parts": placed_family_parts(parts, entry)})
    return entries, placed, aircraft, rejected


def config_path(name):
    return M6 / "Layout" / {"light": "light_support_layout.json", "default": "default_support_layout.json", "full": "full_support_layout.json"}[name]


def save_config(name, entries):
    payload = {
        "schema": "cvn69-deck-equipment-layout-v1", "name": name,
        "coordinate_system": LP.coordinate_system, "deck_top_z_mm": P.deck_top_z,
        "interference_threshold_mm3": LP.interference_threshold_mm3,
        "airwing_layout": {"light": "light_deck_layout.json", "default": "default_deployment_layout.json", "full": "full_deck_layout.json"}[name],
        "entries": entries,
    }
    path = config_path(name); path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def baseline_review_specs(baseline):
    result = []
    for item in baseline:
        material = "charcoal" if item.material == "charcoal" else "ash_gray"
        result.append(ReviewSpec(item.name, item.shape, material, item.role, item.source, item.source, "approved immutable baseline", 0.60, allow_multiple=item.allow_multiple))
    return result


def aircraft_review_specs(records):
    result = []
    for record in records:
        for item in record["parts"]:
            material = {"blue_grey": "ash_gray", "charcoal": "charcoal", "ivory": "ivory", "silver": "silver"}.get(item.material, "ash_gray")
            result.append(ReviewSpec(item.name, item.shape, material, item.role, item.aircraft_code, item.evidence, "approved Milestone 5 aircraft", item.minimum_feature_mm))
    return result


def vehicle_review_specs(placed):
    return [part for record in placed for part in record["parts"]]


def export_step(path, specs):
    doc = App.newDocument(path.stem); objects = []
    try:
        for spec in specs:
            obj = doc.addObject("Part::Feature", spec.name); obj.Shape = spec.shape; objects.append(obj)
        doc.recompute(); Part.export(objects, str(path))
    finally:
        App.closeDocument(doc.Name)


def create_document(baseline, aircraft, vehicles):
    doc = App.newDocument("CVN69_Deck_Equipment_Layout")
    info = doc.addObject("App::FeaturePython", "LayoutInformation")
    for prop, value in (("LayoutName", "default_support"), ("CoordinateSystem", LP.coordinate_system), ("GeometryStatus", "Approved M2-M5 BReps plus new M6 parametric equipment; review assembly"), ("ShipBaseline", "immutable; no baseline file is written")):
        info.addProperty("App::PropertyString", prop); setattr(info, prop, value)
    groups = {name: doc.addObject("App::DocumentObjectGroup", name) for name in ("ApprovedShipBaseline", "ApprovedAirWing", "PlacedDeckVehicles")}
    for spec, group_name in [*((item, "ApprovedShipBaseline") for item in baseline), *((item, "ApprovedAirWing") for item in aircraft), *((item, "PlacedDeckVehicles") for item in vehicles)]:
        obj = doc.addObject("Part::Feature", spec.name); obj.Shape = spec.shape
        obj.addProperty("App::PropertyString", "ReviewRole").ReviewRole = spec.role
        obj.addProperty("App::PropertyString", "SourceFamily").SourceFamily = spec.family
        groups[group_name].addObject(obj)
    doc.recompute(); return doc


def main():
    print("Building Milestone 6 support-equipment layouts")
    parts = B.build_parts(False)
    approved_baseline_raw = AW.load_baseline()
    baseline = baseline_review_specs(approved_baseline_raw)
    collision_targets = [item for item in approved_baseline_raw if item.role not in {"hull_module", "deck_module", "interface_pad"}]
    layouts = {}
    for name in ("light", "default", "full"):
        entries, placed, aircraft, rejected = build_layout(name, parts, collision_targets)
        path = save_config(name, entries)
        layouts[name] = {"entries": entries, "placed": placed, "aircraft": aircraft, "rejected": rejected, "path": path}

    default_vehicles = vehicle_review_specs(layouts["default"]["placed"])
    default_aircraft = aircraft_review_specs(layouts["default"]["aircraft"])
    doc = create_document(baseline, default_aircraft, default_vehicles)
    fcstd = M6 / "CAD" / "FreeCAD" / "CVN69_Deck_Equipment_Layout.FCStd"; doc.saveAs(str(fcstd))
    support_step = M6 / "STEP" / "CVN69_Default_Support_Layout.step"; export_step(support_step, default_vehicles)
    support_obj = M6 / "OBJ" / "CVN69_Default_Support_Layout.obj"; B.write_obj(support_obj, default_vehicles)
    support_3mf = M6 / "3MF" / "CVN69_Default_Support_Layout_Review.3mf"; B.write_3mf(support_3mf, default_vehicles, "CVN-69 Default Support Layout Review")
    integrated = [*baseline, *default_aircraft, *default_vehicles]
    review_step = M6 / "STEP" / "CVN69_Full_Ship_AirWing_Vehicles_Review.step"; export_step(review_step, integrated)
    review_3mf = M6 / "3MF" / "CVN69_Full_Ship_AirWing_Vehicles_Review.3mf"; B.write_3mf(review_3mf, integrated, "CVN-69 Full Ship Air Wing Vehicles Review")

    combined_outputs = []
    for name in ("light", "full"):
        aircraft_specs = aircraft_review_specs(layouts[name]["aircraft"])
        vehicle_specs = vehicle_review_specs(layouts[name]["placed"])
        path = M6 / "3MF" / f"CVN69_{name.title()}_AirWing_Support_Review.3mf"
        B.write_3mf(path, [*baseline, *aircraft_specs, *vehicle_specs], f"CVN-69 {name.title()} Air Wing and Support Review")
        combined_outputs.append(path)

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(), "coordinate_system": LP.coordinate_system,
        "baseline_objects": len(baseline), "collision_targets": len(collision_targets),
        "layouts": {name: {"support_instances": len(data["entries"]), "aircraft_instances": len(data["aircraft"]), "rejected_candidates": data["rejected"], "config": str(data["path"].relative_to(M6))} for name, data in layouts.items()},
        "outputs": [str(path.relative_to(M6)) for path in (fcstd, support_step, support_obj, support_obj.with_suffix(".mtl"), support_3mf, review_step, review_3mf, *combined_outputs)],
        "overall_status": "PASS",
    }
    (M6 / "QA" / "Layout_Build_Report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    App.closeDocument(doc.Name)
    print(json.dumps({"status": "PASS", "support_counts": {name: len(data["entries"]) for name, data in layouts.items()}, "baseline_objects": len(baseline)}, indent=2))


if __name__ == "__main__":
    main()
