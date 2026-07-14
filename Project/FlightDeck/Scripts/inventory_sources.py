#!/usr/bin/env python3
"""Create numerical and visual inventories for every available source STL."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import struct
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection


SCRIPT = Path(__file__).resolve()
DECK_PROJECT = SCRIPT.parents[1]
ROOT_PROJECT = DECK_PROJECT.parent
QA = DECK_PROJECT / "QA"
QA.mkdir(parents=True, exist_ok=True)
ARCHIVE = Path(
    os.environ.get(
        "CVN69_OPTIMIZED_ARCHIVE",
        str(Path.home() / "Downloads" / "CVN69_Optimized_v0_4_Glue_Only.zip"),
    )
)


def binary_triangles(data: bytes):
    if len(data) < 84:
        raise ValueError("shorter than an STL header")
    count = struct.unpack_from("<I", data, 80)[0]
    if 84 + count * 50 != len(data):
        raise ValueError("not a supported binary STL")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attr", "<u2")])
    records = np.frombuffer(data, dtype=dtype, count=count, offset=84)
    return records["vertices"].astype(np.float64), records["normal"].astype(np.float64)


def topology_metrics(triangles, stored_normals):
    flat = triangles.reshape(-1, 3)
    unique, inverse = np.unique(flat, axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    edges = np.sort(
        np.vstack((faces[:, (0, 1)], faces[:, (1, 2)], faces[:, (2, 0)])),
        axis=1,
    )
    unique_edges, counts = np.unique(edges, axis=0, return_counts=True)

    parent = np.arange(len(unique), dtype=np.int64)
    rank = np.zeros(len(unique), dtype=np.int8)

    def find(index):
        index = int(index)
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = int(parent[index])
        return index

    def union(left, right):
        left, right = find(left), find(right)
        if left == right:
            return
        if rank[left] < rank[right]:
            left, right = right, left
        parent[right] = left
        if rank[left] == rank[right]:
            rank[left] += 1

    for left, right in unique_edges:
        union(left, right)
    components = len({find(index) for index in np.unique(faces)})

    crosses = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    double_area = np.linalg.norm(crosses, axis=1)
    degenerate = int(np.count_nonzero(double_area < 1.0e-10))
    calculated = np.zeros_like(crosses)
    usable = double_area > 1.0e-12
    calculated[usable] = crosses[usable] / double_area[usable, None]
    stored_lengths = np.linalg.norm(stored_normals, axis=1)
    stored = np.zeros_like(stored_normals)
    normal_usable = stored_lengths > 1.0e-12
    stored[normal_usable] = stored_normals[normal_usable] / stored_lengths[normal_usable, None]
    dots = np.einsum("ij,ij->i", calculated, stored)
    normal_mismatches = int(np.count_nonzero(usable & (dots < 0.985)))
    signed_volume = float(
        np.einsum("ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum() / 6.0
    )
    lower = flat.min(axis=0)
    upper = flat.max(axis=0)
    return {
        "facets": int(len(triangles)),
        "unique_vertices": int(len(unique)),
        "components": int(components),
        "bounds_min_mm": [round(float(value), 5) for value in lower],
        "bounds_max_mm": [round(float(value), 5) for value in upper],
        "size_mm": [round(float(value), 5) for value in upper - lower],
        "signed_volume_mm3": round(signed_volume, 4),
        "boundary_edges": int(np.count_nonzero(counts == 1)),
        "non_manifold_edges": int(np.count_nonzero(counts > 2)),
        "degenerate_facets": degenerate,
        "normal_mismatches": normal_mismatches,
        "watertight": bool(np.all(counts == 2)),
    }


def load_sources():
    sources = []
    for path in sorted((ROOT_PROJECT / "STL").glob("*.stl")):
        data = path.read_bytes()
        triangles, normals = binary_triangles(data)
        sources.append(
            {
                "source_set": "workspace_stl_package",
                "logical_path": str(path.relative_to(ROOT_PROJECT)),
                "data": data,
                "triangles": triangles,
                "normals": normals,
            }
        )
    if not ARCHIVE.exists():
        raise FileNotFoundError(f"Optimized source archive not found: {ARCHIVE}")
    with zipfile.ZipFile(ARCHIVE) as archive:
        for name in sorted(item for item in archive.namelist() if item.lower().endswith(".stl")):
            data = archive.read(name)
            triangles, normals = binary_triangles(data)
            sources.append(
                {
                    "source_set": "optimized_v0_4_archive",
                    "logical_path": name,
                    "data": data,
                    "triangles": triangles,
                    "normals": normals,
                }
            )
    return sources


def render_inventory(sources, output: Path, projection: str):
    columns = 4
    rows = int(np.ceil(len(sources) / columns))
    fig, axes = plt.subplots(rows, columns, figsize=(16, rows * 3.25), dpi=160, facecolor="#111A21")
    axes = np.asarray(axes).reshape(-1)
    for axis, source in zip(axes, sources):
        triangles = source["triangles"]
        z_mean = triangles[:, :, 2].mean(axis=1)
        z_span = np.ptp(z_mean)
        colors = (z_mean - z_mean.min()) / (z_span if z_span > 1.0e-12 else 1.0)
        if projection == "top":
            polygons = triangles[:, :, (0, 1)]
            x_label, y_label = "x", "y"
        else:
            x = triangles[:, :, 0]
            y = triangles[:, :, 1]
            z = triangles[:, :, 2]
            polygons = np.stack((x - 0.34 * y, z + 0.22 * y), axis=2)
            x_label, y_label = "oblique x", "oblique z"
        collection = PolyCollection(polygons, array=colors, cmap="viridis", edgecolors="none", linewidth=0)
        axis.add_collection(collection)
        axis.autoscale_view()
        axis.set_aspect("equal", adjustable="box")
        axis.set_facecolor("#111A21")
        axis.tick_params(colors="#A9BAC6", labelsize=5)
        for spine in axis.spines.values():
            spine.set_color("#34444F")
        stem = Path(source["logical_path"]).name
        metrics = source["metrics"]
        axis.set_title(
            f"{stem}\n{metrics['facets']:,} facets · {metrics['components']} components",
            fontsize=7.2,
            color="#E8EFF2",
            loc="left",
            pad=4,
        )
        axis.set_xlabel(x_label, color="#A9BAC6", fontsize=5.5)
        axis.set_ylabel(y_label, color="#A9BAC6", fontsize=5.5)
    for axis in axes[len(sources):]:
        axis.axis("off")
    title = "TOP PROJECTION" if projection == "top" else "ISOMETRIC / OBLIQUE PROJECTION"
    fig.suptitle(
        f"CVN-69 SOURCE STL INVENTORY — {title}\ncolor represents local z; geometry shown exactly as supplied",
        color="#F2F5F6",
        fontsize=15,
        weight="bold",
        y=0.997,
    )
    fig.tight_layout(rect=(0.015, 0.012, 0.99, 0.978))
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    sources = load_sources()
    records = []
    for source in sources:
        metrics = topology_metrics(source["triangles"], source["normals"])
        source["metrics"] = metrics
        records.append(
            {
                "source_set": source["source_set"],
                "logical_path": source["logical_path"],
                "bytes": len(source["data"]),
                "sha256": hashlib.sha256(source["data"]).hexdigest(),
                **metrics,
            }
        )

    top_path = QA / "Source_STL_Inventory_Top.png"
    iso_path = QA / "Source_STL_Inventory_Isometric.png"
    render_inventory(sources, top_path, "top")
    render_inventory(sources, iso_path, "isometric")

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "optimized_archive": str(ARCHIVE),
        "optimized_archive_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        "inventory_count": len(records),
        "source_sets": {
            "workspace_stl_package": sum(item["source_set"] == "workspace_stl_package" for item in records),
            "optimized_v0_4_archive": sum(item["source_set"] == "optimized_v0_4_archive" for item in records),
        },
        "files": records,
        "availability_note": (
            "Project/STL was the only pre-existing STL package in the workspace and is inventoried in full. "
            "No second original-source archive was present in the workspace or Downloads; the separately supplied "
            "optimized v0.4 archive is inventoried directly without altering its members."
        ),
    }
    json_path = QA / "Source_STL_Inventory.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    csv_path = QA / "Source_STL_Inventory.csv"
    fields = [
        "source_set",
        "logical_path",
        "bytes",
        "facets",
        "unique_vertices",
        "components",
        "size_x_mm",
        "size_y_mm",
        "size_z_mm",
        "signed_volume_mm3",
        "boundary_edges",
        "non_manifold_edges",
        "degenerate_facets",
        "normal_mismatches",
        "watertight",
        "sha256",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in records:
            writer.writerow(
                {
                    **{key: item[key] for key in fields if key in item},
                    "size_x_mm": item["size_mm"][0],
                    "size_y_mm": item["size_mm"][1],
                    "size_z_mm": item["size_mm"][2],
                }
            )

    md = [
        "# CVN-69 Source STL Inventory",
        "",
        f"Inventoried **{len(records)} STL files**: {report['source_sets']['workspace_stl_package']} in the workspace package and {report['source_sets']['optimized_v0_4_archive']} in the optimized v0.4 archive.",
        "",
        report["availability_note"],
        "",
        "The two PNG sheets are the required visual inventory. Numerical topology and hashes are preserved in the JSON and CSV companions.",
        "",
        "| Source | STL | Facets | Components | Size x × y × z (mm) | Boundary | Non-manifold | Watertight |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in records:
        size = " × ".join(f"{value:.3f}" for value in item["size_mm"])
        md.append(
            f"| {item['source_set']} | `{item['logical_path']}` | {item['facets']:,} | {item['components']} | {size} | {item['boundary_edges']} | {item['non_manifold_edges']} | {'yes' if item['watertight'] else 'no'} |"
        )
    md += [
        "",
        "## Reference interpretation used for reconstruction",
        "",
        "- Source longitudinal datum: x = 0 mm stern; x = 476 mm bow.",
        "- Positive y is starboard, confirmed by the island cluster at x ≈ 121–150 mm and y ≈ 19–36 mm.",
        "- The optimized model bands are intentionally retained as defective references: their disconnected components and non-manifold edges are reported, not repaired or reused.",
        "- Deck outline control points trace the supplied deck-cap silhouettes; missing x intervals between reference bands are faired parametrically.",
    ]
    (QA / "Source_STL_Inventory.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "files": len(records), "top": str(top_path), "isometric": str(iso_path)}, indent=2))


if __name__ == "__main__":
    main()
