#!/usr/bin/env python3
"""Validate the frozen configuration audit against the CAD parameter ledger."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
M5 = SCRIPT.parents[1]
sys.path.insert(0, str(M5 / "CAD" / "Python"))
from airwing_parameters import make_parameters  # noqa: E402


def main():
    p = make_parameters()
    audit = M5 / "References" / "Configuration_Audit.md"
    text = audit.read_text(encoding="utf-8")
    records = []
    for item in p.aircraft_types:
        checks = {
            "code_listed": item.code.split("_")[-1] in text or item.squadron in text,
            "evidence_url_listed": item.evidence_url in text,
            "dimension_url_listed": item.dimension_url in text,
            "model_dimensions_positive": item.model_length > 0 and item.model_span > 0,
        }
        records.append({"code": item.code, "squadron": item.squadron, "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"})
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "configuration_period": p.configuration_period,
        "aircraft_types": len(records),
        "records": records,
        "explicit_exclusions": ["E-2D", "CMV-22B", "F-35C"],
        "overall_status": "PASS" if all(r["status"] == "PASS" for r in records) else "FAIL",
    }
    out = M5 / "QA" / "Reference_Audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["overall_status"], "types": len(records)}, indent=2))
    if report["overall_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
