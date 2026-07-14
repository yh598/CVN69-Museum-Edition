#!/usr/bin/env python3
"""Run Bambu Studio's independent CLI model-info/manifold check on exports."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
DECK_PROJECT = SCRIPT.parents[1]
QA = DECK_PROJECT / "QA"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")


def parse_info(output: str):
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


def main():
    if not BAMBU.exists():
        raise FileNotFoundError(BAMBU)
    files = sorted((DECK_PROJECT / "STL").glob("*.stl")) + sorted((DECK_PROJECT / "3MF").rglob("*.3mf"))
    records = []
    for path in files:
        process = subprocess.run(
            [str(BAMBU), "--debug", "2", "--info", str(path)],
            cwd=DECK_PROJECT.parents[1],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        info = parse_info(process.stdout)
        relative = str(path.relative_to(DECK_PROJECT))
        is_assembly_reference = path.name == "CVN69_Flight_Deck_Assembly.3mf"
        size = [info.get(key, float("inf")) for key in ("size_x", "size_y", "size_z")]
        passed = process.returncode == 0 and info["manifold"] == "yes" and (is_assembly_reference or max(size) <= 240.0 + 1.0e-6)
        records.append(
            {
                "path": relative,
                "return_code": process.returncode,
                "assembly_reference": is_assembly_reference,
                "status": "PASS" if passed else "FAIL",
                **info,
            }
        )

    overall = all(record["status"] == "PASS" for record in records)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "application": "Bambu Studio 02.07.01.62",
        "command": "BambuStudio --debug 2 --info <export>",
        "overall_status": "PASS" if overall else "FAIL",
        "files_checked": len(records),
        "records": records,
    }
    (QA / "BambuStudio_Validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Bambu Studio CLI Validation",
        "",
        f"Overall status: **{report['overall_status']}**",
        "",
        f"Bambu Studio 02.07.01.62 loaded and inspected {len(records)} exported STL/3MF files with its `--info` manifold check.",
        "",
        "| Export | Status | Manifold | Parts | Facets | Size x × y × z (mm) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for record in records:
        size = " × ".join(f"{record.get(key, 0.0):.3f}" for key in ("size_x", "size_y", "size_z"))
        lines.append(f"| `{record['path']}` | {record['status']} | {record['manifold']} | {record.get('parts', 0)} | {record.get('facets', 0):,} | {size} |")
    lines += [
        "",
        "Bambu Studio recenters models when reporting bounds, so bed contact is independently checked against the raw STL/3MF vertices in `Mesh_Validation.md`.",
    ]
    (QA / "BambuStudio_Validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["overall_status"], "files": len(records)}, indent=2))
    if not overall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
