#!/usr/bin/env python3
"""Run Bambu Studio import checks and real 0.12/0.16 mm M5 slices."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


SCRIPT = Path(__file__).resolve()
M5 = SCRIPT.parents[1]
PROJECT = M5.parent
QA = M5 / "QA"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
BAMBU_SYSTEM = Path.home() / "Library" / "Application Support" / "BambuStudio" / "system" / "BBL"
PROFILE_ROOT = PROJECT / "Integration" / "QA" / "Bambu_Profiles"
MACHINE = PROFILE_ROOT / "CVN69_A1_0p4_Machine_Validation.json"
PROCESSES = {
    0.12: PROFILE_ROOT / "CVN69_A1_0p12_Propeller_Validation.json",
    0.16: PROFILE_ROOT / "CVN69_A1_0p16_Propeller_Validation.json",
}
FILAMENT = BAMBU_SYSTEM / "filament" / "Bambu PLA Matte @BBL A1.json"
WARNING_PATTERNS = {
    "floating_region_warnings": r"floating regions?",
    "empty_layer_warnings": r"empty layers?|empty layer between",
    "faulty_mesh_warnings": r"faulty mesh",
}


def parse_info(output):
    def floats(key):
        return [float(value) for value in re.findall(rf"^{key}\s*=\s*([-+0-9.eE]+)", output, re.MULTILINE)]
    def integers(key):
        return [int(value) for value in re.findall(rf"^{key}\s*=\s*(\d+)", output, re.MULTILINE)]
    manifolds = [value.lower() for value in re.findall(r"^manifold\s*=\s*(\w+)", output, re.MULTILINE)]
    sizes = {axis: floats(f"size_{axis}") for axis in "xyz"}
    return {
        "objects_reported": len(manifolds),
        "size_x": max(sizes["x"], default=float("inf")),
        "size_y": max(sizes["y"], default=float("inf")),
        "size_z": max(sizes["z"], default=float("inf")),
        "facets": sum(integers("number_of_facets")), "parts": sum(integers("number_of_parts")),
        "manifold": "yes" if manifolds and all(value == "yes" for value in manifolds) else "no",
        "manifold_results": manifolds,
    }


def object_names(path):
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
    return [obj.attrib.get("name", "") for obj in root.findall("./m:resources/m:object", ns)]


def info_checks():
    files = sorted((M5 / "STL").glob("*.stl")) + sorted((M5 / "3MF").glob("*.3mf"))
    records = []
    with tempfile.TemporaryDirectory(prefix="cvn69_m5_info_") as temporary:
        for path in files:
            process = subprocess.run([str(BAMBU), "--debug", "2", "--info", str(path)], cwd=temporary, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90, check=False)
            info = parse_info(process.stdout)
            reference = path.name in {"CVN69_Hull_Deck_Island_Weapons_AirWing_Review.3mf", "CVN69_AirWing_Default_Layout.3mf"}
            passed = process.returncode == 0 and info["manifold"] == "yes" and (reference or max(info[key] for key in ("size_x", "size_y", "size_z")) <= 240.0 + 1.0e-6)
            records.append({"path": str(path.relative_to(M5)), "return_code": process.returncode, "reference": reference, "status": "PASS" if passed else "FAIL", **info})
    return records


def slice_case(path, layer):
    expected = object_names(path)
    with tempfile.TemporaryDirectory(prefix="cvn69_m5_slice_") as temporary:
        output = Path(temporary) / "output"
        output.mkdir()
        command = [
            str(BAMBU), "--debug", "3", "--slice", "0", "--arrange", "0", "--ensure-on-bed",
            "--load-settings", f"{MACHINE};{PROCESSES[layer]}",
            "--load-filaments", str(FILAMENT), "--load-defaultfila", "--outputdir", str(output), str(path),
        ]
        process = subprocess.run(command, cwd=M5, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240, check=False)
        result_path = output / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
        gcode = output / "plate_1.gcode"
        loaded = [name for name, _object_id in re.findall(r"object (.+?), id\s*:\s*(\d+), from stl or other 3mf", process.stdout)]
        warnings = {key: len(re.findall(pattern, process.stdout, re.IGNORECASE)) for key, pattern in WARNING_PATTERNS.items()}
        rotors_expected = [name for name in expected if "Rotor" in name]
        rotors_loaded = [name for name in loaded if "Rotor" in name]
        passed = (
            process.returncode == 0 and result.get("return_code") == 0 and result.get("error_string") == "Success."
            and abs(float(result.get("layer_height", -1))-layer) <= 1.0e-5 and result.get("wall_loops") == 3
            and all(value == 0 for value in warnings.values()) and sorted(loaded) == sorted(expected)
            and sorted(rotors_loaded) == sorted(rotors_expected) and gcode.exists() and gcode.stat().st_size > 0
        )
        return {
            "plate": str(path.relative_to(M5)), "layer_height_mm": layer,
            "return_code": process.returncode, "slicer_return_code": result.get("return_code"),
            "slicer_result": result.get("error_string"), "actual_layer_height_mm": result.get("layer_height"),
            "wall_loops": result.get("wall_loops"), "expected_named_objects": expected,
            "loaded_named_objects": loaded, "expected_rotors": rotors_expected, "loaded_rotors": rotors_loaded,
            "gcode_bytes": gcode.stat().st_size if gcode.exists() else 0, **warnings,
            "status": "PASS" if passed else "FAIL", "log": process.stdout.strip(),
        }


def main():
    required = [BAMBU, MACHINE, *PROCESSES.values(), FILAMENT]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(missing)
    info = info_checks()
    plates = sorted((M5 / "3MF").glob("Print_Plate_*.3mf"))
    slices = [slice_case(path, layer) for path in plates for layer in sorted(PROCESSES)]
    overall = all(record["status"] == "PASS" for record in info+slices)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(), "application": "Bambu Studio 02.07.01.62",
        "overall_status": "PASS" if overall else "FAIL", "files_checked": len(info),
        "production_plates": len(plates), "slice_cases": len(slices),
        "machine_profile": str(MACHINE.relative_to(PROJECT)),
        "process_profiles": {str(key): str(value.relative_to(PROJECT)) for key, value in PROCESSES.items()},
        "info_records": info, "slice_records": slices,
    }
    (QA / "BambuStudio_Validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Milestone 5 Bambu Studio validation", "", f"Overall status: **{report['overall_status']}**", "",
        f"Bambu Studio 02.07.01.62 imported {len(info)} STL/3MF exports and completed {len(slices)} real slice runs across {len(plates)} production plates. This is not an `--info`-only check.", "",
        "| Plate | Layer | Status | Objects | G-code bytes | Floating | Empty layers | Faulty mesh |", "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in slices:
        lines.append(f"| `{record['plate']}` | {record['layer_height_mm']:.2f} mm | {record['status']} | {len(record['loaded_named_objects'])}/{len(record['expected_named_objects'])} | {record['gcode_bytes']:,} | {record['floating_region_warnings']} | {record['empty_layer_warnings']} | {record['faulty_mesh_warnings']} |")
    lines += ["", "All cases use a 0.4 mm nozzle validation machine, three walls, and the requested 0.12/0.16 mm layers. Named rotor objects must load one-for-one, guarding against missing blades or omitted rotor meshes.", "", "## Import/manifold summary", "", "Every record is retained in `BambuStudio_Validation.json`, including dimensions, facets, parts, per-object manifold results, and raw slice logs."]
    (QA / "BambuStudio_Validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["overall_status"], "files": len(info), "production_plates": len(plates), "slice_cases": len(slices)}, indent=2))
    if not overall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
