#!/usr/bin/env python3
"""Numerically and visually audit the source island mesh without reusing it."""

from __future__ import annotations

import hashlib
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
ISLAND = SCRIPT.parents[1]
IMAGES = ISLAND / "Images"
REFERENCES = ISLAND / "References"
IMAGES.mkdir(parents=True, exist_ok=True)
REFERENCES.mkdir(parents=True, exist_ok=True)
ARCHIVE = Path(
    os.environ.get(
        "CVN69_OPTIMIZED_ARCHIVE",
        str(Path.home() / "Downloads" / "CVN69_Optimized_v0_4_Glue_Only.zip"),
    )
)
MEMBER = "STL_MODEL/CVN69_1-700_section_02.stl"


def binary_triangles(data: bytes):
    if len(data) < 84:
        raise ValueError("STL is shorter than a binary header")
    count = struct.unpack_from("<I", data, 80)[0]
    if 84 + 50 * count != len(data):
        raise ValueError("Source reference is not the expected binary STL")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attr", "<u2")])
    records = np.frombuffer(data, dtype=dtype, count=count, offset=84)
    return records["vertices"].astype(np.float64), records["normal"].astype(np.float64)


def topology(triangles):
    flat = triangles.reshape(-1, 3)
    unique, inverse = np.unique(flat, axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    edges = np.sort(np.vstack((faces[:, (0, 1)], faces[:, (1, 2)], faces[:, (2, 0)])), axis=1)
    _edge_values, incidence = np.unique(edges, axis=0, return_counts=True)
    parent = np.arange(len(unique), dtype=np.int64)

    def find(index):
        index = int(index)
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = int(parent[index])
        return index

    def union(left, right):
        left, right = find(left), find(right)
        if left != right:
            parent[right] = left

    for left, right in edges:
        union(left, right)
    roots = np.asarray([find(face[0]) for face in faces])
    return unique, faces, roots, incidence


def render_reference(triangles, output: Path):
    centroid = triangles.mean(axis=1)
    mask = (
        (triangles[:, :, 2].max(axis=1) > 27.8)
        & (centroid[:, 0] > 116.0)
        & (centroid[:, 0] < 156.0)
        & (centroid[:, 1] > 13.0)
        & (centroid[:, 1] < 42.0)
    )
    subset = triangles[mask]
    fig, axes = plt.subplots(2, 2, figsize=(14, 11), dpi=180, facecolor="#111A21")
    projections = (
        ("Top — source x/y", (0, 1)),
        ("Longitudinal elevation — source x/z", (0, 2)),
        ("End elevation — source y/z", (1, 2)),
        ("Oblique reference", None),
    )
    for axis, (title, projection) in zip(axes.flat, projections):
        if projection is None:
            polygons = np.stack(
                (subset[:, :, 0] - 0.45 * subset[:, :, 1], subset[:, :, 2] + 0.18 * subset[:, :, 1]),
                axis=2,
            )
        else:
            polygons = subset[:, :, projection]
        z_mean = subset[:, :, 2].mean(axis=1)
        colors = (z_mean - z_mean.min()) / (np.ptp(z_mean) or 1.0)
        axis.add_collection(PolyCollection(polygons, array=colors, cmap="viridis", edgecolors="none"))
        axis.autoscale_view()
        axis.set_aspect("equal", adjustable="box")
        axis.set_title(title, color="#F1F4F5", fontsize=11)
        axis.set_facecolor("#111A21")
        axis.tick_params(colors="#B8C5CC", labelsize=7)
        for spine in axis.spines.values():
            spine.set_color("#3C4D57")
    fig.suptitle(
        "CVN-69 v0.4 SECTION 02 — ISLAND REFERENCE AUDIT\n"
        "source triangles shown only for measurement; no production geometry is reused",
        color="#F1F4F5",
        fontsize=16,
        weight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)
    points = subset.reshape(-1, 3)
    return {
        "facets_shown": int(len(subset)),
        "bounds_min_mm": [round(float(value), 5) for value in points.min(axis=0)],
        "bounds_max_mm": [round(float(value), 5) for value in points.max(axis=0)],
    }


def main():
    if not ARCHIVE.exists():
        raise FileNotFoundError(ARCHIVE)
    with zipfile.ZipFile(ARCHIVE) as archive:
        data = archive.read(MEMBER)
    triangles, normals = binary_triangles(data)
    unique, faces, roots, incidence = topology(triangles)
    lower = triangles.reshape(-1, 3).min(axis=0)
    upper = triangles.reshape(-1, 3).max(axis=0)
    crosses = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    area2 = np.linalg.norm(crosses, axis=1)
    stored_length = np.linalg.norm(normals, axis=1)
    usable = (area2 > 1.0e-12) & (stored_length > 1.0e-12)
    calculated = np.zeros_like(crosses)
    stored = np.zeros_like(normals)
    calculated[usable] = crosses[usable] / area2[usable, None]
    stored[usable] = normals[usable] / stored_length[usable, None]
    normal_mismatch = int(np.count_nonzero(usable & (np.einsum("ij,ij->i", calculated, stored) < 0.985)))

    image_path = IMAGES / "Source_Mesh_Island_Reference.png"
    subset = render_reference(triangles, image_path)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "archive": str(ARCHIVE),
        "archive_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        "member": MEMBER,
        "member_sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "facets": int(len(triangles)),
        "unique_vertices": int(len(unique)),
        "connected_components": int(len(np.unique(roots))),
        "bounds_min_mm": [round(float(value), 5) for value in lower],
        "bounds_max_mm": [round(float(value), 5) for value in upper],
        "size_mm": [round(float(value), 5) for value in upper - lower],
        "boundary_edges": int(np.count_nonzero(incidence == 1)),
        "non_manifold_edges": int(np.count_nonzero(incidence > 2)),
        "degenerate_facets": int(np.count_nonzero(area2 < 1.0e-10)),
        "normal_mismatches": normal_mismatch,
        "watertight": bool(np.all(incidence == 2)),
        "island_visual_subset": subset,
        "derived_reference": {
            "source_deck_top_estimate_mm": 27.80,
            "source_mast_top_mm": 71.33544,
            "height_above_deck_mm": 43.53544,
            "source_island_opening_x_mm": [121.0, 151.0],
            "authoritative_island_x_mm": [325.0, 355.0],
            "visible_transverse_extent_mm": [18.8, 35.85],
        },
        "production_use": "Dimensional and visual reference only; no triangle or repaired mesh is used by build_island.py.",
    }
    report_path = REFERENCES / "Source_Mesh_Island_Measurements.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "report": str(report_path), "image": str(image_path)}, indent=2))


if __name__ == "__main__":
    main()
