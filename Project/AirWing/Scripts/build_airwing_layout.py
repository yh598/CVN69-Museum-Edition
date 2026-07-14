#!/usr/bin/env python3
"""Build configurable CVN-69 air-wing layouts on immutable M2–M4 geometry."""

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
M5 = PROJECT / "AirWing"
sys.path.insert(0, str(M5 / "CAD" / "Python"))
from aircraft_layout_parameters import make_parameters as make_layout_parameters  # noqa: E402


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


B = load_module("m5_build_for_layout", M5 / "Scripts" / "build_airwing.py")
P = B.P
LP = make_layout_parameters()


@dataclass
class PlacedSpec:
    name: str
    shape: object
    material: str
    role: str
    aircraft_code: str
    variant: str
    instance: str
    evidence: str
    confidence: str
    print_rotation: object = None
    print_override: object = None
    print_note: str = "non-production integrated review object"
    minimum_feature_mm: float = 0.60
    allow_multiple: bool = False


@dataclass
class BaselineSpec:
    name: str
    shape: object
    material: str
    role: str
    source: str
    print_rotation: object = None
    print_override: object = None
    print_note: str = "approved baseline review geometry"
    minimum_feature_mm: float = 0.60
    allow_multiple: bool = True


def point_in_polygon(x, y, polygon):
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1.0e-12) + xi:
            inside = not inside
        j = i
    return inside


def deck_outline_authoritative():
    return tuple((P.overall_length - x, y) for x, y in P.integration.deck.outline_points)


def transform(shape, x, y, z, heading, local=(0.0, 0.0, 0.0)):
    result = shape.copy()
    result.translate(App.Vector(*local))
    if abs(heading) > 1.0e-9:
        result.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), heading)
    result.translate(App.Vector(x, y, z))
    return result


def accessory_offsets(item):
    if item.code.startswith(("FA18", "EA18")):
        return {"canopy_insert": (4.4, 0, 1.56), "squadron_id_insert": (-3.8, 1.5, 1.30)}
    if item.code.startswith("E2C"):
        return {"canopy_insert": (5.4, 0, 1.73), "rotodome": (-0.6, 0, 3.00), "squadron_id_insert": (-3.8, 2.0, 1.42)}
    if item.code.startswith("C2A"):
        return {"canopy_insert": (5.2, 0, 1.83), "squadron_id_insert": (-3.8, 2.0, 1.42)}
    return {"canopy_insert": (7.0, 0, 2.07), "main_rotor": (0, 0, 2.25), "squadron_id_insert": (-2.2, 1.0, 2.07)}


def placed_aircraft(entry, production):
    item = P.aircraft(entry["type"])
    variant = entry["variant"]
    body = next(spec for spec in production if spec.aircraft_code == item.code and spec.role == "aircraft_body" and spec.variant == variant)
    related = [body]
    related += [spec for spec in production if spec.aircraft_code == item.code and spec.role in {"canopy_insert", "squadron_id_insert"}]
    if item.dome_diameter:
        related += [spec for spec in production if spec.aircraft_code == item.code and spec.role == "rotodome"]
    if item.rotor_diameter:
        related += [spec for spec in production if spec.aircraft_code == item.code and spec.role == "main_rotor" and spec.variant == variant]
    offsets = accessory_offsets(item)
    parts = []
    for spec in related:
        local = (0.0, 0.0, 0.0) if spec.role == "aircraft_body" else offsets[spec.role]
        shape = transform(spec.shape, entry["x"], entry["y"], entry["z"], entry["heading"], local)
        parts.append(PlacedSpec(
            f"{entry['id']}_{spec.role.title().replace('_', '')}", shape, spec.material,
            spec.role, item.code, variant, entry["id"], entry["source"], entry["confidence"],
            minimum_feature_mm=spec.minimum_feature_mm,
        ))
    return parts


def combined_shape(parts):
    return Part.makeCompound([part.shape for part in parts])


def load_baseline():
    records = []
    sources = (
        (PROJECT / "Integration" / "CAD" / "FreeCAD" / "CVN69_Hull_Deck_Integration.FCStd", "IntegrationRole", "M2"),
        (PROJECT / "Island" / "CAD" / "FreeCAD" / "CVN69_Island.FCStd", "IslandRole", "M3"),
        (PROJECT / "WeaponsDeckEdge" / "CAD" / "FreeCAD" / "CVN69_Weapons_DeckEdge.FCStd", "WeaponsDeckEdgeRole", "M4"),
    )
    for path, prop, source in sources:
        doc = App.openDocument(str(path))
        try:
            for obj in doc.Objects:
                role = str(getattr(obj, prop, ""))
                if not role or role in {"test_coupon", "interface_coupon"} or not hasattr(obj, "Shape") or obj.Shape.isNull():
                    continue
                material_name = str(getattr(obj, "Material", ""))
                material = "charcoal" if any(word in material_name.lower() for word in ("charcoal", "black")) else "blue_grey"
                records.append(BaselineSpec(f"Approved_{source}_{obj.Name}", obj.Shape.copy(), material, role, source))
        finally:
            App.closeDocument(doc.Name)
    return records


def collision_baseline(baseline):
    # Hull pieces are far below the deck and deck-module contact at z=34.5 is
    # intended. They remain in the review export and are checked once by the
    # final validator, but are excluded from the repeated placement-search BOPs.
    return [item for item in baseline if item.role not in {"hull_module", "deck_module", "interface_pad"}]


def candidate_positions():
    candidates = []
    # Broad central deck: folded aircraft transverse in two rows.
    for y in (14.5, -15.5, 0.0):
        for x in list(range(148, 321, 14)) + list(range(362, 447, 14)):
            for heading in (90.0, 270.0):
                candidates.append((float(x), y, heading))
    # Longitudinal parking and launch/taxi spots.
    for y in (0.0, 13.5, -13.5, 25.0, -25.0):
        for x in list(range(155, 321, 28)) + list(range(365, 441, 28)):
            for heading in (0.0, 180.0):
                candidates.append((float(x), y, heading))
    # Additional outer-deck longitudinal rows used only when they clear the
    # actual elevator/marking/catapult solids and traced edge margin.
    for y in (27.0, -27.0, 20.5, -21.0):
        for x in list(range(145, 326, 27)) + list(range(352, 447, 27)):
            for heading in (0.0, 180.0):
                candidates.append((float(x), y, heading))
    # Narrow bow/stern centerline spots.
    for x in (32.0, 61.0, 90.0, 119.0, 445.0):
        for heading in (0.0, 180.0):
            candidates.append((x, 0.0, heading))
    # Remove exact duplicates while preserving preference order.
    seen = set()
    result = []
    for item in candidates:
        key = tuple(round(value, 3) for value in item)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def roster(name):
    base = [
        ("E2C_VAW123", "spread"), ("C2A_VRC40", "folded"),
        ("MH60R_HSM74", "deployed"), ("MH60S_HSC7", "folded"),
        ("EA18G_VAQ130", "spread"),
        ("FA18E_VFA105", "launch"), ("FA18F_VFA32", "launch"),
        ("FA18E_VFA83", "spread"), ("FA18E_VFA131", "spread"),
    ]
    folded_cycle = [
        ("FA18E_VFA105", "folded"), ("FA18F_VFA32", "folded"),
        ("FA18E_VFA83", "folded"), ("FA18E_VFA131", "folded"),
        ("EA18G_VAQ130", "folded"), ("MH60R_HSM74", "folded"),
        ("MH60S_HSC7", "folded"), ("E2C_VAW123", "folded"),
    ]
    targets = {"light": 16, "default_deployment": 32, "full_deck": 36}
    wanted = targets[name]
    if name == "full_deck":
        full_cycle = [
            ("FA18E_VFA105", "folded"), ("FA18F_VFA32", "folded"),
            ("FA18E_VFA83", "folded"), ("FA18E_VFA131", "folded"),
            ("EA18G_VAQ130", "folded"), ("E2C_VAW123", "folded"),
            ("C2A_VRC40", "folded"), ("MH60R_HSM74", "folded"),
            ("MH60S_HSC7", "folded"),
        ]
        return [full_cycle[index % len(full_cycle)] for index in range(wanted)]
    result = list(base if name != "light" else base[:8])
    index = 0
    while len(result) < wanted:
        result.append(folded_cycle[index % len(folded_cycle)])
        index += 1
    return result


def bbox_inside_deck(shape, outline):
    box = shape.BoundBox
    margin = LP.deck_edge_margin
    corners = ((box.XMin-margin, box.YMin-margin), (box.XMin-margin, box.YMax+margin), (box.XMax+margin, box.YMin-margin), (box.XMax+margin, box.YMax+margin))
    return all(point_in_polygon(x, y, outline) for x, y in corners)


def bbox_gap(left, right):
    a, b = left.BoundBox, right.BoundBox
    dx = max(0.0, max(a.XMin, b.XMin) - min(a.XMax, b.XMax))
    dy = max(0.0, max(a.YMin, b.YMin) - min(a.YMax, b.YMax))
    dz = max(0.0, max(a.ZMin, b.ZMin) - min(a.ZMax, b.ZMax))
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def baseline_overlap(shape, baseline):
    hits = []
    for target in baseline:
        a, b = shape.BoundBox, target.shape.BoundBox
        separated = (a.XMax <= b.XMin or b.XMax <= a.XMin or a.YMax <= b.YMin or b.YMax <= a.YMin or a.ZMax <= b.ZMin or b.ZMax <= a.ZMin)
        if separated:
            continue
        common = shape.common(target.shape)
        volume = 0.0 if common.isNull() else float(common.Volume)
        if volume > P.interference_threshold_mm3:
            hits.append((target.name, target.role, volume))
    return hits


def assign_layout(name, production, baseline):
    outline = deck_outline_authoritative()
    candidates = candidate_positions()
    placed = []
    entries = []
    rejected = {"outside_deck": 0, "baseline": 0, "aircraft_clearance": 0}
    for index, (code, variant) in enumerate(roster(name), 1):
        item = P.aircraft(code)
        selected = None
        for x, y, heading in candidates:
            entry = {
                "id": f"AW{index:03d}", "type": code, "aircraft": item.name,
                "variant": variant, "squadron": item.squadron,
                "x": x, "y": y, "z": P.deck_top_z, "heading": heading,
                "material": "Bambu PLA Basic Blue Grey / assigned no-paint inserts",
                "source": item.evidence_url, "confidence": item.confidence,
            }
            parts = placed_aircraft(entry, production)
            shape = combined_shape(parts)
            if not bbox_inside_deck(shape, outline):
                rejected["outside_deck"] += 1
                continue
            if baseline_overlap(shape, baseline):
                rejected["baseline"] += 1
                continue
            clearance_ok = True
            for prior in placed:
                # Conservative AABB clearance is intentionally stricter than
                # shape-to-shape distance and makes layout regeneration fast.
                if bbox_gap(shape, prior["shape"]) < 2.0 * P.assembly_clearance_per_side - 1.0e-6:
                    clearance_ok = False
                    break
            if not clearance_ok:
                rejected["aircraft_clearance"] += 1
                continue
            selected = (entry, parts, shape)
            break
        if selected is None:
            raise RuntimeError(f"could not place {name} aircraft {index}: {code}/{variant}; rejected={rejected}")
        entry, parts, shape = selected
        entries.append(entry)
        placed.append({"entry": entry, "parts": parts, "shape": shape})
    return entries, placed, rejected


def write_or_load_config(name, entries):
    filename = {"light": "light_deck_layout.json", "default_deployment": "default_deployment_layout.json", "full_deck": "full_deck_layout.json"}[name]
    path = M5 / "Layout" / filename
    payload = {
        "schema": "cvn69-airwing-layout-v1", "name": name,
        "coordinate_system": LP.coordinate_system, "aircraft_clearance_per_side_mm": P.assembly_clearance_per_side,
        "entries": entries,
    }
    if not path.exists() or os.environ.get("CVN69_REGENERATE_LAYOUTS") == "1":
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return payload
    existing = json.loads(path.read_text(encoding="utf-8"))
    required = {"id", "type", "variant", "squadron", "x", "y", "z", "heading", "material", "source", "confidence"}
    if any(not required.issubset(entry) for entry in existing.get("entries", [])):
        raise ValueError(f"invalid layout schema in {path}")
    return existing


def config_path(name):
    filename = {"light": "light_deck_layout.json", "default_deployment": "default_deployment_layout.json", "full_deck": "full_deck_layout.json"}[name]
    return M5 / "Layout" / filename


def create_layout_document(baseline, placed, layout_name):
    doc = App.newDocument("CVN69_AirWing_Layout")
    info = doc.addObject("App::FeaturePython", "LayoutInformation")
    for prop, value in (
        ("LayoutName", layout_name), ("CoordinateSystem", LP.coordinate_system),
        ("GeometryStatus", "Approved M2-M4 BReps plus new M5 parametric aircraft; review assembly"),
        ("ShipBaseline", "immutable; no baseline file is written"),
    ):
        info.addProperty("App::PropertyString", prop)
        setattr(info, prop, value)
    baseline_group = doc.addObject("App::DocumentObjectGroup", "ApprovedShipBaseline")
    aircraft_group = doc.addObject("App::DocumentObjectGroup", "PlacedAirWing")
    baseline_objects = []
    for spec in baseline:
        obj = doc.addObject("Part::Feature", spec.name)
        obj.Shape = spec.shape
        obj.addProperty("App::PropertyString", "BaselineRole").BaselineRole = spec.role
        obj.addProperty("App::PropertyString", "BaselineSource").BaselineSource = spec.source
        baseline_group.addObject(obj)
        baseline_objects.append(obj)
    aircraft_objects = []
    for record in placed:
        instance_group = doc.addObject("App::DocumentObjectGroup", record["entry"]["id"])
        aircraft_group.addObject(instance_group)
        for spec in record["parts"]:
            obj = doc.addObject("Part::Feature", spec.name)
            obj.Shape = spec.shape
            obj.addProperty("App::PropertyString", "AirWingRole").AirWingRole = spec.role
            obj.addProperty("App::PropertyString", "AircraftCode").AircraftCode = spec.aircraft_code
            obj.addProperty("App::PropertyString", "Variant").Variant = spec.variant
            obj.addProperty("App::PropertyString", "Material").Material = B.MATERIALS[spec.material][0]
            obj.addProperty("App::PropertyString", "EvidenceBasis").EvidenceBasis = spec.evidence
            instance_group.addObject(obj)
            aircraft_objects.append(obj)
    doc.recompute()
    return doc, baseline_objects, aircraft_objects


def export_step(path, specs):
    doc = App.newDocument(path.stem)
    objects = []
    try:
        for spec in specs:
            obj = doc.addObject("Part::Feature", spec.name)
            obj.Shape = spec.shape
            objects.append(obj)
        doc.recompute()
        Part.export(objects, str(path))
    finally:
        App.closeDocument(doc.Name)


def main():
    print("Building configurable CVN-69 Milestone 5 layouts")
    production = B.build_parts()
    baseline = load_baseline()
    collision_targets = collision_baseline(baseline)
    summaries = {}
    default_placed = None
    for name in ("light", "default_deployment", "full_deck"):
        path = config_path(name)
        if path.exists() and os.environ.get("CVN69_REGENERATE_LAYOUTS") != "1":
            payload = json.loads(path.read_text(encoding="utf-8"))
            rejected = {"outside_deck": 0, "baseline": 0, "aircraft_clearance": 0, "note": "persisted configuration used"}
        else:
            generated_entries, _generated_placed, rejected = assign_layout(name, production, collision_targets)
            payload = write_or_load_config(name, generated_entries)
        # Rebuild from the persisted configuration; this is the authoritative path.
        persisted = []
        for entry in payload["entries"]:
            parts = placed_aircraft(entry, production)
            persisted.append({"entry": entry, "parts": parts, "shape": combined_shape(parts)})
        summaries[name] = {"count": len(persisted), "rejected_candidates_during_generation": rejected}
        if name == "default_deployment":
            default_placed = persisted
    if default_placed is None:
        raise RuntimeError("default layout missing")

    doc, baseline_objects, aircraft_objects = create_layout_document(baseline, default_placed, "default_deployment")
    fcstd = M5 / "CAD" / "FreeCAD" / "CVN69_AirWing_Layout.FCStd"
    doc.saveAs(str(fcstd))
    all_specs = [*baseline, *(part for record in default_placed for part in record["parts"])]
    aircraft_specs = [part for record in default_placed for part in record["parts"]]
    review_step = M5 / "STEP" / "CVN69_Hull_Deck_Island_Weapons_AirWing_Review.step"
    layout_step = M5 / "STEP" / "CVN69_AirWing_Default_Layout.step"
    export_step(review_step, all_specs)
    export_step(layout_step, aircraft_specs)
    review_3mf = M5 / "3MF" / "CVN69_Hull_Deck_Island_Weapons_AirWing_Review.3mf"
    layout_3mf = M5 / "3MF" / "CVN69_AirWing_Default_Layout.3mf"
    B.write_3mf(review_3mf, all_specs, "CVN-69 M2-M5 Integrated Air Wing Review")
    B.write_3mf(layout_3mf, aircraft_specs, "CVN-69 Default Deployment Air Wing Layout")
    obj = M5 / "OBJ" / "CVN69_AirWing_Default_Layout.obj"
    B.write_obj(obj, aircraft_specs)

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(), "coordinate_system": LP.coordinate_system,
        "baseline_objects": len(baseline), "collision_targets": len(collision_targets),
        "layouts": summaries, "default_review_aircraft": len(default_placed),
        "outputs": [str(path.relative_to(M5)) for path in (fcstd, review_step, layout_step, review_3mf, layout_3mf, obj, obj.with_suffix(".mtl"))],
        "overall_status": "PASS",
    }
    (M5 / "QA" / "Layout_Build_Report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    App.closeDocument(doc.Name)
    print(json.dumps({"status": "PASS", "layouts": {key: value["count"] for key, value in summaries.items()}, "baseline_objects": len(baseline)}, indent=2))


if __name__ == "__main__":
    main()
