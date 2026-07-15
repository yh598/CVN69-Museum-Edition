#!/usr/bin/env python3
"""Validate the Milestone 6 evidence ledger against released parameters."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve(); M6 = SCRIPT.parents[1]
sys.path.insert(0, str(M6 / "CAD" / "Python"))
from deck_vehicle_parameters import make_parameters  # noqa: E402


def main():
    p = make_parameters(); audit = M6 / "References" / "Configuration_Audit.md"; text = audit.read_text(encoding="utf-8"); records=[]
    for item in p.families:
        checks={"code_listed":item.code in text,"evidence_url_listed":item.evidence_url in text,"dimension_url_listed":item.dimension_url in text,"classification_present":"derived" in text.lower() and "enlarged" in text.lower() and "not dimensionally exact" in text.lower(),"released_dimensions_positive":min(item.model_length,item.model_width,item.model_height)>0,"enlargements_documented":bool(item.enlargements)}
        records.append({"family":item.code,"name":item.name,"confidence":item.confidence,"checks":checks,"status":"PASS" if all(checks.values()) else "FAIL"})
    report={"generated_utc":datetime.now(timezone.utc).isoformat(),"configuration_period":p.configuration_period,"families":len(records),"records":records,"omitted_families_documented":"Omitted after audit" in text,"overall_status":"PASS" if all(r["status"]=="PASS" for r in records) and "Omitted after audit" in text else "FAIL"}
    (M6/"QA"/"Reference_Audit.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); print(json.dumps({"status":report["overall_status"],"families":len(records)},indent=2))
    if report["overall_status"]!="PASS": raise SystemExit(1)


if __name__=="__main__": main()
