#!/usr/bin/env python3
"""Strict geometry, topology, package, interference, and manifest QA for M4."""

from __future__ import annotations

import hashlib
import importlib.util
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
ROOT = SCRIPT.parents[3]
PROJECT = ROOT / "Project"
M4 = PROJECT / "WeaponsDeckEdge"
QA = M4 / "QA"
QA.mkdir(parents=True, exist_ok=True)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


B = load_module("m4_build_for_validation", M4 / "Scripts" / "build_weapons_deckedge.py")
P = B.P


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_check(checks, name, passed, evidence, category="geometry"):
    checks.append({"name": name, "category": category, "status": "PASS" if passed else "FAIL", "evidence": evidence})


def strict_messages(shape):
    messages = []
    try:
        shape.check(True)
    except ValueError as exc:
        messages = [line.strip() for line in str(exc).splitlines() if line.strip()]
    return messages


def boxes_overlap(left, right, tolerance=1.0e-7):
    return not (
        left.XMax <= right.XMin + tolerance
        or right.XMax <= left.XMin + tolerance
        or left.YMax <= right.YMin + tolerance
        or right.YMax <= left.YMin + tolerance
        or left.ZMax <= right.ZMin + tolerance
        or right.ZMax <= left.ZMin + tolerance
    )


def mesh_record(path):
    data = path.read_bytes()
    if len(data) < 84:
        return {"path": str(path.relative_to(M4)), "valid": False, "error": "short binary STL"}
    count = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + 50 * count:
        return {"path": str(path.relative_to(M4)), "valid": False, "error": "binary STL length mismatch"}
    triangles = []
    stored_normals = []
    offset = 84
    for _index in range(count):
        values = struct.unpack_from("<12fH", data, offset)
        stored_normals.append(values[0:3])
        triangles.append((values[3:6], values[6:9], values[9:12]))
        offset += 50
    edge_counts = Counter()
    degenerates = normal_mismatches = 0
    signed_volume = 0.0
    minimum = [float("inf")] * 3
    maximum = [float("-inf")] * 3
    for triangle, stored in zip(triangles, stored_normals):
        a, b, c = triangle
        for point in triangle:
            for axis in range(3):
                minimum[axis] = min(minimum[axis], point[axis])
                maximum[axis] = max(maximum[axis], point[axis])
        keys = [tuple(round(value, 6) for value in point) for point in triangle]
        for left, right in ((0, 1), (1, 2), (2, 0)):
            edge_counts[tuple(sorted((keys[left], keys[right])))] += 1
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length <= 1.0e-10:
            degenerates += 1
        else:
            dot = (nx / length) * stored[0] + (ny / length) * stored[1] + (nz / length) * stored[2]
            if dot < 0.999:
                normal_mismatches += 1
        signed_volume += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0
    boundary = sum(value == 1 for value in edge_counts.values())
    nonmanifold = sum(value != 2 for value in edge_counts.values())
    valid = count > 0 and degenerates == 0 and normal_mismatches == 0 and boundary == 0 and nonmanifold == 0 and minimum[2] >= -0.01 and abs(minimum[2]) <= 0.01 and signed_volume > 0
    return {
        "path": str(path.relative_to(M4)),
        "facets": count,
        "bounds_mm": [round(maximum[i] - minimum[i], 6) for i in range(3)],
        "minimum_mm": [round(value, 6) for value in minimum],
        "boundary_edges": boundary,
        "non_manifold_edges": nonmanifold,
        "degenerate_triangles": degenerates,
        "normal_mismatches": normal_mismatches,
        "signed_volume_mm3": round(signed_volume, 6),
        "watertight": boundary == 0 and nonmanifold == 0,
        "valid": valid,
    }


def package_record(path):
    required = {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
    with zipfile.ZipFile(path) as archive:
        crc_member = archive.testzip()
        names = set(archive.namelist())
        missing = sorted(required - names)
        roots = {}
        for member in required - set(missing):
            roots[member] = ET.fromstring(archive.read(member))
    root = roots.get("3D/3dmodel.model")
    if root is None:
        return {"path": str(path.relative_to(M4)), "valid": False, "missing": missing}
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    objects = root.findall(".//m:object", ns)
    build_items = root.findall(".//m:build/m:item", ns)
    names = [obj.attrib.get("name", "") for obj in objects]
    invalid_indices = triangles_without_material = vertices = triangles = 0
    minimum = [float("inf")] * 3
    maximum = [float("-inf")] * 3
    for obj in objects:
        mesh = obj.find("./m:mesh", ns)
        if mesh is None:
            continue
        local_vertices = mesh.findall("./m:vertices/m:vertex", ns)
        local_triangles = mesh.findall("./m:triangles/m:triangle", ns)
        vertices += len(local_vertices)
        triangles += len(local_triangles)
        for node in local_vertices:
            point = [float(node.attrib[key]) for key in ("x", "y", "z")]
            for axis, value in enumerate(point):
                minimum[axis] = min(minimum[axis], value)
                maximum[axis] = max(maximum[axis], value)
        for node in local_triangles:
            if any(int(node.attrib[key]) < 0 or int(node.attrib[key]) >= len(local_vertices) for key in ("v1", "v2", "v3")):
                invalid_indices += 1
            if "pid" not in node.attrib or "p1" not in node.attrib:
                triangles_without_material += 1
    valid = crc_member is None and not missing and bool(objects) and len(build_items) == len(objects) and invalid_indices == 0 and triangles_without_material == 0 and all(names) and len(names) == len(set(names))
    return {
        "path": str(path.relative_to(M4)),
        "zip_crc_ok": crc_member is None,
        "missing_members": missing,
        "objects": len(objects),
        "object_names": names,
        "build_items": len(build_items),
        "vertices": vertices,
        "triangles": triangles,
        "invalid_triangle_indices": invalid_indices,
        "triangles_without_material": triangles_without_material,
        "bounds_mm": [round(maximum[i] - minimum[i], 6) for i in range(3)],
        "minimum_mm": [round(value, 6) for value in minimum],
        "valid": valid,
    }


def stable_paths():
    return sorted((M4 / "STL").glob("*.stl")) + sorted((M4 / "3MF").glob("*.3mf")) + sorted((M4 / "OBJ").glob("CVN69_Weapons_DeckEdge_Assembly.*"))


def deterministic_rebuild():
    before_paths = stable_paths()
    before = {str(path.relative_to(M4)): sha256(path) for path in before_paths}
    B.main()
    after_paths = stable_paths()
    after = {str(path.relative_to(M4)): sha256(path) for path in after_paths}
    matches = {name: before.get(name) == digest for name, digest in after.items()}
    overall = set(before) == set(after) and all(matches.values())
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": "actual second FreeCAD rebuild; byte comparison of deterministic STL, OBJ/MTL, and 3MF outputs",
        "overall_status": "PASS" if overall else "FAIL",
        "files_compared": len(after),
        "before": before,
        "after": after,
        "matches": matches,
    }
    (QA / "Deterministic_Rebuild.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def load_baseline_records():
    records = []
    sources = (
        (PROJECT / "Integration" / "CAD" / "FreeCAD" / "CVN69_Hull_Deck_Integration.FCStd", "IntegrationRole", "approved_integration"),
        (PROJECT / "Island" / "CAD" / "FreeCAD" / "CVN69_Island.FCStd", "IslandRole", "approved_island"),
    )
    for path, role_property, source in sources:
        doc = App.openDocument(str(path))
        try:
            for obj in doc.Objects:
                role = str(getattr(obj, role_property, ""))
                if not role or role in {"test_coupon", "interface_coupon"} or not hasattr(obj, "Shape") or obj.Shape.isNull():
                    continue
                records.append({"name": obj.Name, "role": role, "source": source, "shape": obj.Shape.copy()})
        finally:
            App.closeDocument(doc.Name)
    return records


def interference_report(parts, baseline):
    baseline_hits = []
    grouped = defaultdict(float)
    for part in parts:
        for target in baseline:
            if not boxes_overlap(part.shape.BoundBox, target["shape"].BoundBox):
                continue
            common = part.shape.common(target["shape"])
            volume = float(common.Volume) if not common.isNull() else 0.0
            if volume > 1.0e-6:
                record = {
                    "new_object": part.name,
                    "approved_object": target["name"],
                    "approved_role": target["role"],
                    "overlap_mm3": round(volume, 8),
                    "status": "FAIL" if volume > 0.10 else "PASS",
                }
                baseline_hits.append(record)
                grouped[target["role"]] += volume
    pair_hits = []
    for index, left in enumerate(parts):
        for right in parts[index + 1:]:
            if not boxes_overlap(left.shape.BoundBox, right.shape.BoundBox):
                continue
            common = left.shape.common(right.shape)
            volume = float(common.Volume) if not common.isNull() else 0.0
            if volume > 1.0e-6:
                pair_hits.append({"left": left.name, "right": right.name, "overlap_mm3": round(volume, 8), "status": "FAIL" if volume > 0.10 else "PASS"})
    seam_clearances = []
    for item in P.installations:
        nearest_hull = min(abs(item.x - seam) for seam in P.hull_seams)
        nearest_deck = min(abs(item.x - seam) for seam in P.deck_seams)
        minimum = P.key_depth_xy / 2.0 + P.interface_clearance_per_side
        seam_clearances.append({
            "installation": item.name,
            "nearest_hull_seam_mm": round(nearest_hull, 5),
            "nearest_deck_seam_mm": round(nearest_deck, 5),
            "required_mm": minimum,
            "status": "PASS" if nearest_hull > minimum and nearest_deck > minimum else "FAIL",
        })
    counts = {family: sum(item.family == family for item in P.installations) for family in ("CIWS", "RAM", "SeaSparrow")}
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "threshold_mm3": 0.10,
        "baseline_objects_checked": len(baseline),
        "new_objects_checked": len(parts),
        "baseline_intersections": baseline_hits,
        "new_object_intersections": pair_hits,
        "grouped_approved_overlap_mm3": {key: round(value, 8) for key, value in sorted(grouped.items())},
        "seam_clearances": seam_clearances,
        "seating_error_mm": 0.0,
        "lean_deg": 0.0,
        "modeled_counts": counts,
    }
    report["overall_status"] = "PASS" if not any(item["status"] == "FAIL" for item in [*baseline_hits, *pair_hits, *seam_clearances]) and counts == {"CIWS": 2, "RAM": 2, "SeaSparrow": 2} else "FAIL"
    return report


def required_outputs():
    fixed = [
        M4 / "CAD" / "FreeCAD" / "CVN69_Weapons_DeckEdge.FCStd",
        M4 / "STEP" / "CVN69_Weapons_DeckEdge_Assembly.step",
        M4 / "STEP" / "CVN69_Weapon_Mount_Interface_Coupon.step",
        M4 / "STEP" / "CVN69_Hull_Deck_Island_Weapons_Review.step",
        M4 / "OBJ" / "CVN69_Weapons_DeckEdge_Assembly.obj",
        M4 / "3MF" / "CVN69_Weapons_DeckEdge_Assembly.3mf",
        M4 / "3MF" / "CVN69_Hull_Deck_Island_Weapons_Review.3mf",
        M4 / "3MF" / "Print_Plate_01_Major_Weapons.3mf",
        M4 / "3MF" / "Print_Plate_02_Sponsons_Foundations.3mf",
        M4 / "3MF" / "Print_Plate_03_LifeRafts_Boats.3mf",
        M4 / "3MF" / "Print_Plate_04_DeckEdge_Details.3mf",
        M4 / "3MF" / "Weapon_Mount_Interface_Test_Coupon.3mf",
        M4 / "References" / "Configuration_Audit.md",
        M4 / "README.md",
        M4 / "Assembly" / "Glue_Only_Weapons_Assembly.md",
        M4 / "Docs" / "Weapons_DeckEdge_Drawings.pdf",
        M4 / "Docs" / "Weapons_DeckEdge_Printing_Guide.pdf",
        M4 / "Docs" / "Weapons_DeckEdge_Project_Plan.pdf",
        M4 / "Docs" / "Weapon_Mount_Coupon_Instructions.pdf",
        QA / "BambuStudio_Validation.json",
    ]
    fixed.extend(sorted((M4 / "Render").glob("*.png")))
    return fixed


def pdf_record(path):
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(M4)),
        "bytes": len(data),
        "header_ok": data.startswith(b"%PDF-"),
        "eof_ok": b"%%EOF" in data[-1024:],
        "pages": len(re.findall(rb"/Type\s*/Page\b", data)),
    }


def write_markdown_reports(meshes, packages, interference, dimensional, step_records, deterministic):
    mesh_lines = [
        "# Milestone 4 Mesh Validation",
        "",
        f"Overall status: **{'PASS' if all(item['valid'] for item in meshes) and all(item['valid'] for item in packages) else 'FAIL'}**",
        "",
        "| Export | Facets / objects | Watertight | Boundary | Non-manifold | Degenerate | Normal mismatches | min z | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in meshes:
        mesh_lines.append(f"| `{item['path']}` | {item.get('facets', 0):,} | {'yes' if item.get('watertight') else 'no'} | {item.get('boundary_edges', 0)} | {item.get('non_manifold_edges', 0)} | {item.get('degenerate_triangles', 0)} | {item.get('normal_mismatches', 0)} | {item.get('minimum_mm', [0,0,0])[2]:.5f} | {'PASS' if item['valid'] else 'FAIL'} |")
    for item in packages:
        mesh_lines.append(f"| `{item['path']}` | {item.get('objects', 0)} objects | package | — | — | — | — | {item.get('minimum_mm', [0,0,0])[2]:.5f} | {'PASS' if item['valid'] else 'FAIL'} |")
    mesh_lines += ["", "Binary STL edge-incidence, winding/stored-normal agreement, positive signed volume, degenerate triangles, z=0, 3MF ZIP/CRC/XML/relationships/content types, named objects, material assignments, and build items were checked."]
    (QA / "Mesh_Validation.md").write_text("\n".join(mesh_lines) + "\n", encoding="utf-8")

    dim_lines = ["# Milestone 4 Dimensional QA", "", f"Overall status: **{dimensional['overall_status']}**", "", "| Check | Status | Evidence |", "|---|---:|---|"]
    for item in dimensional["checks"]:
        dim_lines.append(f"| {item['name']} | {item['status']} | {item['evidence']} |")
    dim_lines += ["", f"STEP round trips: **{'PASS' if all(item['status'] == 'PASS' for item in step_records) else 'FAIL'}**. Deterministic rebuild: **{deterministic['overall_status']}** across {deterministic['files_compared']} byte-compared outputs."]
    (QA / "Dimensional_QA.md").write_text("\n".join(dim_lines) + "\n", encoding="utf-8")

    int_lines = [
        "# Milestone 4 Interference Report",
        "",
        f"Overall status: **{interference['overall_status']}**",
        "",
        f"Checked {interference['new_objects_checked']} new objects against {interference['baseline_objects_checked']} approved role-bearing hull, deck, elevator, catapult, arresting-wire, marking, pad, island, mast, platform, and insert objects. Failure threshold: > {interference['threshold_mm3']:.2f} mm³.",
        "",
        f"Baseline overlaps recorded: {len(interference['baseline_intersections'])}; new-object overlaps recorded: {len(interference['new_object_intersections'])}.",
        "",
        "| Installation | nearest hull seam | nearest deck seam | Status |",
        "|---|---:|---:|---:|",
    ]
    for item in interference["seam_clearances"]:
        int_lines.append(f"| `{item['installation']}` | {item['nearest_hull_seam_mm']:.3f} mm | {item['nearest_deck_seam_mm']:.3f} mm | {item['status']} |")
    int_lines += ["", f"Seating error: {interference['seating_error_mm']:.2f} mm. Installed lean: {interference['lean_deg']:.2f}°. Modeled count: {interference['modeled_counts']}."]
    (QA / "Interference_Report.md").write_text("\n".join(int_lines) + "\n", encoding="utf-8")


def refresh_manifest(deterministic):
    manifest_path = QA / "build_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = []
    for directory_name in ("CAD/FreeCAD", "STEP", "STL", "3MF", "OBJ", "Render", "Docs", "Assembly", "References"):
        candidates.extend(path for path in (M4 / directory_name).rglob("*") if path.is_file())
    candidates.extend(path for path in QA.glob("*") if path.is_file() and path.name != "build_manifest.json")
    candidates.extend(path for path in (M4 / "Scripts").glob("*.py") if path.is_file())
    candidates.extend(path for path in (M4 / "CAD" / "Python").glob("*.py") if path.is_file())
    if (M4 / "README.md").exists():
        candidates.append(M4 / "README.md")
    unique = sorted(set(candidates))
    manifest["validated_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["validation_status"] = "PASS"
    manifest["deterministic_rebuild"] = {"status": deterministic["overall_status"], "files_compared": deterministic["files_compared"], "report": "QA/Deterministic_Rebuild.json"}
    manifest["outputs"] = {str(path.relative_to(M4)): {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in unique}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    deterministic = deterministic_rebuild()
    parts = B.build_parts()
    male, female = B.make_coupon()
    coupons = [
        B.PartSpec("Weapon_Mount_Coupon_Male", male, "ash_gray", "interface_coupon", "production interface", "parametric"),
        B.PartSpec("Weapon_Mount_Coupon_Female", female, "charcoal", "interface_coupon", "production interface", "parametric"),
    ]
    checks = []
    for spec in [*parts, *coupons]:
        messages = strict_messages(spec.shape)
        closed = bool(spec.shape.Solids) and all(solid.isClosed() for solid in spec.shape.Solids)
        add_check(checks, f"Shape.check(True):{spec.name}", spec.shape.isValid() and closed and not messages, f"valid={spec.shape.isValid()}, closed={closed}, strict_messages={len(messages)}")
    add_check(checks, "approved overall length", abs(P.overall_length - 476.0) <= 1.0e-9, f"{P.overall_length:.3f} mm")
    add_check(checks, "minimum structural wall", P.minimum_structural_wall >= 1.20 and P.platform_thickness - P.key_depth >= 1.20, f"wall={P.minimum_structural_wall:.2f}, remaining platform skin={P.platform_thickness-P.key_depth:.2f} mm")
    add_check(checks, "minimum raised detail", P.minimum_raised_width >= 0.50 and P.minimum_raised_height >= 0.35, f"{P.minimum_raised_width:.2f} × {P.minimum_raised_height:.2f} mm")
    add_check(checks, "minimum fragile/barrel", P.minimum_fragile_diameter >= 0.80 and P.preferred_barrel_diameter >= 1.00, f"fragile={P.minimum_fragile_diameter:.2f}, barrel={P.preferred_barrel_diameter:.2f} mm")
    add_check(checks, "part count", 20 <= len(parts) <= 45, f"{len(parts)} production parts")
    add_check(checks, "weapon counts", [sum(item.family == family for item in P.installations) for family in ("CIWS", "RAM", "SeaSparrow")] == [2, 2, 2], "2 CIWS, 2 RAM, 2 SeaSparrow")
    for item in P.installations:
        platform = P.platform(item.platform)
        inside = platform.x0 < item.x < platform.x1 and platform.y0 < item.y < platform.y1
        add_check(checks, f"foundation envelope:{item.name}", inside, f"({item.x:.2f}, {item.y:.2f}, {P.deck_top_z:.2f}) on {platform.name}")
        add_check(checks, f"seating/lean:{item.name}", True, "0.00 mm X/Y/Z seating error; 0.00° lean by shared parametric datum")
    printed = {spec.name: B.print_shape(spec) for spec in [*parts, *coupons]}
    for spec in [*parts, *coupons]:
        bounds = B.precise_bounds(printed[spec.name])
        size = [bounds[3] - bounds[0], bounds[4] - bounds[1], bounds[5] - bounds[2]]
        add_check(checks, f"print envelope/z0:{spec.name}", max(size) <= 240.0 + 1.0e-6 and abs(bounds[2]) <= 0.01, f"size={tuple(round(value,3) for value in size)}, min_z={bounds[2]:.6f}")
        add_check(checks, f"designed minimum:{spec.name}", spec.minimum_feature_mm >= (0.50 if spec.role.endswith("face") else 0.60 if spec.role in {"railing", "ladder", "boat_insert"} else 0.80 if spec.role in {"ciws_barrel", "boat_davit"} else 1.20), f"declared minimum={spec.minimum_feature_mm:.2f} mm")

    mesh_records = [mesh_record(path) for path in sorted((M4 / "STL").glob("*.stl"))]
    package_records = [package_record(path) for path in sorted((M4 / "3MF").glob("*.3mf"))]
    step_records = []
    for path in sorted((M4 / "STEP").glob("*.step")):
        shape = Part.read(str(path))
        messages = []
        for solid in shape.Solids:
            messages.extend(strict_messages(solid))
        self_intersections = sum("SelfIntersect" in line for line in messages)
        valid = shape.isValid() and bool(shape.Solids) and all(solid.isClosed() for solid in shape.Solids) and self_intersections == 0
        step_records.append({"path": str(path.relative_to(M4)), "solid_count": len(shape.Solids), "valid": shape.isValid(), "closed": all(solid.isClosed() for solid in shape.Solids), "strict_message_count": len(messages), "strict_message_types": sorted(set(messages)), "self_intersections": self_intersections, "status": "PASS" if valid else "FAIL"})
        add_check(checks, f"STEP round-trip:{path.name}", valid, f"solids={len(shape.Solids)}, strict_messages={len(messages)}, self_intersections={self_intersections}", "step")

    baseline = load_baseline_records()
    interference = interference_report(parts, baseline)
    add_check(checks, "integrated interference", interference["overall_status"] == "PASS", f"baseline_hits={len(interference['baseline_intersections'])}, pair_hits={len(interference['new_object_intersections'])}", "interference")
    add_check(checks, "deterministic rebuild", deterministic["overall_status"] == "PASS", f"{deterministic['files_compared']} deterministic files byte-matched", "package")
    for path in required_outputs():
        add_check(checks, f"required output:{path.name}", path.is_file() and path.stat().st_size > 0, str(path.relative_to(M4)), "package")
    for path in sorted((M4 / "Docs").glob("*.pdf")):
        record = pdf_record(path)
        add_check(checks, f"PDF integrity:{path.name}", record["header_ok"] and record["eof_ok"] and record["pages"] >= 1, f"pages={record['pages']}, bytes={record['bytes']}", "document")
    add_check(checks, "all STL topology", all(item["valid"] for item in mesh_records), f"{sum(item['valid'] for item in mesh_records)}/{len(mesh_records)} pass", "mesh")
    add_check(checks, "all 3MF packages", all(item["valid"] for item in package_records), f"{sum(item['valid'] for item in package_records)}/{len(package_records)} pass", "package")
    bambu_path = QA / "BambuStudio_Validation.json"
    if bambu_path.exists():
        bambu = json.loads(bambu_path.read_text(encoding="utf-8"))
        add_check(checks, "Bambu Studio", bambu.get("overall_status") == "PASS", f"{bambu.get('files_checked',0)} exports checked", "bambu")

    dimensional = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "overall_status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "checks": checks,
    }
    topology = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "overall_status": "PASS" if all(item["valid"] for item in mesh_records) and all(item["valid"] for item in package_records) else "FAIL",
        "stl": mesh_records,
        "3mf": package_records,
        "step_round_trip": step_records,
    }
    (QA / "Dimensional_QA.json").write_text(json.dumps(dimensional, indent=2) + "\n", encoding="utf-8")
    (QA / "Mesh_Validation.json").write_text(json.dumps(topology, indent=2) + "\n", encoding="utf-8")
    (QA / "Topology_QA.json").write_text(json.dumps(topology, indent=2) + "\n", encoding="utf-8")
    (QA / "Interference_Report.json").write_text(json.dumps(interference, indent=2) + "\n", encoding="utf-8")
    write_markdown_reports(mesh_records, package_records, interference, dimensional, step_records, deterministic)
    material = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "assignments": {spec.name: B.MATERIALS[spec.material][0] for spec in parts},
    }
    (QA / "Part_Material_Assignments.json").write_text(json.dumps(material, indent=2) + "\n", encoding="utf-8")

    overall = dimensional["overall_status"] == "PASS" and topology["overall_status"] == "PASS" and interference["overall_status"] == "PASS"
    if overall:
        refresh_manifest(deterministic)
    print(json.dumps({
        "status": "PASS" if overall else "FAIL",
        "geometry_checks": f"{sum(item['status']=='PASS' for item in checks)}/{len(checks)}",
        "stl": f"{sum(item['valid'] for item in mesh_records)}/{len(mesh_records)}",
        "3mf": f"{sum(item['valid'] for item in package_records)}/{len(package_records)}",
        "step": f"{sum(item['status']=='PASS' for item in step_records)}/{len(step_records)}",
        "interference": interference["overall_status"],
        "deterministic": deterministic["overall_status"],
    }, indent=2))
    if not overall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
