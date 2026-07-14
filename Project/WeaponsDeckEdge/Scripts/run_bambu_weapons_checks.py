#!/usr/bin/env python3
"""Run Bambu Studio independent import/manifold checks for Milestone 4."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
M4 = SCRIPT.parents[1]
QA = M4 / "QA"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
REFERENCE_3MF = {"CVN69_Weapons_DeckEdge_Assembly.3mf", "CVN69_Hull_Deck_Island_Weapons_Review.3mf"}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_info(output):
    result = {"raw": output.strip()}
    patterns = {
        "size_x": r"^size_x\s*=\s*([-+0-9.eE]+)",
        "size_y": r"^size_y\s*=\s*([-+0-9.eE]+)",
        "size_z": r"^size_z\s*=\s*([-+0-9.eE]+)",
        "facets": r"^number_of_facets\s*=\s*(\d+)",
        "parts": r"^number_of_parts\s*=\s*(\d+)",
        "volume": r"^volume\s*=\s*([-+0-9.eE]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.MULTILINE)
        if match:
            result[key] = float(match.group(1)) if key in {"size_x", "size_y", "size_z", "volume"} else int(match.group(1))
    manifold = re.search(r"^manifold\s*=\s*(\w+)", output, re.MULTILINE)
    result["manifold"] = manifold.group(1).lower() if manifold else "missing"
    return result


def update_manifest(paths):
    manifest_path = QA / "build_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path in paths:
        manifest["outputs"][str(path.relative_to(M4))] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    if not BAMBU.exists():
        raise FileNotFoundError(BAMBU)
    files = sorted((M4 / "STL").glob("*.stl")) + sorted((M4 / "3MF").glob("*.3mf"))
    records = []
    with tempfile.TemporaryDirectory(prefix="cvn69_m4_bambu_") as temporary:
        for path in files:
            process = subprocess.run(
                [str(BAMBU), "--debug", "2", "--info", str(path)],
                cwd=temporary,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
                check=False,
            )
            info = parse_info(process.stdout)
            relative = str(path.relative_to(M4))
            reference = path.suffix.lower() == ".3mf" and path.name in REFERENCE_3MF
            sizes = [info.get(key, float("inf")) for key in ("size_x", "size_y", "size_z")]
            passed = process.returncode == 0 and info["manifold"] == "yes" and (reference or max(sizes) <= 240.0 + 1.0e-6)
            records.append({
                "path": relative,
                "return_code": process.returncode,
                "reference_assembly": reference,
                "status": "PASS" if passed else "FAIL",
                **info,
            })

    overall = all(record["status"] == "PASS" for record in records)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "application": "Bambu Studio 02.07.01.62",
        "command": "BambuStudio --debug 2 --info <export>",
        "printer_compatibility": ["Bambu Lab P2S", "Bambu Lab X1C", "Bambu Lab P1S", "Bambu Lab A1"],
        "overall_status": "PASS" if overall else "FAIL",
        "files_checked": len(records),
        "records": records,
    }
    json_path = QA / "BambuStudio_Validation.json"
    md_path = QA / "BambuStudio_Validation.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Milestone 4 Bambu Studio Validation",
        "",
        f"Overall status: **{report['overall_status']}**",
        "",
        f"Bambu Studio 02.07.01.62 independently loaded and inspected {len(records)} STL/3MF exports.",
        "",
        "| Export | Status | Manifold | Parts | Facets | Size x × y × z (mm) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for record in records:
        size = " × ".join(f"{record.get(key, 0.0):.3f}" for key in ("size_x", "size_y", "size_z"))
        suffix = " review/reference" if record["reference_assembly"] else ""
        lines.append(f"| `{record['path']}` | {record['status']}{suffix} | {record['manifold']} | {record.get('parts', 0)} | {record.get('facets', 0):,} | {size} |")
    lines += [
        "",
        "The assembly and integrated-review 3MFs are explicitly non-production references and are exempt only from the 240 mm print-bed envelope. Every object must still import and report manifold. Raw z=0, topology, ZIP/XML/CRC, and named-material checks are performed by the deterministic FreeCAD validator.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    update_manifest([json_path, md_path])
    print(json.dumps({"status": report["overall_status"], "files": len(records)}, indent=2))
    if not overall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
