#!/usr/bin/env python3
"""Generate high-resolution assembled, orthographic, and exploded renders."""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


SCRIPT = Path(__file__).resolve()
PROJECT = SCRIPT.parents[1]
OBJ = PROJECT / "OBJ" / "Hull.obj"

COLORS = {
    "ash_gray": np.array([0.56, 0.58, 0.55]),
    "charcoal": np.array([0.20, 0.22, 0.23]),
    "gold": np.array([0.78, 0.59, 0.19]),
    "silk_silver": np.array([0.67, 0.70, 0.72]),
}


def load_obj(path: Path):
    vertices = []
    faces = []
    current_material = "ash_gray"
    current_object = "unnamed"
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append(tuple(float(value) for value in parts[1:4]))
        elif parts[0] == "o":
            current_object = " ".join(parts[1:])
        elif parts[0] == "usemtl":
            current_material = parts[1]
        elif parts[0] == "f":
            indices = tuple(int(token.split("/")[0]) - 1 for token in parts[1:4])
            faces.append((indices, current_material, current_object))
    return np.asarray(vertices, dtype=float), faces


def triangles_by_material(vertices, faces, translations=None):
    groups = defaultdict(list)
    names = defaultdict(list)
    translations = translations or {}
    for indices, material, name in faces:
        triangle = vertices[list(indices)].copy()
        triangle += np.asarray(translations.get(name, (0.0, 0.0, 0.0)))
        groups[material].append(triangle)
        names[material].append(name)
    return {key: np.asarray(value) for key, value in groups.items()}


def shaded_colors(triangles, base_color):
    u = triangles[:, 1] - triangles[:, 0]
    w = triangles[:, 2] - triangles[:, 0]
    normals = np.cross(u, w)
    lengths = np.linalg.norm(normals, axis=1)
    lengths[lengths == 0.0] = 1.0
    normals /= lengths[:, None]
    light = np.asarray([-0.45, -0.25, 0.86])
    light /= np.linalg.norm(light)
    intensity = np.clip(0.62 + 0.38 * np.abs(normals @ light), 0.48, 1.0)
    rgba = np.ones((len(triangles), 4))
    rgba[:, :3] = np.clip(base_color[None, :] * intensity[:, None], 0.0, 1.0)
    return rgba


def configure_3d(ax, bounds, view=(24, -61)):
    xmin, ymin, zmin, xmax, ymax, zmax = bounds
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_zlim(zmin, zmax)
    ax.set_box_aspect((xmax - xmin, (ymax - ymin) * 1.35, (zmax - zmin) * 1.75))
    ax.view_init(elev=view[0], azim=view[1])
    ax.set_axis_off()
    ax.set_facecolor("#F5F3ED")
    ax.set_position([0.03, 0.075, 0.95, 0.80])


def render_isometric(vertices, faces, output: Path):
    groups = triangles_by_material(vertices, faces)
    fig = plt.figure(figsize=(16, 9), dpi=200, facecolor="#F5F3ED")
    ax = fig.add_subplot(111, projection="3d")
    for material, triangles in groups.items():
        collection = Poly3DCollection(
            triangles,
            facecolors=shaded_colors(triangles, COLORS[material]),
            edgecolors="none",
            linewidths=0,
            antialiased=False,
        )
        ax.add_collection3d(collection)
    configure_3d(ax, (-10, -42, -5, 486, 42, 39))
    fig.text(0.055, 0.91, "USS DWIGHT D. EISENHOWER (CVN-69)", fontsize=21, weight="bold", color="#252A2D")
    fig.text(0.057, 0.867, "MUSEUM EDITION  ·  MILESTONE 1 HULL  ·  1:700", fontsize=10.5, color="#526069")
    fig.text(0.057, 0.075, "PUBLIC-DATA, PRINT-ORIENTED NIMITZ-CLASS RECONSTRUCTION", fontsize=8.5, color="#68747B")
    fig.savefig(output, dpi=200, bbox_inches="tight", pad_inches=0.12, facecolor=fig.get_facecolor())
    plt.close(fig)


def render_exploded(vertices, faces, output: Path):
    translations = {
        "Hull_Module_2": (10.0, 0.0, 0.0),
        "Hull_Module_3": (20.0, 0.0, 0.0),
    }
    for _indices, _material, name in faces:
        if name.startswith(("Shaft_", "Propeller_", "Rudder_")):
            translations[name] = (22.0, 0.0, -12.0)
    groups = triangles_by_material(vertices, faces, translations)
    fig = plt.figure(figsize=(16, 9), dpi=200, facecolor="#F7F7F4")
    ax = fig.add_subplot(111, projection="3d")
    for material, triangles in groups.items():
        ax.add_collection3d(
            Poly3DCollection(
                triangles,
                facecolors=shaded_colors(triangles, COLORS[material]),
                edgecolors="none",
                linewidths=0,
                antialiased=False,
            )
        )
    configure_3d(ax, (-10, -45, -19, 510, 45, 40), view=(22, -60))
    fig.text(0.055, 0.91, "MILESTONE 1 — EXPLODED HULL ASSEMBLY", fontsize=21, weight="bold", color="#252A2D")
    fig.text(0.057, 0.867, "THREE KEYED HULL MODULES  ·  FOUR-SHAFT RUNNING GEAR  ·  TWIN RUDDERS", fontsize=10.5, color="#526069")
    fig.savefig(output, dpi=200, bbox_inches="tight", pad_inches=0.12, facecolor=fig.get_facecolor())
    plt.close(fig)


def add_projection(ax, groups, axes, title):
    for material, triangles in groups.items():
        polygons = triangles[:, :, list(axes)]
        ax.add_collection(
            PolyCollection(polygons, facecolor=COLORS[material], edgecolor="none", linewidth=0)
        )
    ax.autoscale_view()
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, loc="left", fontsize=12, weight="bold", color="#293138", pad=8)
    ax.set_facecolor("#FAFAF7")
    for spine in ax.spines.values():
        spine.set_color("#B8C0C3")
    ax.tick_params(labelsize=7, colors="#56636A")
    ax.grid(True, color="#E1E5E4", linewidth=0.4)
    ax.set_xlabel("LONGITUDINAL DATUM  x  [mm]", fontsize=7, color="#56636A")


def render_orthographic(vertices, faces, output: Path):
    groups = triangles_by_material(vertices, faces)
    fig, axes = plt.subplots(2, 1, figsize=(16, 9), dpi=200, facecolor="#F5F3ED")
    add_projection(axes[0], groups, (0, 1), "PLAN — HULL ENVELOPE / RUNNING GEAR")
    axes[0].set_ylabel("TRANSVERSE  y  [mm]", fontsize=7, color="#56636A")
    add_projection(axes[1], groups, (0, 2), "STARBOARD ELEVATION — WATERLINE / SPLIT DATUMS")
    axes[1].set_ylabel("VERTICAL  z  [mm]", fontsize=7, color="#56636A")
    axes[1].axhline(15.9, color="#315D77", linestyle=(0, (6, 4)), linewidth=1.0)
    for seam in (476.0 / 3.0, 952.0 / 3.0):
        axes[0].axvline(seam, color="#9A5A44", linestyle=(0, (2, 3)), linewidth=0.8)
        axes[1].axvline(seam, color="#9A5A44", linestyle=(0, (2, 3)), linewidth=0.8)
    axes[1].text(8, 17.1, "WATERLINE  z = 15.9 mm", fontsize=7, color="#315D77", ha="left", va="bottom")
    axes[1].annotate("", xy=(0, -4.0), xytext=(476, -4.0), arrowprops=dict(arrowstyle="<->", color="#293138", lw=0.8))
    axes[1].text(238, -3.55, "476.0 mm overall", ha="center", va="bottom", fontsize=8, color="#293138")
    axes[0].set_xlim(-6, 482)
    axes[0].set_ylim(-35, 35)
    axes[1].set_xlim(-6, 482)
    axes[1].set_ylim(-6, 35)
    fig.suptitle("CVN-69 MUSEUM EDITION  ·  HULL ORTHOGRAPHICS  ·  SCALE 1:700", x=0.065, y=0.97, ha="left", fontsize=17, weight="bold", color="#252A2D")
    fig.subplots_adjust(left=0.065, right=0.985, top=0.91, bottom=0.08, hspace=0.32)
    fig.savefig(output, dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    vertices, faces = load_obj(OBJ)
    render_isometric(vertices, faces, PROJECT / "Render" / "Hull_Isometric.png")
    render_orthographic(vertices, faces, PROJECT / "Render" / "Hull_Orthographic.png")
    render_exploded(vertices, faces, PROJECT / "Images" / "Hull_Exploded.png")
    print(f"Rendered {len(faces)} triangles from {OBJ}")


if __name__ == "__main__":
    main()
