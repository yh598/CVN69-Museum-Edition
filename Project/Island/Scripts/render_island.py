#!/usr/bin/env python3
"""Generate the 14 required Milestone 3 island and review renders."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon, Rectangle


SCRIPT = Path(__file__).resolve()
ISLAND = SCRIPT.parents[1]
PROJECT = ISLAND.parent
RENDER = ISLAND / "Render"
RENDER.mkdir(parents=True, exist_ok=True)
ISLAND_OBJ = ISLAND / "OBJ" / "CVN69_Island_Assembly.obj"
BASELINE_OBJ = PROJECT / "Integration" / "OBJ" / "CVN69_Hull_Deck_Assembly.obj"
MANIFEST_PATH = ISLAND / "QA" / "build_manifest.json"


COLORS = {
    "ash_gray": np.array([0.58, 0.59, 0.56]),
    "charcoal": np.array([0.20, 0.22, 0.24]),
    "deck_charcoal": np.array([0.20, 0.22, 0.24]),
    "silk_silver": np.array([0.69, 0.72, 0.74]),
    "ivory_white": np.array([0.93, 0.91, 0.85]),
    "basic_black": np.array([0.08, 0.09, 0.10]),
}
LABELS = {
    "ash_gray": "Matte Ash Gray — island / hull",
    "charcoal": "Matte Charcoal — windows / deck",
    "silk_silver": "Silk Silver — radar / antennas",
    "ivory_white": "Matte Ivory White — 69 markings",
    "basic_black": "Basic Black — signal housings",
}


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_obj(path: Path):
    vertices = []
    faces = []
    material = "ash_gray"
    object_name = "unnamed"
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append(tuple(float(value) for value in parts[1:4]))
        elif parts[0] == "o":
            object_name = "_".join(parts[1:])
        elif parts[0] == "usemtl":
            material = parts[1]
        elif parts[0] == "f":
            indices = tuple(int(token.split("/")[0]) - 1 for token in parts[1:4])
            faces.append((indices, material, object_name))
    return np.asarray(vertices, dtype=float), faces


def combine(left, right):
    left_vertices, left_faces = left
    right_vertices, right_faces = right
    offset = len(left_vertices)
    adjusted = [
        (tuple(index + offset for index in indices), "charcoal" if material == "deck_charcoal" else material, name)
        for indices, material, name in right_faces
    ]
    return np.vstack((left_vertices, right_vertices)), left_faces + adjusted


def legend_handles():
    return [
        Line2D([0], [0], marker="s", linestyle="", markersize=8, markerfacecolor=COLORS[key], markeredgecolor="none", label=label)
        for key, label in LABELS.items()
    ]


def face_arrays(vertices, faces, translations=None):
    translations = translations or {}
    triangles, materials, names = [], [], []
    for indices, material, name in faces:
        triangle = vertices[list(indices)].copy()
        triangle += np.asarray(translations.get(name, (0.0, 0.0, 0.0)))
        triangles.append(triangle)
        materials.append("charcoal" if material == "deck_charcoal" else material)
        names.append(name)
    return np.asarray(triangles), np.asarray(materials), np.asarray(names)


def shaded_colors(triangles, materials):
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    lengths[lengths == 0.0] = 1.0
    normals /= lengths[:, None]
    light = np.asarray([-0.42, -0.25, 0.87])
    light /= np.linalg.norm(light)
    intensity = np.clip(0.62 + 0.38 * np.abs(normals @ light), 0.46, 1.0)
    rgba = np.ones((len(triangles), 4))
    for material in np.unique(materials):
        base = COLORS.get(material, COLORS["ash_gray"])
        mask = materials == material
        rgba[mask, :3] = np.clip(base[None, :] * intensity[mask, None], 0.0, 1.0)
    return rgba


def projected_render(vertices, faces, output, title, subtitle, azimuth, elevation, translations=None, full_ship=False):
    triangles, materials, _names = face_arrays(vertices, faces, translations)
    azimuth_radians = math.radians(azimuth)
    elevation_radians = math.radians(elevation)
    camera = np.asarray(
        [
            math.cos(elevation_radians) * math.cos(azimuth_radians),
            math.cos(elevation_radians) * math.sin(azimuth_radians),
            math.sin(elevation_radians),
        ]
    )
    horizontal = np.asarray([-math.sin(azimuth_radians), math.cos(azimuth_radians), 0.0])
    vertical = np.asarray(
        [
            -math.sin(elevation_radians) * math.cos(azimuth_radians),
            -math.sin(elevation_radians) * math.sin(azimuth_radians),
            math.cos(elevation_radians),
        ]
    )
    projected = np.stack((triangles @ horizontal, triangles @ vertical), axis=2)
    depth = (triangles @ camera).mean(axis=1)
    order = np.argsort(depth)
    colors = shaded_colors(triangles, materials)
    figsize = (17, 8.2) if full_ship else (12.5, 9.2)
    fig, axis = plt.subplots(figsize=figsize, dpi=220, facecolor="#F2F0EA")
    axis.add_collection(PolyCollection(projected[order], facecolors=colors[order], edgecolors="none", linewidth=0, antialiased=False))
    axis.autoscale_view()
    axis.set_aspect("equal", adjustable="box")
    axis.axis("off")
    fig.suptitle(title, x=0.055, y=0.95, ha="left", fontsize=18, weight="bold", color="#20272A")
    fig.text(0.057, 0.905, subtitle, fontsize=9, color="#58646A")
    fig.legend(handles=legend_handles(), loc="lower center", bbox_to_anchor=(0.5, 0.035), ncol=5, frameon=False, fontsize=7.5)
    fig.subplots_adjust(left=0.035, right=0.99, top=0.87, bottom=0.11)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def orthographic_render(vertices, faces, output, title, subtitle, axes, sort_axis, reverse=False, limits=None, annotations=None, full_ship=False):
    triangles, materials, _names = face_arrays(vertices, faces)
    order = np.argsort(triangles[:, :, sort_axis].mean(axis=1))
    if reverse:
        order = order[::-1]
    polygons = triangles[:, :, axes][order]
    colors = np.asarray([COLORS.get(material, COLORS["ash_gray"]) for material in materials[order]])
    figsize = (17, 6.2) if full_ship else (12.5, 8.3)
    fig, axis = plt.subplots(figsize=figsize, dpi=220, facecolor="#F2F0EA")
    axis.add_collection(PolyCollection(polygons, facecolors=colors, edgecolors="none", linewidth=0, antialiased=False))
    axis.autoscale_view()
    axis.set_aspect("equal", adjustable="box")
    axis.set_facecolor("#E8E7E2")
    axis.grid(True, color="#C9CCC9", linewidth=0.35)
    axis.tick_params(labelsize=7, colors="#4D565A")
    for spine in axis.spines.values():
        spine.set_color("#8C969A")
    if limits:
        axis.set_xlim(*limits[0])
        axis.set_ylim(*limits[1])
    if annotations:
        annotations(axis)
    fig.suptitle(title, x=0.055, y=0.96, ha="left", fontsize=17, weight="bold", color="#20272A")
    fig.text(0.057, 0.914, subtitle, fontsize=8.5, color="#58646A")
    fig.legend(handles=legend_handles(), loc="lower center", bbox_to_anchor=(0.5, 0.03), ncol=5, frameon=False, fontsize=7.5)
    fig.subplots_adjust(left=0.065, right=0.985, top=0.87, bottom=0.15)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def island_side_annotations(axis):
    axis.axhline(34.5, color="#C46A50", linestyle=(0, (5, 3)), linewidth=0.8)
    axis.text(324.2, 35.0, "approved deck top z = 34.50 mm", fontsize=7, color="#A6533B")
    axis.annotate("", xy=(368.8, 34.5), xytext=(368.8, 78.0), arrowprops=dict(arrowstyle="<->", color="#39474E", lw=0.8))
    axis.text(369.3, 56.0, "43.50 mm mast height", rotation=90, va="center", fontsize=7.5, color="#39474E")
    axis.set_xlabel("authoritative longitudinal x [mm] — bow left / stern right")
    axis.set_ylabel("vertical z [mm]")


def island_end_annotations(axis):
    axis.axhline(34.5, color="#C46A50", linestyle=(0, (5, 3)), linewidth=0.8)
    axis.set_xlabel("port (−y) / starboard (+y) [mm]")
    axis.set_ylabel("vertical z [mm]")


def island_top_annotations(axis):
    axis.text(324.5, 17.8, "BOW", fontsize=8, weight="bold")
    axis.text(366.5, 17.8, "STERN", fontsize=8, weight="bold", ha="right")
    axis.set_xlabel("authoritative longitudinal x [mm]")
    axis.set_ylabel("port (−y) / starboard (+y) [mm]")


def ship_side_annotations(axis):
    axis.axhline(34.5, color="#C46A50", linestyle=(0, (5, 3)), linewidth=0.7)
    axis.text(8, 35.2, "flight-deck top z = 34.50 mm", fontsize=6.8, color="#A6533B")
    axis.text(2, 80.0, "BOW", fontsize=7.5, weight="bold")
    axis.text(474, 80.0, "STERN", fontsize=7.5, weight="bold", ha="right")
    axis.set_xlabel("authoritative longitudinal x [mm]")
    axis.set_ylabel("vertical z [mm]")


def ship_top_annotations(axis):
    axis.annotate("", xy=(0, -44), xytext=(476, -44), arrowprops=dict(arrowstyle="<->", color="#39474E", lw=0.8))
    axis.text(238, -42.8, "476.00 mm", ha="center", fontsize=8)
    axis.text(2, 43, "BOW", fontsize=7.5, weight="bold")
    axis.text(474, 43, "STERN", fontsize=7.5, weight="bold", ha="right")
    axis.set_xlabel("authoritative longitudinal x [mm]")
    axis.set_ylabel("port (−y) / starboard (+y) [mm]")


def interface_section(output: Path, manifest):
    p = manifest["parameters_mm"]
    fig, axis = plt.subplots(figsize=(12, 8), dpi=220, facecolor="#F2F0EA")
    axis.set_facecolor("#E8E7E2")
    # Local transverse section, not a shipyard drawing.  Dimensions are the
    # production CAD interface values.
    axis.add_patch(Rectangle((-18, 31.5), 13.75, 3.0, facecolor=COLORS["charcoal"], edgecolor="#273036", linewidth=0.9))
    axis.add_patch(Rectangle((4.25, 31.5), 13.75, 3.0, facecolor=COLORS["charcoal"], edgecolor="#273036", linewidth=0.9))
    axis.add_patch(Rectangle((-4.0, 32.1), 8.0, 3.9, facecolor=COLORS["ash_gray"], edgecolor="#273036", linewidth=1.0))
    axis.add_patch(Rectangle((-5.15, 34.5), 10.3, 1.5, facecolor=COLORS["ash_gray"], edgecolor="#273036", linewidth=1.0))
    axis.add_patch(Rectangle((-5.15, 34.5), 1.35, 0.35, facecolor="#E8E7E2", edgecolor="#A6533B", linewidth=0.7))
    axis.add_patch(Rectangle((3.8, 34.5), 1.35, 0.35, facecolor="#E8E7E2", edgecolor="#A6533B", linewidth=0.7))
    axis.annotate("", xy=(-4.25, 30.8), xytext=(-4.0, 30.8), arrowprops=dict(arrowstyle="<->", color="#A6533B"))
    axis.text(-4.125, 30.25, "0.25 mm/side", ha="center", fontsize=8, color="#A6533B")
    axis.annotate("", xy=(6.3, 32.1), xytext=(6.3, 34.5), arrowprops=dict(arrowstyle="<->", color="#39474E"))
    axis.text(6.8, 33.3, "2.40 mm plug", va="center", fontsize=8)
    axis.annotate("", xy=(9.7, 34.5), xytext=(9.7, 36.0), arrowprops=dict(arrowstyle="<->", color="#39474E"))
    axis.text(10.2, 35.25, "1.50 mm hidden flange", va="center", fontsize=8)
    axis.text(-17.4, 32.0, "approved deck\n3.00 mm", fontsize=8, color="#F2F0EA", weight="bold")
    axis.text(-1.9, 37.1, "island body continues upward", fontsize=8.5, weight="bold")
    axis.text(-5.0, 33.7, "asymmetric plug derived from approved opening", fontsize=8, color="#39474E")
    axis.text(-5.0, 36.2, "0.60 × 0.35 mm hidden open glue channel", fontsize=8, color="#A6533B")
    axis.set_xlim(-19, 19)
    axis.set_ylim(29.5, 39)
    axis.set_aspect("equal", adjustable="box")
    axis.grid(True, color="#C9CCC9", linewidth=0.35)
    axis.set_xlabel("local opening section [mm]")
    axis.set_ylabel("authoritative z [mm]")
    fig.suptitle("CVN-69 ISLAND FOUNDATION / DECK INTERFACE SECTION", x=0.06, y=0.95, ha="left", fontsize=16.5, weight="bold", color="#20272A")
    fig.text(0.062, 0.902, "GLUE-ONLY · ASYMMETRIC SELF-ALIGNMENT · ALL GEOMETRY HIDDEN AFTER SEATING", fontsize=8.5, color="#58646A")
    fig.subplots_adjust(left=0.08, right=0.97, top=0.86, bottom=0.12)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def update_manifest(paths):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for path in paths:
        manifest["outputs"][str(path.relative_to(ISLAND))] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    island = load_obj(ISLAND_OBJ)
    baseline = load_obj(BASELINE_OBJ)
    combined = combine(baseline, island)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    island_vertices, island_faces = island
    combined_vertices, combined_faces = combined
    outputs = {
        "port": RENDER / "Island_Port.png",
        "starboard": RENDER / "Island_Starboard.png",
        "forward": RENDER / "Island_Forward.png",
        "aft": RENDER / "Island_Aft.png",
        "top": RENDER / "Island_Top.png",
        "bow_iso": RENDER / "Island_Bow_Isometric.png",
        "stern_iso": RENDER / "Island_Stern_Isometric.png",
        "exploded": RENDER / "Island_Exploded.png",
        "interface": RENDER / "Island_Interface_Section.png",
        "ship_port": RENDER / "CVN69_Hull_Deck_Island_Port.png",
        "ship_starboard": RENDER / "CVN69_Hull_Deck_Island_Starboard.png",
        "ship_top": RENDER / "CVN69_Hull_Deck_Island_Top.png",
        "ship_bow": RENDER / "CVN69_Hull_Deck_Island_Bow_Isometric.png",
        "ship_stern": RENDER / "CVN69_Hull_Deck_Island_Stern_Isometric.png",
    }
    island_limits_side = ((322.5, 371.5), (30.5, 81.5))
    island_limits_end = ((16.0, 38.0), (30.5, 81.5))
    orthographic_render(island_vertices, island_faces, outputs["port"], "CVN-69 ISLAND · PORT", "MILESTONE 3 · 2023–2024 DEPLOYMENT FIT · PHOTO-INFORMED RECONSTRUCTION", (0, 2), 1, True, island_limits_side, island_side_annotations)
    orthographic_render(island_vertices, island_faces, outputs["starboard"], "CVN-69 ISLAND · STARBOARD", "WINDOW INSERTS, RADAR ARRAYS, RAILINGS, AND IDENTIFICATION SHOWN AS SEPARATE OBJECTS", (0, 2), 1, False, island_limits_side, island_side_annotations)
    orthographic_render(island_vertices, island_faces, outputs["forward"], "CVN-69 ISLAND · FORWARD", "AUTHORITATIVE SHIP VIEW FROM THE BOW", (1, 2), 0, True, island_limits_end, island_end_annotations)
    orthographic_render(island_vertices, island_faces, outputs["aft"], "CVN-69 ISLAND · AFT", "AUTHORITATIVE SHIP VIEW FROM THE STERN", (1, 2), 0, False, island_limits_end, island_end_annotations)
    orthographic_render(island_vertices, island_faces, outputs["top"], "CVN-69 ISLAND · TOP", "FOUNDATION DERIVED FROM THE APPROVED ASYMMETRIC DECK OPENING", (0, 1), 2, False, ((322.5, 371.5), (16.0, 38.5)), island_top_annotations)
    projected_render(island_vertices, island_faces, outputs["bow_iso"], "CVN-69 ISLAND · BOW-SIDE ISOMETRIC", "17 MAJOR GLUE-ASSEMBLED PARTS · 0.4 MM NOZZLE · PLA", -145, 26)
    projected_render(island_vertices, island_faces, outputs["stern_iso"], "CVN-69 ISLAND · STERN-SIDE ISOMETRIC", "NO-PAINT OBJECT COLOR DESIGN · PUBLIC-REFERENCE CONFIGURATION", 35, 26)

    role_by_name = {item["name"]: item["role"] for item in manifest["parts"]}
    translations = {}
    for name, role in role_by_name.items():
        if role in {"navigation_bridge", "primary_flight_control", "exhaust_uptake"}:
            translations[name] = (0.0, 0.0, 5.0)
        elif role in {"main_mast", "secondary_mast", "yardarm"}:
            translations[name] = (0.0, 0.0, 14.0)
        elif role in {"radar_array", "antenna_set", "signal_lights"}:
            translations[name] = (0.0, 0.0, 23.0)
        elif role in {"window_insert", "identification_marking", "ladder"}:
            translations[name] = (0.0, 4.0, 8.0)
    projected_render(island_vertices, island_faces, outputs["exploded"], "CVN-69 MILESTONE 3 · EXPLODED ISLAND", "FOUNDATION · BRIDGE / PRI-FLY / UPTAKE · MASTS · RADAR · COLOR INSERTS", -140, 22, translations)
    interface_section(outputs["interface"], manifest)

    ship_limits_side = ((-7, 483), (-8, 83))
    orthographic_render(combined_vertices, combined_faces, outputs["ship_port"], "CVN-69 HULL–DECK–ISLAND REVIEW · PORT", "NON-PRODUCTION INTERFERENCE / PROPORTION REVIEW", (0, 2), 1, True, ship_limits_side, ship_side_annotations, True)
    orthographic_render(combined_vertices, combined_faces, outputs["ship_starboard"], "CVN-69 HULL–DECK–ISLAND REVIEW · STARBOARD", "APPROVED MILESTONE 2 BASELINE + NEW MILESTONE 3 ISLAND", (0, 2), 1, False, ship_limits_side, ship_side_annotations, True)
    orthographic_render(combined_vertices, combined_faces, outputs["ship_top"], "CVN-69 HULL–DECK–ISLAND REVIEW · TOP", "476.00 MM OVERALL · AUTHORITATIVE COORDINATE SYSTEM", (0, 1), 2, False, ((-7, 483), (-48, 48)), ship_top_annotations, True)
    projected_render(combined_vertices, combined_faces, outputs["ship_bow"], "CVN-69 HULL–DECK–ISLAND REVIEW · BOW ISOMETRIC", "MILESTONE 3 REVIEW ASSEMBLY · WEAPONS AND AIRCRAFT OUT OF SCOPE", -145, 27, full_ship=True)
    projected_render(combined_vertices, combined_faces, outputs["ship_stern"], "CVN-69 HULL–DECK–ISLAND REVIEW · STERN ISOMETRIC", "APPROVED HULL / DECK UNCHANGED · ISLAND SEATED IN APPROVED OPENING", 35, 27, full_ship=True)
    update_manifest(list(outputs.values()))
    print(json.dumps({"status": "ok", "renders": {key: str(path) for key, path in outputs.items()}}, indent=2))


if __name__ == "__main__":
    main()
