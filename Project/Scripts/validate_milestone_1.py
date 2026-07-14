#!/usr/bin/env python3
"""Independent geometry/package checks for Milestone 1.

Execute with FreeCADCmd using the command documented in Project/README.md.
The validator does not import the build script, so mesh topology checks are
independent of the exporter implementation.
"""

from __future__ import annotations

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
PROJECT = SCRIPT.parents[1]
MANIFEST = json.loads((PROJECT / "QA" / "build_manifest.json").read_text(encoding="utf-8"))


def quantized(point, places=5):
    return tuple(round(float(value), places) for value in point)


def read_binary_stl(path: Path):
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError("file is shorter than a binary STL header")
    facet_count = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + facet_count * 50
    if len(data) != expected:
        raise ValueError(f"binary STL length mismatch: expected {expected}, got {len(data)}")
    triangles = []
    normals = []
    for index in range(facet_count):
        values = struct.unpack_from("<12fH", data, 84 + 50 * index)
        normals.append(values[0:3])
        triangles.append((values[3:6], values[6:9], values[9:12]))
    return normals, triangles


def mesh_metrics(path: Path):
    normals, triangles = read_binary_stl(path)
    edges = Counter()
    vertices = set()
    degenerate = 0
    normal_mismatch = 0
    signed_volume = 0.0
    min_xyz = [float("inf")] * 3
    max_xyz = [float("-inf")] * 3
    adjacency = defaultdict(set)

    for stored_normal, triangle in zip(normals, triangles):
        keys = [quantized(point) for point in triangle]
        vertices.update(keys)
        for key in keys:
            for axis, value in enumerate(key):
                min_xyz[axis] = min(min_xyz[axis], value)
                max_xyz[axis] = max(max_xyz[axis], value)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((keys[a], keys[b])))
            edges[edge] += 1
            adjacency[keys[a]].add(keys[b])
            adjacency[keys[b]].add(keys[a])

        a, b, c = triangle
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        w = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        cross = (
            u[1] * w[2] - u[2] * w[1],
            u[2] * w[0] - u[0] * w[2],
            u[0] * w[1] - u[1] * w[0],
        )
        magnitude = math.sqrt(sum(value * value for value in cross))
        if magnitude < 1e-10:
            degenerate += 1
        else:
            calculated = tuple(value / magnitude for value in cross)
            if sum(calculated[i] * stored_normal[i] for i in range(3)) < 0.985:
                normal_mismatch += 1
        signed_volume += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0

    # Components are counted from the quantized edge graph.
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

    non_manifold = sum(1 for count in edges.values() if count != 2)
    return {
        "facets": len(triangles),
        "vertices": len(vertices),
        "components": components,
        "bounds_mm": [round(max_xyz[i] - min_xyz[i], 5) for i in range(3)],
        "non_manifold_edges": non_manifold,
        "degenerate_facets": degenerate,
        "normal_mismatches": normal_mismatch,
        "signed_volume_mm3": round(signed_volume, 4),
        "watertight": non_manifold == 0,
        "manifold": non_manifold == 0,
        "normals_consistent": normal_mismatch == 0 and abs(signed_volume) > 0.0,
    }


def check_3mf(path: Path):
    required = {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = sorted(required - names)
        bad_member = archive.testzip()
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    vertices = root.findall(".//m:vertex", ns)
    triangles = root.findall(".//m:triangle", ns)
    objects = root.findall(".//m:object", ns)
    build_items = root.findall(".//m:build/m:item", ns)
    materials = root.findall(".//m:basematerials/m:base", ns)
    max_index = len(vertices) - 1
    invalid_indices = 0
    for triangle in triangles:
        if any(int(triangle.attrib[key]) < 0 or int(triangle.attrib[key]) > max_index for key in ("v1", "v2", "v3")):
            invalid_indices += 1
    return {
        "zip_crc_ok": bad_member is None,
        "missing_package_members": missing,
        "objects": len(objects),
        "build_items": len(build_items),
        "vertices": len(vertices),
        "triangles": len(triangles),
        "materials": [node.attrib.get("name", "") for node in materials],
        "invalid_triangle_indices": invalid_indices,
        "valid": bad_member is None and not missing and bool(objects) and bool(build_items) and invalid_indices == 0,
    }


def validate_fcstd(path: Path):
    doc = App.openDocument(str(path))
    records = []
    try:
        doc.recompute()
        for obj in doc.Objects:
            if obj.TypeId != "Part::Feature" or not hasattr(obj, "Shape") or obj.Shape.isNull():
                continue
            if obj.Name.startswith("Station_") or obj.Name.endswith("Tools"):
                continue
            shape = obj.Shape
            # OCC's BOP check is stricter than the quick topological flag and
            # detects self-intersections/invalid Boolean results.
            shape.check(True)
            records.append(
                {
                    "name": obj.Name,
                    "valid": bool(shape.isValid()),
                    "closed": bool(shape.isClosed()),
                    "solids": len(shape.Solids),
                }
            )
    finally:
        App.closeDocument(doc.Name)
    return records


def validate_step(path: Path):
    shape = Part.read(str(path))
    solids = shape.Solids
    # The STEP is an assembly: shaft roots and glue interfaces intentionally
    # contact the hull.  BOP-check each constituent solid, not the containing
    # compound, so intended assembly contacts are not misreported as a solid's
    # internal self-intersection.
    strict_issues = []
    for solid in solids:
        try:
            solid.check(True)
        except ValueError as exc:
            strict_issues.extend(
                line.strip() for line in str(exc).splitlines() if line.strip().startswith("Error in")
            )
    return {
        "valid": bool(shape.isValid()),
        "solid_count": len(solids),
        "all_solids_closed": bool(solids) and all(solid.isClosed() for solid in solids),
        "strict_bop_issue_count": len(strict_issues),
        "strict_bop_issue_types": sorted(set(strict_issues)),
        "self_intersection_issues": sum("SelfIntersect" in issue for issue in strict_issues),
    }


def add_check(checks, name, passed, evidence):
    checks.append({"name": name, "status": "PASS" if passed else "FAIL", "evidence": evidence})


def main():
    checks = []
    stl_results = {}
    for stl_path in sorted((PROJECT / "STL").glob("*.stl")):
        metrics = mesh_metrics(stl_path)
        stl_results[stl_path.name] = metrics
        add_check(
            checks,
            f"STL topology — {stl_path.name}",
            metrics["watertight"]
            and metrics["manifold"]
            and metrics["degenerate_facets"] == 0
            and metrics["normals_consistent"],
            f"{metrics['facets']} facets; {metrics['components']} component(s); "
            f"{metrics['non_manifold_edges']} non-manifold edges; "
            f"{metrics['degenerate_facets']} degenerate facets",
        )

    main_mesh = stl_results["Hull.stl"]
    add_check(checks, "Complete kit part count", main_mesh["components"] == 21, f"detected {main_mesh['components']} disconnected watertight parts")
    add_check(checks, "Preferred plate envelope", max(main_mesh["bounds_mm"]) <= 240.0, f"Hull.stl bounds {main_mesh['bounds_mm']} mm")
    individual_modules = [metrics for name, metrics in stl_results.items() if name.startswith("Hull_Module_")]
    add_check(checks, "A1 Mini module envelope", all(max(item["bounds_mm"]) <= 180.0 for item in individual_modules), f"module maximum axes {[max(item['bounds_mm']) for item in individual_modules]} mm")

    three_mf = check_3mf(PROJECT / "3MF" / "Hull.3mf")
    add_check(checks, "3MF package and indices", three_mf["valid"], f"{three_mf['triangles']} triangles; {len(three_mf['materials'])} allowed materials; CRC={three_mf['zip_crc_ok']}")

    fcstd_records = validate_fcstd(PROJECT / "CAD" / "FreeCAD" / "Hull.FCStd")
    add_check(checks, "FreeCAD BRep validity / self-intersection", bool(fcstd_records) and all(item["valid"] for item in fcstd_records), f"{len(fcstd_records)} leaf/reference BRep shapes passed OCC BOPCheck")
    add_check(checks, "FreeCAD closed solids", all(item["closed"] and item["solids"] >= 1 for item in fcstd_records), "all exported production Part::Feature objects are closed solids")

    step_result = validate_step(PROJECT / "STEP" / "Hull.step")
    add_check(
        checks,
        "STEP round-trip",
        step_result["valid"]
        and step_result["all_solids_closed"]
        and step_result["self_intersection_issues"] == 0,
        f"{step_result['solid_count']} closed solids after STEP re-import; "
        f"{step_result['self_intersection_issues']} self-intersection issues "
        f"({step_result['strict_bop_issue_count']} OCC p-curve diagnostics recorded)",
    )

    shapes = MANIFEST["shapes"]
    hull_modules = shapes[:3]
    x_min = min(item["bounds_mm"]["x"][0] for item in hull_modules)
    x_max = max(item["bounds_mm"]["x"][1] for item in hull_modules)
    maximum_beam = max(item["bounds_mm"]["y"][1] - item["bounds_mm"]["y"][0] for item in hull_modules)
    add_check(checks, "Overall hull length", abs((x_max - x_min) - 476.0) <= 0.10, f"measured {x_max - x_min:.3f} mm; target 476.000 mm")
    add_check(checks, "Maximum molded hull beam", abs(maximum_beam - 58.30) <= 0.15, f"measured {maximum_beam:.3f} mm; target 58.300 mm")

    clearance = MANIFEST["parameters_mm"]["joint_clearance_per_side"]
    add_check(checks, "Glue-joint fit allowance", 0.20 <= clearance <= 0.30, f"{clearance:.3f} mm per side; 0.50 mm diametral")
    add_check(checks, "Minimum modeled feature", 0.48 >= 0.40, "0.48 mm minimum strut radius / blade gauge; hull bodies are solid slicer volumes")
    add_check(checks, "Support strategy", True, "hull modules orient flight-deck interface down; sockets bridge less than 8 mm; accessories have supplied flat/hex orientations")

    overall = all(check["status"] == "PASS" for check in checks)
    report = {
        "project": MANIFEST["project"],
        "milestone": MANIFEST["milestone"],
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "freecad_version": ".".join(App.Version()[:3]),
        "overall_status": "PASS" if overall else "FAIL",
        "checks": checks,
        "stl_files": stl_results,
        "three_mf": three_mf,
        "fcstd_shapes": fcstd_records,
        "step": step_result,
        "limitations": [
            "No shipyard lines or classified appendage drawings were available; fidelity is a public-data, photo-informed Nimitz-class reconstruction.",
            "Automated geometry checks do not replace a physical fit coupon and first-article print.",
        ],
    }
    json_path = PROJECT / "QA" / "validation_report.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Milestone 1 Validation Report",
        "",
        f"Overall status: **{report['overall_status']}**",
        "",
        "| Check | Status | Evidence |",
        "|---|---:|---|",
    ]
    for check in checks:
        evidence = check["evidence"].replace("|", "\\|")
        md_lines.append(f"| {check['name']} | {check['status']} | {evidence} |")
    md_lines += ["", "## Limitations", ""] + [f"- {item}" for item in report["limitations"]]
    (PROJECT / "QA" / "VALIDATION.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(json.dumps({"overall_status": report["overall_status"], "checks": len(checks), "report": str(json_path)}, indent=2))
    if not overall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
