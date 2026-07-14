#!/usr/bin/env python3
"""Mandatory deterministic QA for CVN-69 Milestone 3 island."""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import FreeCAD as App
import Part


SCRIPT = Path(__file__).resolve()
ISLAND = SCRIPT.parents[1]
PROJECT = ISLAND.parent
REPO = PROJECT.parent
QA = ISLAND / "QA"
MANIFEST_PATH = QA / "build_manifest.json"
sys.path.insert(0, str(ISLAND / "CAD" / "Python"))
from island_parameters import make_parameters  # noqa: E402


P = make_parameters()
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
REFERENCE_3MF = {"CVN69_Island_Assembly.3mf", "CVN69_Hull_Deck_Island_Review.3mf"}


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quantized(point, places=5):
    return tuple(round(float(value), places) for value in point)


def read_binary_stl(path: Path):
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError("file is shorter than a binary STL header")
    count = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + count * 50:
        raise ValueError("binary STL length mismatch")
    normals, triangles = [], []
    for index in range(count):
        values = struct.unpack_from("<12fH", data, 84 + index * 50)
        normals.append(values[:3])
        triangles.append((values[3:6], values[6:9], values[9:12]))
    return normals, triangles


def mesh_metrics(path: Path):
    normals, triangles = read_binary_stl(path)
    edges = Counter()
    vertices = set()
    adjacency = defaultdict(set)
    minimum = [float("inf")] * 3
    maximum = [float("-inf")] * 3
    degenerate = normal_mismatch = 0
    signed_volume = 0.0
    for stored_normal, triangle in zip(normals, triangles):
        keys = [quantized(point) for point in triangle]
        vertices.update(keys)
        for point in keys:
            for axis, value in enumerate(point):
                minimum[axis] = min(minimum[axis], value)
                maximum[axis] = max(maximum[axis], value)
        for left, right in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((keys[left], keys[right])))
            edges[edge] += 1
            adjacency[keys[left]].add(keys[right])
            adjacency[keys[right]].add(keys[left])
        a, b, c = triangle
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        w = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        cross = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        magnitude = math.sqrt(sum(value * value for value in cross))
        if magnitude < 1.0e-10:
            degenerate += 1
        else:
            calculated = tuple(value / magnitude for value in cross)
            stored_length = math.sqrt(sum(value * value for value in stored_normal))
            if stored_length <= 1.0e-12:
                normal_mismatch += 1
            else:
                stored = tuple(value / stored_length for value in stored_normal)
                if sum(calculated[axis] * stored[axis] for axis in range(3)) < 0.985:
                    normal_mismatch += 1
        signed_volume += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0
    unseen = set(vertices)
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            current = stack.pop()
            neighbours = adjacency[current] & unseen
            unseen.difference_update(neighbours)
            stack.extend(neighbours)
    bad_edges = sum(count != 2 for count in edges.values())
    return {
        "facets": len(triangles),
        "vertices": len(vertices),
        "components": components,
        "min_mm": [round(value, 5) for value in minimum],
        "max_mm": [round(value, 5) for value in maximum],
        "bounds_mm": [round(maximum[axis] - minimum[axis], 5) for axis in range(3)],
        "non_two_incident_edges": bad_edges,
        "degenerate_facets": degenerate,
        "normal_mismatches": normal_mismatch,
        "signed_volume_mm3": round(signed_volume, 5),
        "watertight": bad_edges == 0,
        "manifold": bad_edges == 0,
        "normals_consistent": normal_mismatch == 0 and signed_volume > 1.0e-9,
    }


def check_3mf(path: Path):
    required = {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = sorted(required - names)
        crc_member = archive.testzip()
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    invalid_indices = 0
    vertex_count = triangle_count = 0
    minimum = [float("inf")] * 3
    maximum = [float("-inf")] * 3
    object_names = []
    material_missing = 0
    for obj in root.findall(".//m:object", ns):
        object_names.append(obj.attrib.get("name", ""))
        mesh = obj.find("./m:mesh", ns)
        if mesh is None:
            continue
        vertices = mesh.findall("./m:vertices/m:vertex", ns)
        triangles = mesh.findall("./m:triangles/m:triangle", ns)
        vertex_count += len(vertices)
        triangle_count += len(triangles)
        for vertex in vertices:
            point = [float(vertex.attrib[key]) for key in ("x", "y", "z")]
            for axis, value in enumerate(point):
                minimum[axis] = min(minimum[axis], value)
                maximum[axis] = max(maximum[axis], value)
        for triangle in triangles:
            if any(int(triangle.attrib[key]) < 0 or int(triangle.attrib[key]) >= len(vertices) for key in ("v1", "v2", "v3")):
                invalid_indices += 1
            if "pid" not in triangle.attrib or "p1" not in triangle.attrib:
                material_missing += 1
    objects = root.findall(".//m:object", ns)
    build_items = root.findall(".//m:build/m:item", ns)
    finite = vertex_count > 0
    return {
        "zip_crc_ok": crc_member is None,
        "missing_members": missing,
        "objects": len(objects),
        "object_names": object_names,
        "unique_object_names": len(set(object_names)),
        "build_items": len(build_items),
        "vertices": vertex_count,
        "triangles": triangle_count,
        "invalid_triangle_indices": invalid_indices,
        "triangles_without_material": material_missing,
        "min_mm": [round(value, 5) for value in minimum] if finite else [],
        "bounds_mm": [round(maximum[axis] - minimum[axis], 5) for axis in range(3)] if finite else [],
        "valid": crc_member is None and not missing and bool(objects) and len(build_items) == len(objects) and invalid_indices == 0 and material_missing == 0 and len(set(object_names)) == len(object_names) and all(object_names),
    }


def png_dimensions(path: Path):
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError(path)
    return struct.unpack(">II", data[16:24])


def pdf_metrics(path: Path):
    data = path.read_bytes()
    return {"bytes": len(data), "header_ok": data.startswith(b"%PDF-"), "eof_ok": b"%%EOF" in data[-1024:], "pages": len(re.findall(rb"/Type\s*/Page\b", data))}


def add_check(checks, name, passed, evidence):
    checks.append({"name": name, "status": "PASS" if passed else "FAIL", "evidence": evidence})


def polygon_wire(points, z_value):
    vectors = [App.Vector(float(x), float(y), float(z_value)) for x, y in points]
    return Part.makePolygon(vectors + [vectors[0]])


def polygon_prism(points, z0, height):
    return Part.Face(polygon_wire(points, z0)).extrude(App.Vector(0, 0, float(height)))


def strict_record(name, role, shape):
    messages = []
    try:
        shape.check(True)
    except ValueError as exc:
        messages = [line.strip() for line in str(exc).splitlines() if line.strip()]
    return {
        "name": name,
        "role": role,
        "valid": bool(shape.isValid()),
        "solids": len(shape.Solids),
        "all_solids_closed": bool(shape.Solids) and all(solid.isClosed() for solid in shape.Solids),
        "strict_messages": messages,
        "self_intersections": sum("SelfIntersect" in line for line in messages),
    }


def mast_lean(shape):
    points, _faces = shape.tessellate(P.tessellation_deflection)
    tuples = sorted({(round(point.x, 6), round(point.y, 6), round(point.z, 6)) for point in points})
    base_z = P.deck_top_z + 16.5
    top_z = P.deck_top_z + P.mast_top_height
    lower = [point for point in tuples if point[2] <= base_z + 0.15]
    upper = [point for point in tuples if point[2] >= top_z - 0.15]
    if not lower or not upper:
        raise RuntimeError("Cannot sample mast axis")
    low = (sum(point[0] for point in lower) / len(lower), sum(point[1] for point in lower) / len(lower), sum(point[2] for point in lower) / len(lower))
    high = (sum(point[0] for point in upper) / len(upper), sum(point[1] for point in upper) / len(upper), sum(point[2] for point in upper) / len(upper))
    horizontal = math.hypot(high[0] - low[0], high[1] - low[1])
    return math.degrees(math.atan2(horizontal, high[2] - low[2])), low, high


def validate_fcstd():
    island_doc = App.openDocument(str(ISLAND / "CAD" / "FreeCAD" / "CVN69_Island.FCStd"))
    records = []
    context = {}
    try:
        island_doc.recompute()
        objects = [obj for obj in island_doc.Objects if hasattr(obj, "IslandRole") and hasattr(obj, "Shape") and not obj.Shape.isNull()]
        for obj in objects:
            records.append(strict_record(obj.Name, str(obj.IslandRole), obj.Shape))
        production = [obj for obj in objects if str(obj.IslandRole) != "interface_coupon"]
        coupons = [obj for obj in objects if str(obj.IslandRole) == "interface_coupon"]
        foundation = island_doc.getObject("Foundation_Lower_Island").Shape
        mast = island_doc.getObject("Main_Mast").Shape
        expected_plug = polygon_prism(P.interface_plug_points, P.deck_top_z - P.interface_plug_depth, P.interface_plug_depth)
        clip = Part.makeBox(60, 40, P.interface_plug_depth, App.Vector(P.opening_bounds[0] - 15, P.opening_bounds[1] - 10, P.deck_top_z - P.interface_plug_depth))
        actual_plug = foundation.common(clip).removeSplitter()
        plug_difference = expected_plug.cut(actual_plug).Volume + actual_plug.cut(expected_plug).Volume
        expected_bounds = expected_plug.BoundBox
        actual_bounds = actual_plug.BoundBox
        expected_center = ((expected_bounds.XMin + expected_bounds.XMax) / 2.0, (expected_bounds.YMin + expected_bounds.YMax) / 2.0)
        actual_center = ((actual_bounds.XMin + actual_bounds.XMax) / 2.0, (actual_bounds.YMin + actual_bounds.YMax) / 2.0)
        location_error = (abs(expected_center[0] - actual_center[0]), abs(expected_center[1] - actual_center[1]))
        vertical_error = abs(actual_bounds.ZMax - P.deck_top_z)
        clearance = polygon_wire(P.opening_authoritative, P.deck_top_z).distToShape(polygon_wire(P.interface_plug_points, P.deck_top_z))[0]
        opening_volume = polygon_prism(P.opening_authoritative, P.deck_top_z - P.interface_plug_depth, P.interface_plug_depth)
        rotated = expected_plug.copy()
        cx, cy = P.opening_center
        rotated.rotate(App.Vector(cx, cy, P.deck_top_z), App.Vector(0, 0, 1), 180)
        backward_outside = rotated.cut(opening_volume).Volume
        lean, lean_low, lean_high = mast_lean(mast)
        context = {
            "production_part_count": len(production),
            "coupon_part_count": len(coupons),
            "interface_plug_symmetric_difference_mm3": float(plug_difference),
            "interface_clearance_per_side_mm": float(clearance),
            "position_error_x_mm": float(location_error[0]),
            "position_error_y_mm": float(location_error[1]),
            "vertical_seating_error_mm": float(vertical_error),
            "mast_lean_degrees": float(lean),
            "mast_axis_low_mm": list(lean_low),
            "mast_axis_high_mm": list(lean_high),
            "backward_rotated_plug_outside_opening_mm3": float(backward_outside),
            "mast_top_z_mm": float(mast.BoundBox.ZMax),
            "island_height_above_deck_mm": float(mast.BoundBox.ZMax - P.deck_top_z),
        }
    finally:
        App.closeDocument(island_doc.Name)
    return records, context


def baseline_shapes():
    doc = App.openDocument(str(PROJECT / "Integration" / "CAD" / "FreeCAD" / "CVN69_Hull_Deck_Integration.FCStd"))
    records = []
    try:
        for obj in doc.Objects:
            if not hasattr(obj, "IntegrationRole") or not hasattr(obj, "Shape") or obj.Shape.isNull() or str(obj.IntegrationRole) == "test_coupon":
                continue
            records.append((obj.Name, str(obj.IntegrationRole), obj.Shape.copy()))
    finally:
        App.closeDocument(doc.Name)
    return records


def island_shapes():
    doc = App.openDocument(str(ISLAND / "CAD" / "FreeCAD" / "CVN69_Island.FCStd"))
    records = []
    try:
        for obj in doc.Objects:
            if hasattr(obj, "IslandRole") and hasattr(obj, "Shape") and not obj.Shape.isNull() and str(obj.IslandRole) != "interface_coupon":
                records.append((obj.Name, str(obj.IslandRole), obj.Shape.copy()))
    finally:
        App.closeDocument(doc.Name)
    return records


def interference_context():
    baseline = baseline_shapes()
    island = island_shapes()
    totals = {"all": 0.0, "elevators": 0.0, "markings": 0.0, "landing_pads": 0.0, "deck_modules": 0.0}
    pairs = []
    for island_name, _island_role, island_shape in island:
        for baseline_name, baseline_role, baseline_shape in baseline:
            volume = float(island_shape.common(baseline_shape).Volume)
            if volume > 1.0e-8:
                pairs.append({"island": island_name, "baseline": baseline_name, "baseline_role": baseline_role, "volume_mm3": volume})
            totals["all"] += volume
            if baseline_role == "elevator":
                totals["elevators"] += volume
            if baseline_role in {"raised_marking", "catapult_track", "arresting_wire"}:
                totals["markings"] += volume
            if baseline_role == "interface_pad":
                totals["landing_pads"] += volume
            if baseline_role == "deck_module":
                totals["deck_modules"] += volume
    elevator_bounds = [shape.BoundBox for _name, role, shape in baseline if role == "elevator"]
    island_bounds = [shape.BoundBox for _name, _role, shape in island]
    nearest_elevator_gap = min(
        max(0.0, max(elevator.XMin - isle.XMax, isle.XMin - elevator.XMax, elevator.YMin - isle.YMax, isle.YMin - elevator.YMax))
        for elevator in elevator_bounds for isle in island_bounds
    )
    return {
        "baseline_objects": len(baseline),
        "island_objects": len(island),
        "overlap_mm3": totals,
        "overlap_pairs": pairs,
        "nearest_elevator_axis_gap_mm": nearest_elevator_gap,
        "island_x_bounds_mm": [min(shape.BoundBox.XMin for _n, _r, shape in island), max(shape.BoundBox.XMax for _n, _r, shape in island)],
        "deck_seams_x_mm": list(P.integration.deck_authoritative_seams),
    }


def validate_step(path: Path, expected_solids=None):
    shape = Part.read(str(path))
    messages = []
    for solid in shape.Solids:
        try:
            solid.check(True)
        except ValueError as exc:
            messages.extend(line.strip() for line in str(exc).splitlines() if line.strip())
    return {
        "valid": bool(shape.isValid()),
        "solid_count": len(shape.Solids),
        "expected_solids": expected_solids,
        "all_solids_closed": bool(shape.Solids) and all(solid.isClosed() for solid in shape.Solids),
        "self_intersections": sum("SelfIntersect" in line for line in messages),
        "strict_message_count": len(messages),
        "strict_message_types": sorted(set(messages)),
    }


def markdown_report(title, overall, checks, sections=None):
    lines = [f"# {title}", "", f"Overall status: **{'PASS' if overall else 'FAIL'}**", "", "| Check | Status | Evidence |", "|---|---:|---|"]
    for check in checks:
        evidence = str(check["evidence"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {check['status']} | {evidence} |")
    if sections:
        lines.extend(sections)
    return "\n".join(lines) + "\n"


def main():
    generated = datetime.now(timezone.utc).isoformat()
    mesh_checks, dimensional_checks, interference_checks = [], [], []

    stl_results = {}
    for path in sorted((ISLAND / "STL").glob("*.stl")):
        metrics = mesh_metrics(path)
        stl_results[path.name] = metrics
        passed = metrics["watertight"] and metrics["manifold"] and metrics["degenerate_facets"] == 0 and metrics["normals_consistent"] and abs(metrics["min_mm"][2]) <= 0.01 and max(metrics["bounds_mm"]) <= 240.0 + 1.0e-6
        add_check(mesh_checks, f"STL — {path.name}", passed, f"{metrics['facets']} facets; {metrics['components']} component(s); {metrics['non_two_incident_edges']} bad edges; {metrics['bounds_mm']} mm; min z {metrics['min_mm'][2]:.5f}")

    expected_3mf_objects = {
        "CVN69_Island_Assembly.3mf": MANIFEST["counts"]["production_parts"],
        "Print_Plate_01_Island_Body.3mf": 4,
        "Print_Plate_02_Mast_Radar.3mf": 6,
        "Print_Plate_03_Antennas_Details.3mf": 7,
        "Island_Interface_Test_Coupon.3mf": 2,
        "CVN69_Hull_Deck_Island_Review.3mf": MANIFEST["counts"]["review_baseline_objects"] + MANIFEST["counts"]["production_parts"],
    }
    three_mf_results = {}
    for path in sorted((ISLAND / "3MF").glob("*.3mf")):
        result = check_3mf(path)
        three_mf_results[path.name] = result
        reference = path.name in REFERENCE_3MF
        envelope = reference or (max(result["bounds_mm"]) <= 240.0 + 1.0e-6 and abs(result["min_mm"][2]) <= 0.01)
        count_ok = result["objects"] == expected_3mf_objects.get(path.name, -1)
        add_check(mesh_checks, f"3MF — {path.name}", result["valid"] and envelope and count_ok, f"CRC={result['zip_crc_ok']}; named objects={result['objects']}/{expected_3mf_objects.get(path.name)}; triangles={result['triangles']}; bounds={result['bounds_mm']}" + ("; review/reference" if reference else "; print envelope"))

    fcstd_records, context = validate_fcstd()
    add_check(mesh_checks, "FreeCAD Shape.check(True) / strict BOPCheck", len(fcstd_records) == 19 and all(item["valid"] and item["all_solids_closed"] and item["self_intersections"] == 0 for item in fcstd_records), f"{len(fcstd_records)} production/coupon objects; zero invalid/open solids or self-intersections")

    island_expected_solids = sum(item["solid_count"] for item in MANIFEST["parts"])
    coupon_expected_solids = sum(item["solid_count"] for item in MANIFEST["coupon_parts"])
    baseline_expected_solids = sum(len(shape.Solids) for _name, _role, shape in baseline_shapes())
    island_step = validate_step(ISLAND / "STEP" / "CVN69_Island_Assembly.step", island_expected_solids)
    coupon_step = validate_step(ISLAND / "STEP" / "CVN69_Island_Interface_Coupon.step", coupon_expected_solids)
    review_step = validate_step(ISLAND / "STEP" / "CVN69_Hull_Deck_Island_Review.step", baseline_expected_solids + island_expected_solids)
    for label, result in (("Island STEP round-trip", island_step), ("Coupon STEP round-trip", coupon_step), ("Review STEP round-trip", review_step)):
        add_check(mesh_checks, label, result["valid"] and result["solid_count"] == result["expected_solids"] and result["all_solids_closed"] and result["self_intersections"] == 0, f"{result['solid_count']}/{result['expected_solids']} closed solids; self-intersections={result['self_intersections']}; diagnostics={result['strict_message_count']}")

    bambu = json.loads((QA / "BambuStudio_Validation.json").read_text(encoding="utf-8"))
    expected_bambu = len(stl_results) + len(three_mf_results)
    add_check(mesh_checks, "Bambu Studio independent import/manifold check", bambu["overall_status"] == "PASS" and bambu["files_checked"] == expected_bambu, f"Bambu Studio 02.07.01.62 loaded {bambu['files_checked']}/{expected_bambu} STL/3MF exports; all manifold")

    render_names = [
        "Island_Port.png", "Island_Starboard.png", "Island_Forward.png", "Island_Aft.png", "Island_Top.png", "Island_Bow_Isometric.png", "Island_Stern_Isometric.png", "Island_Exploded.png", "Island_Interface_Section.png",
        "CVN69_Hull_Deck_Island_Port.png", "CVN69_Hull_Deck_Island_Starboard.png", "CVN69_Hull_Deck_Island_Top.png", "CVN69_Hull_Deck_Island_Bow_Isometric.png", "CVN69_Hull_Deck_Island_Stern_Isometric.png",
    ]
    required = [
        "README.md", "CAD/Python/island_parameters.py", "CAD/FreeCAD/CVN69_Island.FCStd", "Assembly/Glue_Only_Island_Assembly.md",
        "References/Configuration_Audit.md", "References/Source_Mesh_Island_Measurements.json", "Images/Source_Mesh_Island_Reference.png",
        "STEP/CVN69_Island_Assembly.step", "STEP/CVN69_Island_Interface_Coupon.step", "STEP/CVN69_Hull_Deck_Island_Review.step",
        "OBJ/CVN69_Island_Assembly.obj", "OBJ/CVN69_Island_Assembly.mtl",
        "3MF/CVN69_Island_Assembly.3mf", "3MF/Print_Plate_01_Island_Body.3mf", "3MF/Print_Plate_02_Mast_Radar.3mf", "3MF/Print_Plate_03_Antennas_Details.3mf", "3MF/Island_Interface_Test_Coupon.3mf", "3MF/CVN69_Hull_Deck_Island_Review.3mf",
        "Docs/Island_Drawings.pdf", "Docs/Island_Printing_Guide.pdf", "Docs/Island_Project_Plan.pdf", "Docs/Island_Interface_Coupon_Instructions.pdf", "Docs/Island_Material_Mapping.csv",
        "QA/Approved_Input_Inspection.json", "QA/BambuStudio_Validation.json", "QA/BambuStudio_Validation.md", "QA/Reference_Confidence_Report.md", "QA/build_manifest.json",
        "Scripts/audit_island_reference.py", "Scripts/build_island.py", "Scripts/render_island.py", "Scripts/generate_island_documents.py", "Scripts/run_bambu_island_checks.py", "Scripts/validate_island.py",
    ] + [f"Render/{name}" for name in render_names] + [f"STL/{name}" for name in sorted(stl_results)]
    missing = [relative for relative in required if not (ISLAND / relative).exists()]
    add_check(mesh_checks, "Required source and production outputs exist", not missing, f"{len(required)} required files; missing={missing}")

    hash_mismatches = []
    for relative, expected in MANIFEST["outputs"].items():
        path = ISLAND / relative
        if not path.exists():
            hash_mismatches.append(f"missing {relative}")
        elif path.stat().st_size != expected["bytes"] or sha256(path) != expected["sha256"]:
            hash_mismatches.append(f"hash/size mismatch {relative}")
    add_check(mesh_checks, "Build-manifest production hashes", not hash_mismatches, f"{len(MANIFEST['outputs'])} SHA-256/byte-size records match" if not hash_mismatches else "; ".join(hash_mismatches))

    approved_mismatches = []
    for relative, expected in MANIFEST["approved_input_hashes"].items():
        path = REPO / relative
        if not path.exists() or path.stat().st_size != expected["bytes"] or sha256(path) != expected["sha256"]:
            approved_mismatches.append(relative)
    add_check(mesh_checks, "Approved Milestone 1–2 inputs unchanged", not approved_mismatches, f"{len(MANIFEST['approved_input_hashes'])} immutable hashes match" if not approved_mismatches else str(approved_mismatches))

    build_source = (ISLAND / "Scripts" / "build_island.py").read_text(encoding="utf-8")
    add_check(mesh_checks, "Production build excludes source mesh import", "import Mesh" not in build_source and "CVN69_Optimized" not in build_source and "section_02.stl" not in build_source, "build_island.py creates Part BReps and does not import the reference archive/STL")

    pdfs = {name: pdf_metrics(ISLAND / "Docs" / name) for name in ("Island_Drawings.pdf", "Island_Printing_Guide.pdf", "Island_Project_Plan.pdf", "Island_Interface_Coupon_Instructions.pdf")}
    pdf_ok = all(item["header_ok"] and item["eof_ok"] and item["pages"] >= minimum for item, minimum in zip(pdfs.values(), (6, 4, 3, 1)))
    add_check(mesh_checks, "PDF documentation structure", pdf_ok, str(pdfs))
    render_dimensions = {name: png_dimensions(ISLAND / "Render" / name) for name in render_names}
    add_check(mesh_checks, "All 14 high-resolution renders", len(render_dimensions) == 14 and all(width >= 2000 and height >= 1200 for width, height in render_dimensions.values()), str(render_dimensions))

    # Dimensional and feature-rule checks.
    add_check(dimensional_checks, "Authoritative overall length import", abs(P.overall_length - 476.0) <= 1.0e-9, f"{P.overall_length:.5f} mm")
    add_check(dimensional_checks, "Approved deck elevation import", abs(P.deck_base_z - 31.50) <= 1.0e-9 and abs(P.deck_top_z - 34.50) <= 1.0e-9, f"underside={P.deck_base_z:.3f}; top={P.deck_top_z:.3f} mm")
    add_check(dimensional_checks, "Island opening / foundation match", context["interface_plug_symmetric_difference_mm3"] <= 0.001, f"plug symmetric difference={context['interface_plug_symmetric_difference_mm3']:.9f} mm³")
    add_check(dimensional_checks, "Island X/Y position error", context["position_error_x_mm"] <= 0.10 and context["position_error_y_mm"] <= 0.10, f"x={context['position_error_x_mm']:.6f}; y={context['position_error_y_mm']:.6f} mm")
    add_check(dimensional_checks, "Vertical seating error", context["vertical_seating_error_mm"] <= 0.10, f"{context['vertical_seating_error_mm']:.6f} mm")
    add_check(dimensional_checks, "Island lean", context["mast_lean_degrees"] <= 0.20, f"{context['mast_lean_degrees']:.6f}°")
    add_check(dimensional_checks, "Glue clearance", abs(context["interface_clearance_per_side_mm"] - P.interface_clearance_per_side) <= 0.05, f"measured={context['interface_clearance_per_side_mm']:.5f}; parameter={P.interface_clearance_per_side:.5f} mm/side")
    add_check(dimensional_checks, "Backward installation prevented", context["backward_rotated_plug_outside_opening_mm3"] > 0.10, f"180° rotated plug protrudes {context['backward_rotated_plug_outside_opening_mm3']:.5f} mm³ outside opening")
    add_check(dimensional_checks, "Mast height envelope", abs(context["island_height_above_deck_mm"] - P.mast_top_height) <= 0.05, f"{context['island_height_above_deck_mm']:.5f} mm above deck; reference={P.island_reference_height_above_deck:.5f} mm")
    add_check(dimensional_checks, "Structural wall minimum", P.minimum_structural_wall >= 1.20 and P.foundation_flange_height >= 1.20, f"structural={P.minimum_structural_wall:.2f}; flange={P.foundation_flange_height:.2f} mm")
    add_check(dimensional_checks, "Mast / antenna thickness", P.minimum_freestanding_mast >= 0.80 and P.preferred_fragile_mast >= 1.00 and P.minimum_antenna >= 0.60, f"mast={P.minimum_freestanding_mast:.2f}; preferred={P.preferred_fragile_mast:.2f}; antenna={P.minimum_antenna:.2f} mm")
    add_check(dimensional_checks, "Raised / engraved detail rules", P.minimum_raised_width >= 0.50 and P.minimum_raised_height >= 0.35 and P.minimum_engraved_width >= 0.50 and P.minimum_engraved_depth >= 0.30, f"raised={P.minimum_raised_width:.2f}×{P.minimum_raised_height:.2f}; engraved={P.minimum_engraved_width:.2f}×{P.minimum_engraved_depth:.2f} mm")
    add_check(dimensional_checks, "Railing / radar rib rules", P.minimum_railing >= 0.60 and P.radar_rib_width >= 0.50 and P.radar_rib_height >= 0.35, f"railing={P.minimum_railing:.2f}; radar rib={P.radar_rib_width:.2f}×{P.radar_rib_height:.2f} mm")
    coupon_3mf = three_mf_results["Island_Interface_Test_Coupon.3mf"]
    add_check(dimensional_checks, "Physical coupon envelope", coupon_3mf["bounds_mm"][0] <= 60 and coupon_3mf["bounds_mm"][1] <= 60 and coupon_3mf["bounds_mm"][2] <= 25, f"{coupon_3mf['bounds_mm']} mm; limit 60 × 60 × 25 mm")
    add_check(dimensional_checks, "No trapped unsupported interface cavity", P.interface_plug_depth > 0 and P.glue_channel_width >= 0.50, "solid plug + through opening + four perimeter-open glue channels")
    add_check(dimensional_checks, "Production part envelope", all(max(item["print_size_mm"]) <= 240.0 + 1.0e-6 for item in MANIFEST["parts"]), f"maximum={max(max(item['print_size_mm']) for item in MANIFEST['parts']):.3f} mm")

    interference = interference_context()
    add_check(interference_checks, "Integrated unintended overlap", interference["overlap_mm3"]["all"] <= 0.10, f"{interference['overlap_mm3']['all']:.9f} mm³; maximum 0.10 mm³")
    add_check(interference_checks, "Elevators unobstructed", interference["overlap_mm3"]["elevators"] <= 0.10, f"overlap={interference['overlap_mm3']['elevators']:.9f} mm³; nearest axis-aligned gap={interference['nearest_elevator_axis_gap_mm']:.3f} mm")
    add_check(interference_checks, "Deck markings/catapults/wires unobstructed", interference["overlap_mm3"]["markings"] <= 0.10, f"overlap={interference['overlap_mm3']['markings']:.9f} mm³")
    add_check(interference_checks, "Twelve Milestone 2 landing pads unobstructed", interference["overlap_mm3"]["landing_pads"] <= 0.10, f"overlap={interference['overlap_mm3']['landing_pads']:.9f} mm³")
    add_check(interference_checks, "Approved deck solids clear interface", interference["overlap_mm3"]["deck_modules"] <= 0.10, f"overlap={interference['overlap_mm3']['deck_modules']:.9f} mm³")
    seam_clear = min(abs(bound - seam) for bound in interference["island_x_bounds_mm"] for seam in interference["deck_seams_x_mm"])
    add_check(interference_checks, "No coincident island/deck seam", seam_clear > 10.0, f"island x={interference['island_x_bounds_mm']}; deck seams={interference['deck_seams_x_mm']}; nearest={seam_clear:.3f} mm")

    mesh_overall = all(check["status"] == "PASS" for check in mesh_checks)
    dimensional_overall = all(check["status"] == "PASS" for check in dimensional_checks)
    interference_overall = all(check["status"] == "PASS" for check in interference_checks)
    mesh_report = {
        "generated_utc": generated,
        "overall_status": "PASS" if mesh_overall else "FAIL",
        "freecad_version": ".".join(App.Version()[:3]),
        "checks": mesh_checks,
        "stl_files": stl_results,
        "three_mf_files": three_mf_results,
        "fcstd_shapes": fcstd_records,
        "step_round_trip": {"island": island_step, "coupon": coupon_step, "review": review_step},
        "pdfs": pdfs,
    }
    dimensional_report = {"generated_utc": generated, "overall_status": "PASS" if dimensional_overall else "FAIL", "checks": dimensional_checks, "measurements": context, "parameters_mm": MANIFEST["parameters_mm"]}
    interference_report = {"generated_utc": generated, "overall_status": "PASS" if interference_overall else "FAIL", "checks": interference_checks, "measurements": interference, "method": "OpenCascade common-volume checks between approved Milestone 2 BReps and all assembled island production BReps"}
    (QA / "Mesh_Validation.json").write_text(json.dumps(mesh_report, indent=2) + "\n", encoding="utf-8")
    (QA / "Dimensional_QA.json").write_text(json.dumps(dimensional_report, indent=2) + "\n", encoding="utf-8")
    (QA / "Interference_Report.json").write_text(json.dumps(interference_report, indent=2) + "\n", encoding="utf-8")
    (QA / "Mesh_Validation.md").write_text(markdown_report("Milestone 3 Mesh / Geometry Validation", mesh_overall, mesh_checks, ["", "## Checks run", "", "Binary STL edge incidence, normals, degenerates, signed volume, z=0, print envelope; named-object 3MF ZIP/XML/CRC/index/material checks; FreeCAD Shape.check(True), strict BOPCheck, STEP round-trip, PDF/PNG structure, immutable-input hashes, production-output hashes, source-mesh exclusion, and Bambu Studio manifold checks."]), encoding="utf-8")
    (QA / "Dimensional_QA.md").write_text(markdown_report("Milestone 3 Dimensional QA", dimensional_overall, dimensional_checks), encoding="utf-8")
    (QA / "Interference_Report.md").write_text(markdown_report("Milestone 3 Hull–Deck–Island Interference Report", interference_overall, interference_checks, ["", "The approved hull/deck/interface-pad BReps are loaded read-only. Touching assembly faces are accepted only when common volume remains below 0.10 mm³; no island-to-baseline overlap is preclassified as intended."]), encoding="utf-8")
    commands = [
        "# Milestone 3 Validation Commands", "", f"Generated UTC: {generated}", f"FreeCAD: {'.'.join(App.Version()[:3])}", "Bambu Studio: 02.07.01.62", "", "```sh",
        "python3 Project/Island/Scripts/audit_island_reference.py",
        "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \"globals()['__file__']='Project/Island/Scripts/build_island.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))\"",
        "python3 Project/Island/Scripts/render_island.py",
        "/Users/Yun.Hu@blueshieldca.com/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 Project/Island/Scripts/generate_island_documents.py",
        "python3 Project/Island/Scripts/run_bambu_island_checks.py",
        "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \"globals()['__file__']='Project/Island/Scripts/validate_island.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))\"",
        "```",
    ]
    (QA / "Validation_Commands.md").write_text("\n".join(commands) + "\n", encoding="utf-8")
    print(json.dumps({"mesh": mesh_report["overall_status"], "dimensional": dimensional_report["overall_status"], "interference": interference_report["overall_status"], "mesh_checks": len(mesh_checks), "dimensional_checks": len(dimensional_checks), "interference_checks": len(interference_checks)}, indent=2))
    if not (mesh_overall and dimensional_overall and interference_overall):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
