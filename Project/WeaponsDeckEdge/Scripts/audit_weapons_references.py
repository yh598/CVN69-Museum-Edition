#!/usr/bin/env python3
"""Cross-check the frozen public-reference audit against parametric counts."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


SCRIPT = Path(__file__).resolve()
M4 = SCRIPT.parents[1]
sys.path.insert(0, str(M4 / "CAD" / "Python"))
from weapons_deckedge_parameters import make_parameters  # noqa: E402


ALLOWED = {"www.navy.mil", "www.dvidshub.net", "www.navsea.navy.mil"}


def main():
    p = make_parameters()
    audit_path = M4 / "References" / "Configuration_Audit.md"
    text = audit_path.read_text(encoding="utf-8")
    urls = re.findall(r"https://[^)\s]+", text)
    checks = []
    for item in p.installations:
        checks.append({"check": f"installation:{item.name}", "status": "PASS" if item.name in text else "FAIL"})
        coordinate = f"{item.x:.1f} | {item.y:.1f} | {p.deck_top_z:.1f}"
        checks.append({"check": f"coordinate:{item.name}", "status": "PASS" if coordinate in text else "FAIL", "expected": coordinate})
    family_counts = {family: sum(item.family == family for item in p.installations) for family in ("CIWS", "RAM", "SeaSparrow")}
    checks.append({"check": "frozen_period", "status": "PASS" if "2023-10-14 through 2024-07-14" in text else "FAIL"})
    checks.append({"check": "access_date", "status": "PASS" if "2026-07-14" in text else "FAIL"})
    checks.append({"check": "public_url_count", "status": "PASS" if len(set(urls)) >= 10 else "FAIL", "count": len(set(urls))})
    checks.append({"check": "official_domains", "status": "PASS" if all(urlparse(url).netloc in ALLOWED for url in urls) else "FAIL", "domains": sorted({urlparse(url).netloc for url in urls})})
    checks.append({"check": "model_counts", "status": "PASS" if family_counts == {"CIWS": 2, "RAM": 2, "SeaSparrow": 2} else "FAIL", "counts": family_counts})
    checks.append({"check": "honesty_labels", "status": "PASS" if all(term in text for term in ("photo-derived", "visually approximated", "deliberately enlarged")) else "FAIL"})
    overall = all(item["status"] == "PASS" for item in checks)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "overall_status": "PASS" if overall else "FAIL",
        "configuration_period": p.configuration_period,
        "installation_count": len(p.installations),
        "family_counts": family_counts,
        "public_urls": sorted(set(urls)),
        "checks": checks,
    }
    output = M4 / "QA" / "Reference_Confidence_Report.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["overall_status"], "checks": len(checks), "urls": len(set(urls))}, indent=2))
    if not overall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
