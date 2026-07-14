#!/usr/bin/env python3
"""Render the assembled flight-deck BRep export from its OBJ tessellation."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


SCRIPT = Path(__file__).resolve()
DECK_PROJECT = SCRIPT.parents[1]
OBJ = DECK_PROJECT / "OBJ" / "CVN69_Flight_Deck_Assembly.obj"
RENDER = DECK_PROJECT / "Render"
RENDER.mkdir(parents=True, exist_ok=True)

COLORS = {
    "deck_charcoal": np.array([0.20, 0.22, 0.24]),
    "elevator_gray": np.array([0.40, 0.43, 0.46]),
    "marking_white": np.array([0.94, 0.94, 0.90]),
    "track_silver": np.array([0.68, 0.71, 0.73]),
    "wire_yellow": np.array([0.84, 0.70, 0.16]),
}


def load_obj(path: Path):
    vertices = []
    faces = []
    material = "deck_charcoal"
    object_name = "unnamed"
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append(tuple(float(value) for value in parts[1:4]))
        elif parts[0] == "o":
            object_name = " ".join(parts[1:])
        elif parts[0] == "usemtl":
            material = parts[1]
        elif parts[0] == "f":
            indices = tuple(int(token.split("/")[0]) - 1 for token in parts[1:4])
            faces.append((indices, material, object_name))
    return np.asarray(vertices, dtype=float), faces


def grouped_triangles(vertices, faces):
    groups = defaultdict(list)
    for indices, material, _name in faces:
        groups[material].append(vertices[list(indices)])
    return {key: np.asarray(value) for key, value in groups.items()}


def shaded_colors(triangles, base):
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    lengths[lengths == 0.0] = 1.0
    normals /= lengths[:, None]
    light = np.asarray([-0.36, -0.28, 0.89])
    light /= np.linalg.norm(light)
    intensity = np.clip(0.62 + 0.38 * np.abs(normals @ light), 0.48, 1.0)
    rgba = np.ones((len(triangles), 4))
    rgba[:, :3] = np.clip(base[None, :] * intensity[:, None], 0.0, 1.0)
    return rgba


def legend_handles():
    labels = {
        "deck_charcoal": "main deck modules",
        "elevator_gray": "elevators",
        "marking_white": "raised markings",
        "track_silver": "catapult tracks",
        "wire_yellow": "arresting wires",
    }
    return [
        Line2D([0], [0], marker="s", linestyle="", markersize=8, markerfacecolor=COLORS[key], markeredgecolor="none", label=label)
        for key, label in labels.items()
    ]


def render_top(groups, output: Path):
    fig, axis = plt.subplots(figsize=(17, 6.3), dpi=220, facecolor="#F2F0EA")
    axis.set_facecolor("#E8E7E2")
    for material in ("deck_charcoal", "elevator_gray", "marking_white", "track_silver", "wire_yellow"):
        triangles = groups.get(material)
        if triangles is None:
            continue
        axis.add_collection(
            PolyCollection(triangles[:, :, (0, 1)], facecolor=COLORS[material], edgecolor="none", linewidth=0)
        )
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlim(-8, 484)
    axis.set_ylim(-48, 48)
    axis.grid(True, color="#C8CBC8", linewidth=0.35)
    for seam in (190.0, 330.0):
        axis.axvline(seam, color="#CA795F", linestyle=(0, (4, 3)), linewidth=0.8)
        axis.text(seam, 42.5, f"split x={seam:.0f}", ha="center", va="bottom", fontsize=7.5, color="#9C4D37")
    axis.annotate("", xy=(0, -43.0), xytext=(476, -43.0), arrowprops=dict(arrowstyle="<->", color="#22292D", lw=0.9))
    axis.text(238, -41.8, "476.00 mm overall", ha="center", va="bottom", fontsize=9, color="#22292D")
    axis.text(1.5, 40.5, "STERN", fontsize=8, weight="bold", color="#31383C")
    axis.text(474.5, 40.5, "BOW", ha="right", fontsize=8, weight="bold", color="#31383C")
    axis.text(136, 25.8, "ISLAND OPENING", ha="center", fontsize=6.8, color="#E3E5E1", weight="bold")
    axis.set_xlabel("longitudinal datum x [mm]", fontsize=8, color="#4D565A")
    axis.set_ylabel("transverse datum y [mm]", fontsize=8, color="#4D565A")
    axis.tick_params(labelsize=7, colors="#4D565A")
    axis.legend(handles=legend_handles(), loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=5, frameon=False, fontsize=8)
    fig.suptitle("USS DWIGHT D. EISENHOWER (CVN-69) · RECONSTRUCTED FLIGHT DECK · TOP VIEW", x=0.055, y=0.965, ha="left", fontsize=15.5, weight="bold", color="#20272A")
    fig.text(0.056, 0.915, "1:700 · CLEAN PARAMETRIC BREP · SOURCE MESH USED ONLY AS REFERENCE", fontsize=8.5, color="#58646A")
    fig.subplots_adjust(left=0.045, right=0.99, top=0.88, bottom=0.20)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def render_isometric(groups, output: Path):
    fig = plt.figure(figsize=(17, 7.5), dpi=220, facecolor="#F2F0EA")
    axis = fig.add_subplot(111, projection="3d", computed_zorder=False)
    for zorder, material in enumerate(("deck_charcoal", "elevator_gray", "marking_white", "track_silver", "wire_yellow"), 1):
        triangles = groups.get(material)
        if triangles is None:
            continue
        collection = Poly3DCollection(
                triangles,
                facecolors=shaded_colors(triangles, COLORS[material]),
                edgecolors="none",
                linewidths=0,
                antialiased=False,
            )
        collection.set_zorder(zorder)
        axis.add_collection3d(collection)
    axis.set_xlim(-4, 480)
    axis.set_ylim(-42, 42)
    axis.set_zlim(-0.15, 5.0)
    # The z aspect is enlarged only for legibility of the true 0.35 mm raised details.
    axis.set_box_aspect((7.0, 2.35, 0.55), zoom=1.52)
    axis.set_proj_type("ortho")
    axis.view_init(elev=62, azim=-68)
    axis.set_axis_off()
    axis.set_facecolor("#F2F0EA")
    axis.set_position([0.02, 0.12, 0.97, 0.73])
    fig.suptitle("CVN-69 FLIGHT-DECK RECONSTRUCTION · ISOMETRIC", x=0.055, y=0.94, ha="left", fontsize=17, weight="bold", color="#20272A")
    fig.text(0.057, 0.892, "THREE GLUE-KEYED MODULES · FOUR REMOVABLE ELEVATORS · SEPARATE RAISED DETAIL SOLIDS", fontsize=9, color="#58646A")
    fig.text(0.057, 0.105, "DISPLAY NOTE: vertical aspect enlarged for visibility; model dimensions and exported geometry are not scaled in z.", fontsize=7.8, color="#667177")
    fig.legend(handles=legend_handles(), loc="lower center", bbox_to_anchor=(0.5, 0.035), ncol=5, frameon=False, fontsize=8)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    vertices, faces = load_obj(OBJ)
    groups = grouped_triangles(vertices, faces)
    top = RENDER / "CVN69_Flight_Deck_Top.png"
    iso = RENDER / "CVN69_Flight_Deck_Isometric.png"
    render_top(groups, top)
    render_isometric(groups, iso)
    print(f"Rendered {len(faces):,} triangles to {top} and {iso}")


if __name__ == "__main__":
    main()
