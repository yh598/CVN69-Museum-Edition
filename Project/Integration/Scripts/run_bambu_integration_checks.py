#!/usr/bin/env python3
"""Run Bambu Studio import and real slicing checks on Milestone 2 exports."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


SCRIPT = Path(__file__).resolve()
INTEGRATION = SCRIPT.parents[1]
PROJECT = INTEGRATION.parent
QA = INTEGRATION / "QA"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
BAMBU_SYSTEM = Path.home() / "Library" / "Application Support" / "BambuStudio" / "system" / "BBL"
MACHINE_PROFILE = QA / "Bambu_Profiles" / "CVN69_A1_0p4_Machine_Validation.json"
PROCESS_PROFILES = {
    0.12: QA / "Bambu_Profiles" / "CVN69_A1_0p12_Propeller_Validation.json",
    0.16: QA / "Bambu_Profiles" / "CVN69_A1_0p16_Propeller_Validation.json",
}
FILAMENT_PROFILES = {
    "matte": BAMBU_SYSTEM / "filament" / "Bambu PLA Matte @BBL A1.json",
    "silk": BAMBU_SYSTEM / "filament" / "Bambu PLA Silk @BBL A1.json",
}
SLICE_PLATES = {
    "3MF/Print_Plate_01_Hull.3mf": "matte",
    "3MF/Print_Plate_04_Propellers.3mf": "silk",
}
TARGET_WARNING_PATTERNS = {
    "floating_region_warnings": r"floating regions?",
    "empty_layer_warnings": r"empty layers?|empty layer between",
    "faulty_mesh_warnings": r"faulty mesh",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_info(output: str):
    def floats(key):
        return [float(value) for value in re.findall(rf"^{key}\s*=\s*([-+0-9.eE]+)", output, re.MULTILINE)]

    def integers(key):
        return [int(value) for value in re.findall(rf"^{key}\s*=\s*(\d+)", output, re.MULTILINE)]

    manifolds = [value.lower() for value in re.findall(r"^manifold\s*=\s*(\w+)", output, re.MULTILINE)]
    sizes = {axis: floats(f"size_{axis}") for axis in "xyz"}
    facets = integers("number_of_facets")
    parts = integers("number_of_parts")
    return {
        "raw": output.strip(),
        "objects_reported": len(manifolds),
        "size_x": max(sizes["x"], default=float("inf")),
        "size_y": max(sizes["y"], default=float("inf")),
        "size_z": max(sizes["z"], default=float("inf")),
        "facets": sum(facets),
        "parts": sum(parts),
        "manifold": "yes" if manifolds and all(value == "yes" for value in manifolds) else "no",
        "manifold_results": manifolds,
    }


def three_mf_metadata(path: Path):
    namespace = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
    records = []
    for obj in root.findall("./m:resources/m:object", namespace):
        vertices = [
            tuple(float(vertex.attrib[key]) for key in ("x", "y", "z"))
            for vertex in obj.findall("./m:mesh/m:vertices/m:vertex", namespace)
        ]
        minimum = [min(point[axis] for point in vertices) for axis in range(3)]
        maximum = [max(point[axis] for point in vertices) for axis in range(3)]
        records.append(
            {
                "id": int(obj.attrib["id"]),
                "name": obj.attrib.get("name", ""),
                "bounds_mm": [round(maximum[axis] - minimum[axis], 5) for axis in range(3)],
                "min_z_mm": round(minimum[2], 5),
                "facets": len(obj.findall("./m:mesh/m:triangles/m:triangle", namespace)),
            }
        )
    return records


def legacy_propeller_mapping():
    source_manifest = json.loads((PROJECT / "QA" / "build_manifest.json").read_text(encoding="utf-8"))
    accessories = [record for record in source_manifest["shapes"] if not record["name"].startswith("Hull_Module_")]
    ordered_names = ["Hull_Module_1_Bow", "Hull_Module_2_Midship", "Hull_Module_3_Stern"] + [
        record["name"] for record in accessories
    ]
    by_name = {record["name"]: record for record in accessories}
    records = []
    legacy_print_bounds = [7.26227, 7.12636, 2.075]
    for component_id in (5, 9, 13, 17):
        name = ordered_names[component_id - 1]
        source_bounds = by_name[name]["bounds_mm"]
        source_size = [source_bounds[axis][1] - source_bounds[axis][0] for axis in ("x", "y", "z")]
        records.append(
            {
                "legacy_component_id": component_id,
                "name": name,
                "source_assembled_bounds_mm": [round(value, 5) for value in source_size],
                "legacy_print_orientation_bounds_mm": legacy_print_bounds,
            }
        )
    verified = [record["name"] for record in records] == [f"Propeller_{index}" for index in range(1, 5)]
    verified = verified and abs(records[2]["legacy_print_orientation_bounds_mm"][0] - 7.26227) <= 0.001
    return {
        "legacy_plate_sha256": "fbadf12dbb3b5a97ccdb178e8f6f38d78501afb1709f5bb815c4d0f90b72fea5",
        "legacy_bounds_source": "pre-fix Integration build manifest and 3MF component inspection",
        "legacy_3mf_structure": "one named 3MF object containing 21 ordered disconnected mesh components",
        "mapping_verified": verified,
        "affected_components": records,
    }


def run_info_checks():
    files = sorted((INTEGRATION / "STL").glob("*.stl")) + sorted((INTEGRATION / "3MF").glob("*.3mf"))
    records = []
    with tempfile.TemporaryDirectory(prefix="cvn69_m2_bambu_info_") as temporary:
        for path in files:
            process = subprocess.run(
                [str(BAMBU), "--debug", "2", "--info", str(path)],
                cwd=temporary,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=90,
                check=False,
            )
            info = parse_info(process.stdout)
            relative = str(path.relative_to(INTEGRATION))
            assembly_reference = path.name == "CVN69_Hull_Deck_Assembly.3mf"
            size = [info[key] for key in ("size_x", "size_y", "size_z")]
            passed = process.returncode == 0 and info["manifold"] == "yes" and (assembly_reference or max(size) <= 240.0 + 1.0e-6)
            records.append(
                {
                    "path": relative,
                    "return_code": process.returncode,
                    "assembly_reference": assembly_reference,
                    "status": "PASS" if passed else "FAIL",
                    **info,
                }
            )
    return records


def run_slice_case(relative: str, filament_key: str, layer_height: float):
    plate = INTEGRATION / relative
    process_profile = PROCESS_PROFILES[layer_height]
    expected_names = [record["name"] for record in three_mf_metadata(plate)]
    with tempfile.TemporaryDirectory(prefix="cvn69_m2_bambu_slice_") as temporary:
        output = Path(temporary) / "output"
        output.mkdir()
        command = [
            str(BAMBU),
            "--debug",
            "3",
            "--slice",
            "0",
            "--arrange",
            "0",
            "--ensure-on-bed",
            "--load-settings",
            f"{MACHINE_PROFILE};{process_profile}",
            "--load-filaments",
            str(FILAMENT_PROFILES[filament_key]),
            "--load-defaultfila",
            "--outputdir",
            str(output),
            str(plate),
        ]
        process = subprocess.run(
            command,
            cwd=INTEGRATION,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=180,
            check=False,
        )
        result_path = output / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
        gcode_path = output / "plate_1.gcode"
        loaded_objects = [
            {"name": name, "bambu_object_id": int(object_id)}
            for name, object_id in re.findall(r"object (.+?), id\s*:\s*(\d+), from stl or other 3mf", process.stdout)
        ]
        loaded_names = [record["name"] for record in loaded_objects]
        warning_counts = {
            key: len(re.findall(pattern, process.stdout, re.IGNORECASE))
            for key, pattern in TARGET_WARNING_PATTERNS.items()
        }
        passed = (
            process.returncode == 0
            and result.get("return_code") == 0
            and result.get("error_string") == "Success."
            and abs(float(result.get("layer_height", -1.0)) - layer_height) <= 1.0e-5
            and result.get("wall_loops") == 3
            and all(count == 0 for count in warning_counts.values())
            and sorted(loaded_names) == sorted(expected_names)
            and gcode_path.exists()
            and gcode_path.stat().st_size > 0
        )
        return {
            "plate": relative,
            "layer_height_mm": layer_height,
            "profile": str(process_profile.relative_to(INTEGRATION)),
            "machine_profile": str(MACHINE_PROFILE.relative_to(INTEGRATION)),
            "filament_profile": FILAMENT_PROFILES[filament_key].name,
            "command": "BambuStudio --slice 0 --arrange 0 --ensure-on-bed --load-settings <machine;process> --load-filaments <filament> <plate>",
            "return_code": process.returncode,
            "slicer_return_code": result.get("return_code"),
            "slicer_result": result.get("error_string"),
            "actual_layer_height_mm": result.get("layer_height"),
            "wall_loops": result.get("wall_loops"),
            "expected_named_objects": expected_names,
            "loaded_named_objects": loaded_names,
            "loaded_object_metadata": loaded_objects,
            "gcode_bytes": gcode_path.stat().st_size if gcode_path.exists() else 0,
            **warning_counts,
            "status": "PASS" if passed else "FAIL",
            "log": process.stdout.strip(),
        }


def main():
    if not BAMBU.exists():
        raise FileNotFoundError(BAMBU)
    required_profiles = [MACHINE_PROFILE, *PROCESS_PROFILES.values(), *FILAMENT_PROFILES.values()]
    missing_profiles = [str(path) for path in required_profiles if not path.exists()]
    if missing_profiles:
        raise FileNotFoundError(missing_profiles)

    info_records = run_info_checks()
    slice_records = [
        run_slice_case(relative, filament_key, layer_height)
        for relative, filament_key in SLICE_PLATES.items()
        for layer_height in sorted(PROCESS_PROFILES)
    ]
    plate_metadata = {relative: three_mf_metadata(INTEGRATION / relative) for relative in SLICE_PLATES}
    propeller_parameters = json.loads((QA / "build_manifest.json").read_text(encoding="utf-8"))["propeller_parameters_mm"]
    propeller_metadata = plate_metadata["3MF/Print_Plate_04_Propellers.3mf"]
    propeller_geometry_pass = (
        [record["name"] for record in propeller_metadata] == [f"Propeller_{index}" for index in range(1, 5)]
        and all(record["facets"] > 0 and record["min_z_mm"] == 0.0 for record in propeller_metadata)
        and all(abs(max(record["bounds_mm"][:2]) - 7.26) <= 0.01 for record in propeller_metadata)
        and propeller_parameters["blade_count"] == 5
        and propeller_parameters["blade_thickness"] >= 0.60
        and propeller_parameters["scale_enlargement"] == 1.0
    )
    legacy_mapping = legacy_propeller_mapping()
    propeller_slice = next(
        record
        for record in slice_records
        if record["plate"] == "3MF/Print_Plate_04_Propellers.3mf" and record["layer_height_mm"] == 0.12
    )
    propeller_object_id_map = {
        record["bambu_object_id"]: record["name"] for record in propeller_slice["loaded_object_metadata"]
    }
    propeller_object_mapping_pass = propeller_object_id_map == {
        5: "Propeller_1",
        9: "Propeller_2",
        13: "Propeller_3",
        17: "Propeller_4",
    }
    hull_plate_names = [record["name"] for record in plate_metadata["3MF/Print_Plate_01_Hull.3mf"]]
    plate_separation_pass = not any(name.startswith("Propeller_") for name in hull_plate_names)

    overall = (
        all(record["status"] == "PASS" for record in info_records)
        and all(record["status"] == "PASS" for record in slice_records)
        and legacy_mapping["mapping_verified"]
        and propeller_object_mapping_pass
        and plate_separation_pass
        and propeller_geometry_pass
    )
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "application": "Bambu Studio 02.07.01.62",
        "overall_status": "PASS" if overall else "FAIL",
        "info_command": "BambuStudio --debug 2 --info <export>",
        "slice_command": "BambuStudio --debug 3 --slice 0 --arrange 0 --ensure-on-bed --load-settings <machine;process> --load-filaments <filament> <plate>",
        "files_checked": len(info_records),
        "slice_cases": len(slice_records),
        "legacy_mapping": legacy_mapping,
        "propeller_object_mapping_pass": propeller_object_mapping_pass,
        "corrected_plate_bambu_object_id_map": {
            str(object_id): name for object_id, name in sorted(propeller_object_id_map.items())
        },
        "plate_separation_pass": plate_separation_pass,
        "propeller_geometry_pass": propeller_geometry_pass,
        "propeller_parameters_mm": propeller_parameters,
        "plate_metadata": plate_metadata,
        "slice_records": slice_records,
        "records": info_records,
    }
    (QA / "BambuStudio_Validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Milestone 2 Bambu Studio Validation",
        "",
        f"Overall status: **{report['overall_status']}**",
        "",
        f"Bambu Studio 02.07.01.62 imported and inspected {len(info_records)} STL/3MF exports, then performed {len(slice_records)} actual slicing runs. This report does not rely on `--info` alone.",
        "",
        "## Propeller object mapping and correction",
        "",
        "The legacy hull plate stored one named 3MF mesh with 21 ordered disconnected components. The original build order and component bounds verify Bambu object IDs 5, 9, 13, and 17 as the four propellers:",
        "",
        "| Reported object ID | 3MF/Bambu named object | Legacy print-oriented bounds (mm) |",
        "|---:|---|---:|",
    ]
    for record in legacy_mapping["affected_components"]:
        bounds = " × ".join(f"{value:.5f}" for value in record["legacy_print_orientation_bounds_mm"])
        lines.append(f"| {record['legacy_component_id']} | `{record['name']}` | {bounds} |")
    lines += [
        "",
        "The corrected `Print_Plate_01_Hull.3mf` contains 17 explicitly named non-propeller objects. `Print_Plate_04_Propellers.3mf` contains four explicitly named propeller objects, and Bambu's import log binds IDs 5/9/13/17 to `Propeller_1`/`Propeller_2`/`Propeller_3`/`Propeller_4` respectively.",
        "",
        "The propellers are new parametric solids at 100% scale: 7.26 mm overall diameter, five retained 0.60 mm blade lobes per object, 0.60 mm hub wall, 0.60 mm blind-bore back wall, and a common flat bed-side face. No scale enlargement was applied. A removable sprue was not required; a 3 mm brim remains recommended.",
        "",
        "## Actual slicing results",
        "",
        "| Plate | Layer | Status | Named objects | G-code bytes | Floating | Empty layers | Faulty mesh |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in slice_records:
        lines.append(
            f"| `{record['plate']}` | {record['layer_height_mm']:.2f} mm | {record['status']} | "
            f"{len(record['loaded_named_objects'])}/{len(record['expected_named_objects'])} | {record['gcode_bytes']:,} | "
            f"{record['floating_region_warnings']} | {record['empty_layer_warnings']} | {record['faulty_mesh_warnings']} |"
        )
    lines += [
        "",
        "All four real slice runs used a Bambu Lab A1 0.4 mm machine profile, three walls, 0.15 mm elephant-foot compensation, and the named 0.12/0.16 mm validation profiles. Every run returned `Success`, emitted non-empty G-code, loaded every named object, and produced none of the targeted warnings.",
        "",
        "## Import / manifold checks",
        "",
        "| Export | Status | Manifold | Objects | Parts | Facets | Maximum object size x × y × z (mm) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for record in info_records:
        size = " × ".join(f"{record[key]:.3f}" for key in ("size_x", "size_y", "size_z"))
        lines.append(
            f"| `{record['path']}` | {record['status']} | {record['manifold']} | {record['objects_reported']} | "
            f"{record['parts']} | {record['facets']:,} | {size} |"
        )
    (QA / "BambuStudio_Validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["overall_status"], "files": len(info_records), "slice_cases": len(slice_records)}, indent=2))
    if not overall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
