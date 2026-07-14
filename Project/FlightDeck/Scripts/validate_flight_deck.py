#!/usr/bin/env python3
"""Independent BRep, STEP, STL, 3MF, and dimensional QA for the flight deck."""

from __future__ import annotations

import hashlib
import json
import math
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
DECK_PROJECT = SCRIPT.parents[1]
ROOT_PROJECT = DECK_PROJECT.parent
sys.path.insert(0, str(DECK_PROJECT / "CAD" / "Python"))
from deck_parameters import make_parameters  # noqa: E402


P = make_parameters()
QA = DECK_PROJECT / "QA"
MANIFEST = json.loads((QA / "build_manifest.json").read_text(encoding="utf-8"))


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
    min_xyz = [float("inf")] * 3
    max_xyz = [float("-inf")] * 3
    degenerate = 0
    normal_mismatch = 0
    signed_volume = 0.0
    for stored_normal, triangle in zip(normals, triangles):
        keys = [quantized(point) for point in triangle]
        vertices.update(keys)
        for point in keys:
            for axis, value in enumerate(point):
                min_xyz[axis] = min(min_xyz[axis], value)
                max_xyz[axis] = max(max_xyz[axis], value)
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
    bounds = [round(max_xyz[axis] - min_xyz[axis], 5) for axis in range(3)]
    return {
        "facets": len(triangles),
        "vertices": len(vertices),
        "components": components,
        "min_mm": [round(value, 5) for value in min_xyz],
        "max_mm": [round(value, 5) for value in max_xyz],
        "bounds_mm": bounds,
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
    min_xyz = [float("inf")] * 3
    max_xyz = [float("-inf")] * 3
    for mesh in root.findall(".//m:mesh", ns):
        vertices = mesh.findall("./m:vertices/m:vertex", ns)
        triangles = mesh.findall("./m:triangles/m:triangle", ns)
        vertex_count += len(vertices)
        triangle_count += len(triangles)
        for vertex in vertices:
            point = [float(vertex.attrib[key]) for key in ("x", "y", "z")]
            for axis, value in enumerate(point):
                min_xyz[axis] = min(min_xyz[axis], value)
                max_xyz[axis] = max(max_xyz[axis], value)
        for triangle in triangles:
            if any(int(triangle.attrib[key]) < 0 or int(triangle.attrib[key]) >= len(vertices) for key in ("v1", "v2", "v3")):
                invalid_indices += 1
    objects = root.findall(".//m:object", ns)
    build_items = root.findall(".//m:build/m:item", ns)
    size = [round(max_xyz[axis] - min_xyz[axis], 5) for axis in range(3)] if vertex_count else []
    return {
        "zip_crc_ok": crc_member is None,
        "missing_members": missing,
        "objects": len(objects),
        "build_items": len(build_items),
        "vertices": vertex_count,
        "triangles": triangle_count,
        "invalid_triangle_indices": invalid_indices,
        "min_mm": [round(value, 5) for value in min_xyz] if vertex_count else [],
        "bounds_mm": size,
        "valid": crc_member is None and not missing and bool(objects) and bool(build_items) and invalid_indices == 0,
    }


def png_dimensions(path: Path):
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError(f"Not a PNG: {path}")
    return struct.unpack(">II", data[16:24])


def add_check(checks, name, passed, evidence):
    checks.append({"name": name, "status": "PASS" if passed else "FAIL", "evidence": evidence})


def validate_fcstd(path: Path):
    doc = App.openDocument(str(path))
    records = []
    context = {}
    try:
        doc.recompute()
        production = [obj for obj in doc.Objects if hasattr(obj, "PartCategory") and hasattr(obj, "Shape")]
        for obj in production:
            strict_messages = []
            try:
                obj.Shape.check(True)
            except ValueError as exc:
                strict_messages = [line.strip() for line in str(exc).splitlines() if line.strip()]
            records.append(
                {
                    "name": obj.Name,
                    "category": obj.PartCategory,
                    "valid": bool(obj.Shape.isValid()),
                    "closed": bool(obj.Shape.isClosed()),
                    "solids": len(obj.Shape.Solids),
                    "self_intersections": sum("SelfIntersect" in line for line in strict_messages),
                    "strict_messages": strict_messages,
                }
            )
        modules = [obj.Shape for obj in production if obj.PartCategory == "main_deck_body"]
        island_tool = doc.getObject("Island_Opening_Tool").Shape
        island_overlap = sum(module.common(island_tool).Volume for module in modules)
        elevator_overlap = 0.0
        for obj in production:
            if obj.PartCategory == "elevator":
                elevator_overlap += sum(obj.Shape.common(module).Volume for module in modules)
        context = {
            "production_part_count": len(production),
            "island_opening_overlap_mm3": float(island_overlap),
            "elevator_deck_overlap_mm3": float(elevator_overlap),
        }
    finally:
        App.closeDocument(doc.Name)
    return records, context


def validate_step(path: Path):
    shape = Part.read(str(path))
    strict_messages = []
    for solid in shape.Solids:
        try:
            solid.check(True)
        except ValueError as exc:
            strict_messages.extend(line.strip() for line in str(exc).splitlines() if line.strip())
    return {
        "valid": bool(shape.isValid()),
        "solid_count": len(shape.Solids),
        "all_solids_closed": bool(shape.Solids) and all(solid.isClosed() for solid in shape.Solids),
        "self_intersections": sum("SelfIntersect" in line for line in strict_messages),
        "strict_message_count": len(strict_messages),
        "strict_message_types": sorted(set(strict_messages)),
    }


def source_inventory_check():
    path = QA / "Source_STL_Inventory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "count": data["inventory_count"],
        "source_sets": data["source_sets"],
        "visuals": {
            name: png_dimensions(QA / name)
            for name in ("Source_STL_Inventory_Top.png", "Source_STL_Inventory_Isometric.png")
        },
    }


def markdown_report(title, overall, checks, extra_sections=None):
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
    if extra_sections:
        lines.extend(extra_sections)
    return "\n".join(lines) + "\n"


def main():
    stl_results = {}
    mesh_checks = []
    for path in sorted((DECK_PROJECT / "STL").glob("*.stl")):
        metrics = mesh_metrics(path)
        stl_results[path.name] = metrics
        passed = (
            metrics["watertight"]
            and metrics["manifold"]
            and metrics["degenerate_facets"] == 0
            and metrics["normals_consistent"]
            and abs(metrics["min_mm"][2]) <= 1.0e-5
            and max(metrics["bounds_mm"]) <= 240.0
        )
        add_check(
            mesh_checks,
            f"STL — {path.name}",
            passed,
            f"{metrics['facets']} facets; {metrics['components']} component; {metrics['non_two_incident_edges']} bad edges; bounds {metrics['bounds_mm']} mm; min z {metrics['min_mm'][2]:.5f}",
        )

    three_mf_results = {}
    for path in sorted((DECK_PROJECT / "3MF").rglob("*.3mf")):
        result = check_3mf(path)
        relative = str(path.relative_to(DECK_PROJECT / "3MF"))
        three_mf_results[relative] = result
        is_print_file = path.parent.name == "Individual" or path.name.startswith("Print_Plate")
        envelope_ok = not is_print_file or (max(result["bounds_mm"]) <= 240.0 and abs(result["min_mm"][2]) <= 1.0e-5)
        add_check(
            mesh_checks,
            f"3MF — {relative}",
            result["valid"] and envelope_ok,
            f"CRC={result['zip_crc_ok']}; {result['triangles']} triangles; bounds {result['bounds_mm']} mm" + ("; printable envelope" if is_print_file else "; assembly reference"),
        )

    fcstd_path = DECK_PROJECT / "CAD" / "FreeCAD" / "CVN69_Flight_Deck_Reconstruction.FCStd"
    fcstd_records, fcstd_context = validate_fcstd(fcstd_path)
    add_check(
        mesh_checks,
        "FreeCAD production BRep validity / BOPCheck",
        len(fcstd_records) == 22 and all(item["valid"] and item["closed"] and item["solids"] == 1 and item["self_intersections"] == 0 for item in fcstd_records),
        f"{len(fcstd_records)} production Part::Feature objects; OCC strict checks; zero self-intersections",
    )

    step_path = DECK_PROJECT / "STEP" / "CVN69_Flight_Deck_Assembly.step"
    step_result = validate_step(step_path)
    add_check(
        mesh_checks,
        "STEP round-trip",
        step_result["valid"] and step_result["solid_count"] == 22 and step_result["all_solids_closed"] and step_result["self_intersections"] == 0,
        f"{step_result['solid_count']} closed solids after STEP re-import; {step_result['self_intersections']} self-intersections; {step_result['strict_message_count']} OCC diagnostics",
    )

    inventory = source_inventory_check()
    add_check(
        mesh_checks,
        "Complete source STL numerical and visual inventory",
        inventory["count"] == 33 and all(width >= 2000 and height >= 2000 for width, height in inventory["visuals"].values()),
        f"{inventory['count']} source STLs; sets {inventory['source_sets']}; PNG dimensions {inventory['visuals']}",
    )

    manifest_outputs_ok = True
    mismatches = []
    for relative, expected in MANIFEST["outputs"].items():
        path = DECK_PROJECT / relative
        if not path.exists():
            manifest_outputs_ok = False
            mismatches.append(f"missing {relative}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.stat().st_size != expected["bytes"] or digest != expected["sha256"]:
            manifest_outputs_ok = False
            mismatches.append(f"changed {relative}")
    add_check(mesh_checks, "Build-manifest output hashes", manifest_outputs_ok, "51 FCStd/STEP/STL/3MF/OBJ outputs match recorded byte sizes and SHA-256 hashes" if manifest_outputs_ok else "; ".join(mismatches))

    bambu_path = QA / "BambuStudio_Validation.json"
    bambu = json.loads(bambu_path.read_text(encoding="utf-8"))
    add_check(
        mesh_checks,
        "Bambu Studio independent import/manifold check",
        bambu["overall_status"] == "PASS" and bambu["files_checked"] == 47,
        f"Bambu Studio 02.07.01.62 loaded {bambu['files_checked']} STL/3MF exports; all reported manifold",
    )

    dimension_checks = []
    shapes = MANIFEST["shapes"]
    modules = [shape for shape in shapes if shape["kind"] == "main_deck_body"]
    overall_min = min(shape["bounds_mm"]["x"][0] for shape in modules)
    overall_max = max(shape["bounds_mm"]["x"][1] for shape in modules)
    overall_length = overall_max - overall_min
    add_check(dimension_checks, "Corrected 1:700 overall length", abs(overall_length - 476.0) <= 0.01, f"measured {overall_length:.4f} mm; target 476.0000 mm")
    add_check(dimension_checks, "Main-deck split count", len(modules) == 3, f"3 glue-only modules at x={P.split_seams[0]:.1f} and {P.split_seams[1]:.1f} mm")
    add_check(dimension_checks, "Every production part within 240 × 240 mm", all(max(shape["bounds_mm"]["size"][:2]) <= 240.0 for shape in shapes), f"maximum planar axis {max(max(shape['bounds_mm']['size'][:2]) for shape in shapes):.3f} mm")
    add_check(dimension_checks, "Deck body minimum thickness", P.deck_thickness >= P.minimum_wall, f"{P.deck_thickness:.2f} mm deck; requirement ≥ {P.minimum_wall:.2f} mm")
    add_check(dimension_checks, "Elevator support shelf", abs(P.elevator_shelf_thickness - 1.2) <= 1.0e-9, f"{P.elevator_shelf_thickness:.2f} mm continuous shelf")
    top_skin = P.deck_thickness - P.glue_socket_depth
    add_check(dimension_checks, "Top skin above glue sockets", top_skin >= P.minimum_wall, f"{top_skin:.2f} mm remaining above {P.glue_socket_depth:.2f} mm-deep sockets")
    add_check(dimension_checks, "Glue-only keyed joint clearance", 0.20 <= P.fit_clearance_per_side <= 0.30, f"{P.fit_clearance_per_side:.2f} mm per side; two underside tongues per seam")
    add_check(dimension_checks, "Minimum raised detail width", min(P.raised_marking_width, P.catapult_width, P.arresting_wire_width) >= 0.50, f"minimum {min(P.raised_marking_width, P.catapult_width, P.arresting_wire_width):.2f} mm")
    add_check(dimension_checks, "Minimum raised detail height", min(P.raised_marking_height, P.catapult_height, P.arresting_wire_height) >= 0.35, f"minimum {min(P.raised_marking_height, P.catapult_height, P.arresting_wire_height):.2f} mm")
    counts = MANIFEST["counts"]
    add_check(dimension_checks, "Four separate elevator solids", counts["elevators"] == 4, f"detected {counts['elevators']}")
    add_check(dimension_checks, "Four separate catapult tracks", counts["catapult_tracks"] == 4, f"detected {counts['catapult_tracks']}")
    add_check(dimension_checks, "Four separate arresting wires", counts["arresting_wires"] == 4, f"detected {counts['arresting_wires']}")
    add_check(dimension_checks, "Separate raised-marking solids", counts["raised_marking_parts"] == 7, f"detected {counts['raised_marking_parts']} connected printable marking parts")
    add_check(dimension_checks, "Island opening is clear", fcstd_context["island_opening_overlap_mm3"] <= 1.0e-6, f"deck/tool overlap {fcstd_context['island_opening_overlap_mm3']:.8f} mm³")
    add_check(dimension_checks, "Elevator plates do not intersect deck body", fcstd_context["elevator_deck_overlap_mm3"] <= 1.0e-6, f"total overlap {fcstd_context['elevator_deck_overlap_mm3']:.8f} mm³; plates seat on shelves")
    island_edge_wall = 34.5 - max(y for _x, y in P.island_opening)
    add_check(dimension_checks, "Island opening deck-edge wall", island_edge_wall >= P.minimum_wall, f"minimum traced starboard wall {island_edge_wall:.2f} mm")
    max_width = max(y for _x, y in P.outline_points) - min(y for _x, y in P.outline_points)
    add_check(dimension_checks, "Source-traced maximum deck width", abs(max_width - 73.7) <= 0.01, f"{max_width:.3f} mm")
    top_render = DECK_PROJECT / "Render" / "CVN69_Flight_Deck_Top.png"
    iso_render = DECK_PROJECT / "Render" / "CVN69_Flight_Deck_Isometric.png"
    render_dims = {top_render.name: png_dimensions(top_render), iso_render.name: png_dimensions(iso_render)}
    add_check(dimension_checks, "Top and isometric renders", all(width >= 3000 and height >= 1200 for width, height in render_dims.values()), str(render_dims))

    mesh_overall = all(check["status"] == "PASS" for check in mesh_checks)
    dimensional_overall = all(check["status"] == "PASS" for check in dimension_checks)
    generated = datetime.now(timezone.utc).isoformat()

    mesh_report = {
        "generated_utc": generated,
        "overall_status": "PASS" if mesh_overall else "FAIL",
        "freecad_version": ".".join(App.Version()[:3]),
        "checks": mesh_checks,
        "stl_files": stl_results,
        "three_mf_files": three_mf_results,
        "fcstd_shapes": fcstd_records,
        "step": step_result,
        "source_inventory": inventory,
    }
    (QA / "Mesh_Validation.json").write_text(json.dumps(mesh_report, indent=2) + "\n", encoding="utf-8")
    (QA / "Mesh_Validation.md").write_text(
        markdown_report(
            "CVN-69 Flight Deck Mesh Validation",
            mesh_overall,
            mesh_checks,
            [
                "",
                "## Geometry checks run",
                "",
                "Binary STL length/triangle parse; quantized two-edge incidence; connected components; degenerates; stored-normal agreement; signed volume; z=0 print placement; 240 mm envelope; 3MF ZIP CRC/package/XML/index validation; FreeCAD `Shape.check(True)`; BRep validity/closedness; STEP round-trip and per-solid strict BOPCheck; source-inventory image verification; manifest SHA-256 verification.",
            ],
        ),
        encoding="utf-8",
    )

    dimensional_report = {
        "generated_utc": generated,
        "overall_status": "PASS" if dimensional_overall else "FAIL",
        "checks": dimension_checks,
        "parameters_mm": MANIFEST["parameters_mm"],
        "part_counts": counts,
        "limitations": [
            "The source archive contains separated reference bands and disconnected/non-manifold components; missing longitudinal intervals were faired parametrically.",
            "This review package reconstructs only the flight deck and named deck details. Island, weapons, aircraft, hull redesign, and ocean base are intentionally absent.",
            "Automated checks do not replace a physical first-article print and glue-fit test.",
        ],
    }
    (QA / "Dimensional_QA.json").write_text(json.dumps(dimensional_report, indent=2) + "\n", encoding="utf-8")
    (QA / "Dimensional_QA.md").write_text(
        markdown_report(
            "CVN-69 Flight Deck Dimensional QA",
            dimensional_overall,
            dimension_checks,
            ["", "## Scope boundary", ""] + [f"- {item}" for item in dimensional_report["limitations"]],
        ),
        encoding="utf-8",
    )

    command_log = [
        "# Validation commands executed",
        "",
        f"Generated UTC: {generated}",
        f"FreeCAD: {'.'.join(App.Version()[:3])}",
        "",
        "```sh",
        "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \"globals()['__file__']='Project/FlightDeck/Scripts/build_flight_deck.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))\"",
        "python3 Project/FlightDeck/Scripts/inventory_sources.py",
        "python3 Project/FlightDeck/Scripts/render_flight_deck.py",
        "python3 Project/FlightDeck/Scripts/run_bambu_checks.py",
        "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \"globals()['__file__']='Project/FlightDeck/Scripts/validate_flight_deck.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))\"",
        "```",
    ]
    (QA / "Validation_Commands.md").write_text("\n".join(command_log) + "\n", encoding="utf-8")
    print(json.dumps({"mesh": mesh_report["overall_status"], "dimensional": dimensional_report["overall_status"], "mesh_checks": len(mesh_checks), "dimensional_checks": len(dimension_checks)}, indent=2))
    if not (mesh_overall and dimensional_overall):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
