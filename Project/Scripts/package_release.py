#!/usr/bin/env python3
"""Seal an immutable checksum manifest for the completed v0.1.0 release."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
PROJECT = SCRIPT.parents[1]
VERSION = "0.1.0"
RELEASE_DIR = PROJECT / "Releases" / f"v{VERSION}"
RELEASE_JSON = RELEASE_DIR / "RELEASE.json"
CHECKSUMS = RELEASE_DIR / "SHA256SUMS.txt"


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def included(path: Path):
    relative = path.relative_to(PROJECT)
    parts = relative.parts
    if not path.is_file():
        return False
    if "__pycache__" in parts or parts[:2] == ("QA", "tmp") or parts[0] == "Releases":
        return False
    return not path.name.startswith(".DS_Store")


def main():
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    if RELEASE_JSON.exists() or CHECKSUMS.exists():
        raise SystemExit(
            f"Release v{VERSION} is already sealed. Increment the semantic version; never overwrite it."
        )

    files = sorted(path for path in PROJECT.rglob("*") if included(path))
    artifacts = []
    for path in files:
        artifacts.append(
            {
                "path": str(path.relative_to(PROJECT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    validation = json.loads((PROJECT / "QA" / "validation_report.json").read_text(encoding="utf-8"))
    release = {
        "project": "USS Dwight D. Eisenhower (CVN-69) Museum Edition",
        "milestone": "Milestone 1 — Hull",
        "version": VERSION,
        "sealed_utc": datetime.now(timezone.utc).isoformat(),
        "status": validation["overall_status"],
        "validation_checks": len(validation["checks"]),
        "accuracy_class": "public-data, photo-informed, print-oriented reconstruction",
        "artifacts": artifacts,
    }
    RELEASE_JSON.write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    CHECKSUMS.write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in artifacts),
        encoding="utf-8",
    )
    print(json.dumps({"release": str(RELEASE_JSON), "status": release["status"], "artifacts": len(artifacts)}, indent=2))


if __name__ == "__main__":
    main()

