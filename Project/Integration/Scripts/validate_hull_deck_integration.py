#!/usr/bin/env python3
"""Deterministic mandatory QA for CVN-69 Milestone 2 integration."""

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
INTEGRATION = SCRIPT.parents[1]
PROJECT = INTEGRATION.parent
REPO = PROJECT.parent
QA = INTEGRATION / "QA"
MANIFEST_PATH = QA / "build_manifest.json"
sys.path.insert(0, str(INTEGRATION / "CAD" / "Python"))
from integration_parameters import make_parameters  # noqa: E402


P = make_parameters()
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


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
    normals = []
    triangles = []
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
    degenerate = 0
    normal_mismatch = 0
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
        cross = (
            u[1] * w[2] - u[2] * w[1],
            u[2] * w[0] - u[0] * w[2],
            u[0] * w[1] - u[1] * w[0],
        )
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
        "normals_consistent": normal_mismatch == 0 and abs(signed_volume) > 1.0e-9,
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
    vertex_count = 0
    triangle_count = 0
    minimum = [float("inf")] * 3
    maximum = [float("-inf")] * 3
    for mesh in root.findall(".//m:mesh", ns):
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
    objects = root.findall(".//m:object", ns)
    build_items = root.findall(".//m:build/m:item", ns)
    return {
        "zip_crc_ok": crc_member is None,
        "missing_members": missing,
        "objects": len(objects),
        "build_items": len(build_items),
        "vertices": vertex_count,
        "triangles": triangle_count,
        "invalid_triangle_indices": invalid_indices,
        "min_mm": [round(value, 5) for value in minimum],
        "bounds_mm": [round(maximum[axis] - minimum[axis], 5) for axis in range(3)],
        "valid": crc_member is None and not missing and bool(objects) and bool(build_items) and invalid_indices == 0,
    }


def precise_bounds(shape):
    points, _faces = shape.tessellate(P.tessellation_deflection)
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    zs = [point.z for point in points]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def png_dimensions(path: Path):
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError(f"Not a PNG: {path}")
    return struct.unpack(">II", data[16:24])


def pdf_metrics(path: Path):
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "header_ok": data.startswith(b"%PDF-"),
        "eof_ok": b"%%EOF" in data[-1024:],
        "pages": len(re.findall(rb"/Type\s*/Page\b", data)),
    }


def add_check(checks, name, passed, evidence):
    checks.append({"name": name, "status": "PASS" if passed else "FAIL", "evidence": evidence})


def polygon_prism(points, z0, height):
    vectors = [App.Vector(float(x), float(y), float(z0)) for x, y in points]
    wire = Part.makePolygon(vectors + [vectors[0]])
    return Part.Face(wire).extrude(App.Vector(0, 0, float(height)))


def validate_fcstd(path: Path):
    doc = App.openDocument(str(path))
    records = []
    context = {}
    try:
        doc.recompute()
        objects = [obj for obj in doc.Objects if hasattr(obj, "IntegrationRole") and hasattr(obj, "Shape") and not obj.Shape.isNull()]
        production = [obj for obj in objects if obj.IntegrationRole != "test_coupon"]
        coupons = [obj for obj in objects if obj.IntegrationRole == "test_coupon"]
        for obj in objects:
            messages = []
            try:
                obj.Shape.check(True)
            except ValueError as exc:
                messages = [line.strip() for line in str(exc).splitlines() if line.strip()]
            records.append(
                {
                    "name": obj.Name,
                    "role": obj.IntegrationRole,
                    "valid": bool(obj.Shape.isValid()),
                    "closed": bool(obj.Shape.isClosed()),
                    "solids": len(obj.Shape.Solids),
                    "strict_messages": messages,
                    "self_intersections": sum("SelfIntersect" in line for line in messages),
                }
            )
        hull_modules = [obj for obj in production if obj.IntegrationRole == "hull_module"]
        deck_modules = [obj for obj in production if obj.IntegrationRole == "deck_module"]
        pads = [obj for obj in production if obj.IntegrationRole == "interface_pad"]
        elevators = [obj for obj in production if obj.IntegrationRole == "elevator"]

        hull_deck_overlap = sum(hull.Shape.common(deck.Shape).Volume for hull in hull_modules for deck in deck_modules)
        pad_hull_overlap = sum(pad.Shape.common(hull.Shape).Volume for pad in pads for hull in hull_modules)
        pad_deck_overlap = sum(pad.Shape.common(deck.Shape).Volume for pad in pads for deck in deck_modules)
        elevator_hull_overlap = sum(elevator.Shape.common(hull.Shape).Volume for elevator in elevators for hull in hull_modules)
        elevator_pad_overlap = sum(elevator.Shape.common(pad.Shape).Volume for elevator in elevators for pad in pads)
        elevator_deck_overlap = sum(elevator.Shape.common(deck.Shape).Volume for elevator in elevators for deck in deck_modules)

        island_points = [(P.deck_x_to_authoritative(x), y) for x, y in P.deck.island_opening]
        island_clearance = polygon_prism(island_points, P.deck_base_z + 0.0001, P.deck.deck_thickness + 1.0)
        island_obstruction = sum(island_clearance.common(obj.Shape).Volume for obj in hull_modules + deck_modules + pads)

        hull_bounds = [precise_bounds(obj.Shape) for obj in hull_modules]
        deck_bounds = [precise_bounds(obj.Shape) for obj in deck_modules]
        hull_min_x = min(bounds[0] for bounds in hull_bounds)
        hull_max_x = max(bounds[3] for bounds in hull_bounds)
        deck_min_x = min(bounds[0] for bounds in deck_bounds)
        deck_max_x = max(bounds[3] for bounds in deck_bounds)
        hull_top = max(bounds[5] for bounds in hull_bounds)
        deck_bottoms = [bounds[2] for bounds in deck_bounds]
        deck_collective_y = [min(bounds[1] for bounds in deck_bounds), max(bounds[4] for bounds in deck_bounds)]

        hull_tool = doc.getObject("Hull_Interface_Socket_Tools").Shape
        deck_tool = doc.getObject("Deck_Interface_Socket_Tools").Shape
        hull_socket_sizes = [[solid.BoundBox.XLength, solid.BoundBox.YLength, solid.BoundBox.ZLength] for solid in hull_tool.Solids]
        deck_socket_sizes = [[solid.BoundBox.XLength, solid.BoundBox.YLength, solid.BoundBox.ZLength] for solid in deck_tool.Solids]
        measured_clearance = (hull_socket_sizes[0][0] - P.pad_length) / 2.0

        centerline = doc.getObject("Authoritative_Centerline").Shape.BoundBox
        context = {
            "production_part_count": len(production),
            "coupon_part_count": len(coupons),
            "hull_deck_unintended_overlap_mm3": float(hull_deck_overlap),
            "pad_hull_overlap_mm3": float(pad_hull_overlap),
            "pad_deck_overlap_mm3": float(pad_deck_overlap),
            "elevator_hull_overlap_mm3": float(elevator_hull_overlap),
            "elevator_pad_overlap_mm3": float(elevator_pad_overlap),
            "elevator_deck_overlap_mm3": float(elevator_deck_overlap),
            "island_opening_obstruction_mm3": float(island_obstruction),
            "hull_length_mm": float(hull_max_x - hull_min_x),
            "deck_length_mm": float(deck_max_x - deck_min_x),
            "assembled_length_mm": float(max(hull_max_x, deck_max_x) - min(hull_min_x, deck_min_x)),
            "bow_datum_error_mm": float(abs(hull_min_x - deck_min_x)),
            "stern_datum_error_mm": float(abs(hull_max_x - deck_max_x)),
            "centerline_error_mm": float(max(abs(centerline.YMin), abs(centerline.YMax))),
            "seating_gap_mm": float(min(deck_bottoms) - hull_top),
            "deck_base_spread_mm": float(max(deck_bottoms) - min(deck_bottoms)),
            "deck_collective_y_mm": deck_collective_y,
            "hull_socket_count": len(hull_socket_sizes),
            "deck_socket_count": len(deck_socket_sizes),
            "hull_socket_size_mm": hull_socket_sizes[0],
            "deck_socket_size_mm": deck_socket_sizes[0],
            "measured_clearance_per_side_mm": float(measured_clearance),
        }
    finally:
        App.closeDocument(doc.Name)
    return records, context


def validate_step(path: Path, expected_solids: int):
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
    lines = [
        f"# {title}",
        "",
        f"Overall status: **{'PASS' if overall else 'FAIL'}**",
        "",
        "| Check | Status | Evidence |",
        "|---|---:|---|",
    ]
    for check in checks:
        evidence = str(check["evidence"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {check['status']} | {evidence} |")
    if sections:
        lines.extend(sections)
    return "\n".join(lines) + "\n"


def main():
    generated = datetime.now(timezone.utc).isoformat()
    mesh_checks = []
    dimensional_checks = []
    interference_checks = []

    stl_results = {}
    for path in sorted((INTEGRATION / "STL").glob("*.stl")):
        metrics = mesh_metrics(path)
        stl_results[path.name] = metrics
        passed = (
            metrics["watertight"]
            and metrics["manifold"]
            and metrics["components"] == 1
            and metrics["degenerate_facets"] == 0
            and metrics["normals_consistent"]
            and abs(metrics["min_mm"][2]) <= 0.01
            and max(metrics["bounds_mm"]) <= 240.0
        )
        add_check(
            mesh_checks,
            f"STL — {path.name}",
            passed,
            f"{metrics['facets']} facets; {metrics['components']} component; {metrics['non_two_incident_edges']} bad edges; bounds {metrics['bounds_mm']} mm; min z {metrics['min_mm'][2]:.5f}",
        )

    three_mf_results = {}
    for path in sorted((INTEGRATION / "3MF").glob("*.3mf")):
        result = check_3mf(path)
        three_mf_results[path.name] = result
        is_assembly = path.name == "CVN69_Hull_Deck_Assembly.3mf"
        envelope_ok = is_assembly or (max(result["bounds_mm"]) <= 240.0 and abs(result["min_mm"][2]) <= 0.01)
        add_check(
            mesh_checks,
            f"3MF — {path.name}",
            result["valid"] and envelope_ok,
            f"CRC={result['zip_crc_ok']}; {result['triangles']} triangles; bounds {result['bounds_mm']} mm" + ("; assembly reference" if is_assembly else "; printable envelope"),
        )

    fcstd_path = INTEGRATION / "CAD" / "FreeCAD" / "CVN69_Hull_Deck_Integration.FCStd"
    fcstd_records, context = validate_fcstd(fcstd_path)
    add_check(
        mesh_checks,
        "FreeCAD Shape.check(True) / strict BOPCheck",
        len(fcstd_records) == 57 and all(item["valid"] and item["closed"] and item["solids"] == 1 and item["self_intersections"] == 0 for item in fcstd_records),
        f"{len(fcstd_records)} production/coupon BReps checked; zero self-intersections",
    )

    assembly_step = validate_step(INTEGRATION / "STEP" / "CVN69_Hull_Deck_Assembly.step", 55)
    coupon_step = validate_step(INTEGRATION / "STEP" / "Interface_Test_Coupon.step", 2)
    add_check(
        mesh_checks,
        "Assembly STEP round-trip",
        assembly_step["valid"] and assembly_step["solid_count"] == 55 and assembly_step["all_solids_closed"] and assembly_step["self_intersections"] == 0,
        f"{assembly_step['solid_count']} closed solids; {assembly_step['self_intersections']} self-intersections; {assembly_step['strict_message_count']} OCC diagnostics",
    )
    add_check(
        mesh_checks,
        "Coupon STEP round-trip",
        coupon_step["valid"] and coupon_step["solid_count"] == 2 and coupon_step["all_solids_closed"] and coupon_step["self_intersections"] == 0,
        f"{coupon_step['solid_count']} closed solids; {coupon_step['self_intersections']} self-intersections",
    )

    bambu = json.loads((QA / "BambuStudio_Validation.json").read_text(encoding="utf-8"))
    add_check(
        mesh_checks,
        "Bambu Studio independent import/manifold check",
        bambu["overall_status"] == "PASS" and bambu["files_checked"] == 62,
        f"Bambu Studio 02.07.01.62 loaded {bambu['files_checked']} STL/3MF exports; all reported manifold",
    )

    required_production = [
        "CAD/FreeCAD/CVN69_Hull_Deck_Integration.FCStd",
        "STEP/CVN69_Hull_Deck_Assembly.step",
        "STEP/Interface_Test_Coupon.step",
        "3MF/CVN69_Hull_Deck_Assembly.3mf",
        "3MF/Print_Plate_01_Hull.3mf",
        "3MF/Print_Plate_02_Deck.3mf",
        "3MF/Print_Plate_03_Details.3mf",
        "3MF/Interface_Test_Coupon.3mf",
        "Docs/Hull_Deck_Integration_Drawings.pdf",
        "Docs/Hull_Deck_Printing_Guide.pdf",
        "Docs/Interface_Test_Coupon_Instructions.pdf",
        "Docs/Material_Mapping.csv",
        "README.md",
        "Assembly/Glue_Only_Assembly.md",
        "CAD/Python/integration_parameters.py",
        "Scripts/build_hull_deck_integration.py",
        "Scripts/render_hull_deck_integration.py",
        "Scripts/run_bambu_integration_checks.py",
        "Scripts/generate_integration_documents.py",
        "Scripts/validate_hull_deck_integration.py",
        "Render/CVN69_Hull_Deck_Top.png",
        "Render/CVN69_Hull_Deck_Port.png",
        "Render/CVN69_Hull_Deck_Starboard.png",
        "Render/CVN69_Hull_Deck_Bow_Isometric.png",
        "Render/CVN69_Hull_Deck_Stern_Isometric.png",
        "Render/CVN69_Hull_Deck_Exploded.png",
        "Render/Section_Keyed_Landing_Pad.png",
        "Render/Section_Direct_Support.png",
    ] + [f"STL/{name}" for name in sorted(stl_results)]
    missing = [relative for relative in required_production if not (INTEGRATION / relative).exists()]
    add_check(mesh_checks, "Required production outputs exist", not missing, f"{len(required_production)} required outputs; missing={missing}")

    hash_mismatches = []
    for relative in required_production:
        path = INTEGRATION / relative
        expected = MANIFEST["outputs"].get(relative)
        if expected is None:
            hash_mismatches.append(f"not manifested {relative}")
        elif path.stat().st_size != expected["bytes"] or sha256(path) != expected["sha256"]:
            hash_mismatches.append(f"hash/size mismatch {relative}")
    add_check(mesh_checks, "Build-manifest production hashes", not hash_mismatches, f"{len(required_production)} byte-size/SHA-256 records match" if not hash_mismatches else "; ".join(hash_mismatches))

    approved_hash_mismatches = []
    for relative, expected in MANIFEST["approved_input_hashes"].items():
        if sha256(REPO / relative) != expected:
            approved_hash_mismatches.append(relative)
    add_check(mesh_checks, "Approved inputs unchanged", not approved_hash_mismatches, "Hull v0.1.0 and FlightDeck review hashes match build inputs" if not approved_hash_mismatches else str(approved_hash_mismatches))

    pdfs = {
        "drawings": pdf_metrics(INTEGRATION / "Docs" / "Hull_Deck_Integration_Drawings.pdf"),
        "printing": pdf_metrics(INTEGRATION / "Docs" / "Hull_Deck_Printing_Guide.pdf"),
        "coupon": pdf_metrics(INTEGRATION / "Docs" / "Interface_Test_Coupon_Instructions.pdf"),
    }
    add_check(
        mesh_checks,
        "PDF documentation structure",
        pdfs["drawings"]["header_ok"] and pdfs["drawings"]["eof_ok"] and pdfs["drawings"]["pages"] == 4
        and pdfs["printing"]["header_ok"] and pdfs["printing"]["eof_ok"] and pdfs["printing"]["pages"] == 5
        and pdfs["coupon"]["header_ok"] and pdfs["coupon"]["eof_ok"] and pdfs["coupon"]["pages"] == 1,
        str(pdfs),
    )

    render_names = [relative for relative in required_production if relative.startswith("Render/")]
    render_dimensions = {relative: png_dimensions(INTEGRATION / relative) for relative in render_names}
    add_check(mesh_checks, "All required renders", all(width >= 2000 and height >= 1200 for width, height in render_dimensions.values()), str(render_dimensions))

    # Mandatory dimensional checks.
    add_check(dimensional_checks, "Assembled overall length", abs(context["assembled_length_mm"] - 476.0) <= 0.05, f"{context['assembled_length_mm']:.5f} mm; tolerance ±0.05 mm")
    add_check(dimensional_checks, "Hull/deck centerline coincidence", context["centerline_error_mm"] <= 0.05, f"error {context['centerline_error_mm']:.5f} mm")
    add_check(dimensional_checks, "Bow datum coincidence", context["bow_datum_error_mm"] <= 0.05, f"error {context['bow_datum_error_mm']:.5f} mm")
    add_check(dimensional_checks, "Stern datum coincidence", context["stern_datum_error_mm"] <= 0.05, f"error {context['stern_datum_error_mm']:.5f} mm")
    add_check(dimensional_checks, "Deck elevation consistency", context["deck_base_spread_mm"] <= 0.01 and abs(context["seating_gap_mm"] - P.seating_gap) <= 0.01, f"base spread {context['deck_base_spread_mm']:.5f} mm; seating gap {context['seating_gap_mm']:.5f} mm")
    add_check(dimensional_checks, "Nominal seating gap", abs(context["seating_gap_mm"]) <= 0.30, f"{context['seating_gap_mm']:.5f} mm; maximum 0.30 mm")
    add_check(dimensional_checks, "Interface structural thickness", min(P.pad_hull_insertion, P.pad_deck_insertion, P.deck_top_skin_over_socket) >= 1.20, f"minimum {min(P.pad_hull_insertion, P.pad_deck_insertion, P.deck_top_skin_over_socket):.2f} mm")
    add_check(dimensional_checks, "Glue clearance", abs(context["measured_clearance_per_side_mm"] - P.interface_clearance_per_side) <= 0.05, f"measured {context['measured_clearance_per_side_mm']:.3f} mm/side; parameter {P.interface_clearance_per_side:.3f}")
    seam_offsets = [min(abs(deck - hull) for hull in P.hull_module_seams) for deck in P.deck_authoritative_seams]
    add_check(dimensional_checks, "Staggered module-seam compatibility", min(seam_offsets) >= 10.0, f"deck seams {P.deck_authoritative_seams}; hull seams {P.hull_module_seams}; nearest offsets {[round(value, 3) for value in seam_offsets]} mm")
    add_check(dimensional_checks, "Interface socket counts", context["hull_socket_count"] == 12 and context["deck_socket_count"] == 12, f"hull={context['hull_socket_count']}; deck={context['deck_socket_count']}")
    add_check(dimensional_checks, "Deck external planform preserved", abs(context["deck_length_mm"] - P.deck.overall_length) <= 0.01 and all(abs(a - b) <= 0.01 for a, b in zip(context["deck_collective_y_mm"], (-36.7, 37.0))), f"length {context['deck_length_mm']:.3f} mm; y {context['deck_collective_y_mm']}")
    add_check(dimensional_checks, "Hull external length preserved", abs(context["hull_length_mm"] - P.hull.overall_length) <= 0.01, f"length {context['hull_length_mm']:.3f} mm")
    coupon_3mf = three_mf_results["Interface_Test_Coupon.3mf"]
    add_check(dimensional_checks, "Physical coupon envelope", coupon_3mf["bounds_mm"][0] <= 60 and coupon_3mf["bounds_mm"][1] <= 60 and coupon_3mf["bounds_mm"][2] <= 20, f"{coupon_3mf['bounds_mm']} mm; limit 60 × 60 × 20 mm")
    add_check(dimensional_checks, "No trapped unsupported interface cavity", P.socket_width <= 6.50 and P.socket_opening_allowance > 0.0, f"open underside/top sockets; maximum roof span {P.socket_width:.2f} mm")

    # Mandatory interference checks.
    add_check(interference_checks, "Hull/deck unintended overlap", context["hull_deck_unintended_overlap_mm3"] <= 0.10, f"{context['hull_deck_unintended_overlap_mm3']:.8f} mm³; maximum 0.10 mm³")
    add_check(interference_checks, "Pads clear hull sockets", context["pad_hull_overlap_mm3"] <= 0.10, f"unintended overlap {context['pad_hull_overlap_mm3']:.8f} mm³")
    add_check(interference_checks, "Pads clear deck sockets", context["pad_deck_overlap_mm3"] <= 0.10, f"unintended overlap {context['pad_deck_overlap_mm3']:.8f} mm³; tip clearance {P.vertical_pad_tip_clearance:.2f} mm")
    elevator_total = context["elevator_hull_overlap_mm3"] + context["elevator_pad_overlap_mm3"] + context["elevator_deck_overlap_mm3"]
    add_check(interference_checks, "Elevators removable and unobstructed", elevator_total <= 0.10, f"hull={context['elevator_hull_overlap_mm3']:.8f}; pads={context['elevator_pad_overlap_mm3']:.8f}; deck/shelf={context['elevator_deck_overlap_mm3']:.8f} mm³")
    add_check(interference_checks, "Island opening unobstructed", context["island_opening_obstruction_mm3"] <= 0.10, f"obstruction above seating datum {context['island_opening_obstruction_mm3']:.8f} mm³")

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
        "assembly_step": assembly_step,
        "coupon_step": coupon_step,
        "pdfs": pdfs,
    }
    dimensional_report = {
        "generated_utc": generated,
        "overall_status": "PASS" if dimensional_overall else "FAIL",
        "checks": dimensional_checks,
        "measurements": context,
        "parameters_mm": MANIFEST["parameters_mm"],
    }
    interference_report = {
        "generated_utc": generated,
        "overall_status": "PASS" if interference_overall else "FAIL",
        "checks": interference_checks,
        "measurements": context,
        "method": "OpenCascade common-volume checks between production BReps in assembled coordinates",
    }
    (QA / "Mesh_Validation.json").write_text(json.dumps(mesh_report, indent=2) + "\n", encoding="utf-8")
    (QA / "Dimensional_QA.json").write_text(json.dumps(dimensional_report, indent=2) + "\n", encoding="utf-8")
    (QA / "Interference_Report.json").write_text(json.dumps(interference_report, indent=2) + "\n", encoding="utf-8")
    (QA / "Mesh_Validation.md").write_text(
        markdown_report(
            "Milestone 2 Mesh / Geometry Validation",
            mesh_overall,
            mesh_checks,
            [
                "",
                "## Checks run",
                "",
                "Binary STL structure, two-edge incidence, connected components, degenerates, normals, signed volume, print z=0, 240 mm envelope, 3MF ZIP/XML/CRC/index checks, FreeCAD Shape.check(True), strict BOPCheck, STEP round-trip, PDF/PNG structure, approved-input hashes, production-output hashes, and Bambu Studio import/manifold checks.",
            ],
        ),
        encoding="utf-8",
    )
    (QA / "Dimensional_QA.md").write_text(markdown_report("Milestone 2 Dimensional QA", dimensional_overall, dimensional_checks), encoding="utf-8")
    (QA / "Interference_Report.md").write_text(
        markdown_report(
            "Milestone 2 Hull–Deck Interference Report",
            interference_overall,
            interference_checks,
            [
                "",
                "## Interface interpretation",
                "",
                "- Hull and deck broad faces meet at z = 31.50 mm; common-volume overlap remains zero.",
                "- Interface pads occupy clearance-controlled hull and deck sockets and are not counted as intended interference.",
                "- Island clearance is tested above the seating datum, so the future island opening remains free of deck material and integration hardware.",
                "- Elevator plates are checked against hull modules, interface pads, and deck shelf geometry.",
            ],
        ),
        encoding="utf-8",
    )

    command_lines = [
        "# Milestone 2 Validation Commands",
        "",
        f"Generated UTC: {generated}",
        f"FreeCAD: {'.'.join(App.Version()[:3])}",
        "Bambu Studio: 02.07.01.62",
        "",
        "```sh",
        "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \"globals()['__file__']='Project/Integration/Scripts/build_hull_deck_integration.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))\"",
        "python3 Project/Integration/Scripts/render_hull_deck_integration.py",
        "python3 Project/Integration/Scripts/run_bambu_integration_checks.py",
        "/Users/Yun.Hu@blueshieldca.com/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 Project/Integration/Scripts/generate_integration_documents.py",
        "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \"globals()['__file__']='Project/Integration/Scripts/validate_hull_deck_integration.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))\"",
        "```",
    ]
    (QA / "Validation_Commands.md").write_text("\n".join(command_lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "mesh": mesh_report["overall_status"],
                "dimensional": dimensional_report["overall_status"],
                "interference": interference_report["overall_status"],
                "mesh_checks": len(mesh_checks),
                "dimensional_checks": len(dimensional_checks),
                "interference_checks": len(interference_checks),
            },
            indent=2,
        )
    )
    if not (mesh_overall and dimensional_overall and interference_overall):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
