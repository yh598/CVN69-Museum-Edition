#!/usr/bin/env python3
"""Render Milestone 2 assembled, exploded, side, and interface views."""

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
from matplotlib.patches import Rectangle


SCRIPT = Path(__file__).resolve()
INTEGRATION = SCRIPT.parents[1]
OBJ = INTEGRATION / "OBJ" / "CVN69_Hull_Deck_Assembly.obj"
MANIFEST_PATH = INTEGRATION / "QA" / "build_manifest.json"
RENDER = INTEGRATION / "Render"
RENDER.mkdir(parents=True, exist_ok=True)

COLORS = {
    "ash_gray": np.array([0.56, 0.58, 0.55]),
    "deck_charcoal": np.array([0.20, 0.22, 0.24]),
    "ivory_white": np.array([0.92, 0.90, 0.84]),
    "silk_silver": np.array([0.68, 0.71, 0.73]),
}
LABELS = {
    "ash_gray": "hull / interface pads",
    "deck_charcoal": "flight deck / elevators",
    "ivory_white": "raised markings",
    "silk_silver": "metallic details",
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
            object_name = " ".join(parts[1:])
        elif parts[0] == "usemtl":
            material = parts[1]
        elif parts[0] == "f":
            indices = tuple(int(token.split("/")[0]) - 1 for token in parts[1:4])
            faces.append((indices, material, object_name))
    return np.asarray(vertices, dtype=float), faces


def legend_handles():
    return [
        Line2D([0], [0], marker="s", linestyle="", markersize=8, markerfacecolor=COLORS[key], markeredgecolor="none", label=LABELS[key])
        for key in COLORS
    ]


def face_arrays(vertices, faces, translations=None):
    translations = translations or {}
    triangles = []
    materials = []
    names = []
    for indices, material, name in faces:
        triangle = vertices[list(indices)].copy()
        triangle += np.asarray(translations.get(name, (0.0, 0.0, 0.0)))
        triangles.append(triangle)
        materials.append(material)
        names.append(name)
    return np.asarray(triangles), np.asarray(materials), np.asarray(names)


def shade(triangles, materials, camera):
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    lengths[lengths == 0] = 1.0
    normals /= lengths[:, None]
    light = np.asarray([-0.35, -0.25, 0.90])
    light /= np.linalg.norm(light)
    intensity = np.clip(0.60 + 0.40 * np.abs(normals @ light), 0.44, 1.0)
    rgba = np.ones((len(triangles), 4))
    for key, base in COLORS.items():
        mask = materials == key
        rgba[mask, :3] = np.clip(base[None, :] * intensity[mask, None], 0.0, 1.0)
    return rgba


def projected_render(vertices, faces, output, title, subtitle, azimuth, elevation, translations=None):
    triangles, materials, _names = face_arrays(vertices, faces, translations)
    az = math.radians(azimuth)
    el = math.radians(elevation)
    camera = np.asarray([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    horizontal = np.asarray([-math.sin(az), math.cos(az), 0.0])
    vertical = np.asarray([-math.sin(el) * math.cos(az), -math.sin(el) * math.sin(az), math.cos(el)])
    projected = np.stack((triangles @ horizontal, triangles @ vertical), axis=2)
    depth = (triangles @ camera).mean(axis=1)
    all_colors = shade(triangles, materials, camera)
    fig, axis = plt.subplots(figsize=(17, 8.2), dpi=210, facecolor="#F2F0EA")
    # For an above-deck camera, material layers are also physical vertical
    # layers. Drawing hull, deck, markings, and metal in that order prevents
    # long hull triangles from bleeding through the deck in a painter render.
    for material in ("ash_gray", "deck_charcoal", "ivory_white", "silk_silver"):
        indices = np.flatnonzero(materials == material)
        order = indices[np.argsort(depth[indices])]
        axis.add_collection(PolyCollection(projected[order], facecolors=all_colors[order], edgecolors="none", linewidth=0, antialiased=False))
    axis.autoscale_view()
    axis.set_aspect("equal", adjustable="box")
    axis.axis("off")
    fig.suptitle(title, x=0.055, y=0.945, ha="left", fontsize=17, weight="bold", color="#20272A")
    fig.text(0.057, 0.897, subtitle, fontsize=9, color="#58646A")
    fig.legend(handles=legend_handles(), loc="lower center", bbox_to_anchor=(0.5, 0.045), ncol=4, frameon=False, fontsize=8)
    fig.subplots_adjust(left=0.035, right=0.99, top=0.86, bottom=0.12)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def orthographic_render(vertices, faces, output, title, axes, view_sort, annotations=None, reverse_sort=False):
    triangles, materials, _names = face_arrays(vertices, faces)
    order = np.argsort(triangles[:, :, view_sort].mean(axis=1))
    if reverse_sort:
        order = order[::-1]
    polygons = triangles[:, :, axes][order]
    colors = np.asarray([COLORS[key] for key in materials[order]])
    fig, axis = plt.subplots(figsize=(17, 6.0), dpi=210, facecolor="#F2F0EA")
    axis.add_collection(PolyCollection(polygons, facecolors=colors, edgecolors="none", linewidth=0))
    axis.autoscale_view()
    axis.set_aspect("equal", adjustable="box")
    axis.set_facecolor("#E8E7E2")
    axis.grid(True, color="#C9CCC9", linewidth=0.35)
    axis.tick_params(labelsize=7, colors="#4D565A")
    for spine in axis.spines.values():
        spine.set_color("#8C969A")
    if annotations:
        annotations(axis)
    fig.suptitle(title, x=0.055, y=0.96, ha="left", fontsize=16, weight="bold", color="#20272A")
    fig.text(0.057, 0.908, "MILESTONE 2 · AUTHORITATIVE X=0 BOW TO X=476 STERN · 1:700", fontsize=8.5, color="#58646A")
    axis.legend(handles=legend_handles(), loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False, fontsize=8)
    fig.subplots_adjust(left=0.055, right=0.99, top=0.86, bottom=0.20)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def top_annotations(axis):
    for seam, color, label in (
        (146.0, "#C9775D", "deck seam"),
        (158.667, "#4F7082", "hull seam"),
        (286.0, "#C9775D", "deck seam"),
        (317.333, "#4F7082", "hull seam"),
    ):
        axis.axvline(seam, color=color, linestyle=(0, (4, 3)), linewidth=0.75)
        label_y = 40.5 if label == "deck seam" else 44.0
        axis.text(seam, label_y, f"{label}\n{seam:.3f}", ha="center", va="bottom", fontsize=6.2, color=color)
    axis.annotate("", xy=(0, -43.5), xytext=(476, -43.5), arrowprops=dict(arrowstyle="<->", color="#293135", lw=0.8))
    axis.text(238, -42.3, "476.00 mm", ha="center", va="bottom", fontsize=8, color="#293135")
    axis.text(2, 43.0, "BOW", weight="bold", fontsize=7.5)
    axis.text(474, 43.0, "STERN", weight="bold", fontsize=7.5, ha="right")
    axis.set_xlim(-7, 483)
    axis.set_ylim(-48, 48)
    axis.set_xlabel("longitudinal x [mm]")
    axis.set_ylabel("port (−y) / starboard (+y) [mm]")


def side_annotations(axis):
    axis.axhline(31.5, color="#C9775D", linestyle=(0, (5, 3)), linewidth=0.8)
    axis.text(8, 32.2, "deck seating datum z = 31.50 mm", fontsize=7, color="#A6533B")
    axis.set_xlim(-7, 483)
    axis.set_ylim(-9, 37)
    axis.set_xlabel("longitudinal x [mm]")
    axis.set_ylabel("vertical z [mm]")


def section_keyed(output: Path):
    fig, axis = plt.subplots(figsize=(10, 8), dpi=210, facecolor="#F2F0EA")
    axis.set_facecolor("#E8E7E2")
    # Local section around the starboard pad; dimensions are actual.
    axis.add_patch(Rectangle((-12, 26.5), 24, 5.0, facecolor=COLORS["ash_gray"], edgecolor="#252D31", linewidth=0.8))
    axis.add_patch(Rectangle((-18, 31.5), 36, 3.0, facecolor=COLORS["deck_charcoal"], edgecolor="#252D31", linewidth=0.8))
    axis.add_patch(Rectangle((-3.25, 30.3), 6.5, 1.2, facecolor="#E8E7E2", edgecolor="#9B5B46", linewidth=0.8))
    axis.add_patch(Rectangle((-3.25, 31.5), 6.5, 1.45, facecolor="#E8E7E2", edgecolor="#9B5B46", linewidth=0.8))
    axis.add_patch(Rectangle((-3.0, 30.3), 6.0, 2.4, facecolor=COLORS["ash_gray"], edgecolor="#20272A", linewidth=1.0))
    axis.annotate("", xy=(-3.25, 29.5), xytext=(-3.0, 29.5), arrowprops=dict(arrowstyle="<->", color="#9B5B46"))
    axis.text(-3.125, 29.1, "0.25 mm/side", ha="center", va="top", fontsize=8, color="#9B5B46")
    axis.annotate("", xy=(4.4, 31.5), xytext=(4.4, 32.95), arrowprops=dict(arrowstyle="<->", color="#374A55"))
    axis.text(4.8, 32.2, "1.45 socket", fontsize=8, va="center", color="#374A55")
    axis.annotate("", xy=(7.0, 32.95), xytext=(7.0, 34.5), arrowprops=dict(arrowstyle="<->", color="#374A55"))
    axis.text(7.4, 33.72, "1.55 top skin", fontsize=8, va="center", color="#374A55")
    axis.axhline(31.5, color="#C9775D", linestyle=(0, (5, 3)), linewidth=0.8)
    axis.text(-17.5, 31.65, "zero-gap hidden seating/glue plane", fontsize=8, color="#A6533B")
    axis.set_xlim(-19, 19)
    axis.set_ylim(28.5, 35.5)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("local transverse section [mm]")
    axis.set_ylabel("z [mm]")
    axis.grid(True, color="#C8CBC8", linewidth=0.35)
    fig.suptitle("SECTION — KEYED LANDING PAD INTERFACE", x=0.07, y=0.95, ha="left", fontsize=15, weight="bold", color="#20272A")
    fig.text(0.072, 0.905, "6.00 × 6.00 × 2.40 mm printed pad · 6.50 mm sockets · no through-deck feature", fontsize=8.5, color="#58646A")
    fig.subplots_adjust(left=0.10, right=0.96, top=0.86, bottom=0.11)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def section_direct(output: Path):
    fig, axis = plt.subplots(figsize=(10, 7), dpi=210, facecolor="#F2F0EA")
    axis.set_facecolor("#E8E7E2")
    axis.add_patch(Rectangle((-14, 26.5), 28, 5.0, facecolor=COLORS["ash_gray"], edgecolor="#252D31", linewidth=0.8))
    axis.add_patch(Rectangle((-19, 31.5), 38, 3.0, facecolor=COLORS["deck_charcoal"], edgecolor="#252D31", linewidth=0.8))
    axis.axhline(31.5, color="#C9775D", linestyle=(0, (5, 3)), linewidth=1.0)
    axis.annotate("", xy=(16.0, 31.5), xytext=(16.0, 34.5), arrowprops=dict(arrowstyle="<->", color="#374A55"))
    axis.text(16.4, 33.0, "3.00 mm deck", fontsize=8, va="center")
    axis.text(-18.2, 31.65, "continuous hull-top support / hidden glue plane", fontsize=8, color="#A6533B")
    axis.text(-18.2, 30.9, "nominal seating gap = 0.00 mm", fontsize=8, color="#A6533B")
    axis.set_xlim(-20, 20)
    axis.set_ylim(28.8, 35.2)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("local transverse section [mm]")
    axis.set_ylabel("z [mm]")
    axis.grid(True, color="#C8CBC8", linewidth=0.35)
    fig.suptitle("SECTION — DIRECT SUPPORT / GLUE INTERFACE", x=0.07, y=0.94, ha="left", fontsize=15, weight="bold", color="#20272A")
    fig.text(0.072, 0.892, "Approved deck underside seats directly on approved hull-top datum between keyed stations", fontsize=8.5, color="#58646A")
    fig.subplots_adjust(left=0.10, right=0.96, top=0.84, bottom=0.12)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def update_manifest(paths):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for path in paths:
        manifest["outputs"][str(path.relative_to(INTEGRATION))] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    vertices, faces = load_obj(OBJ)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    roles = {item["name"]: item["kind"] for item in manifest["shapes"]}
    outputs = {
        "top": RENDER / "CVN69_Hull_Deck_Top.png",
        "port": RENDER / "CVN69_Hull_Deck_Port.png",
        "starboard": RENDER / "CVN69_Hull_Deck_Starboard.png",
        "bow": RENDER / "CVN69_Hull_Deck_Bow_Isometric.png",
        "stern": RENDER / "CVN69_Hull_Deck_Stern_Isometric.png",
        "exploded": RENDER / "CVN69_Hull_Deck_Exploded.png",
        "section_keyed": RENDER / "Section_Keyed_Landing_Pad.png",
        "section_direct": RENDER / "Section_Direct_Support.png",
    }
    orthographic_render(vertices, faces, outputs["top"], "CVN-69 HULL–FLIGHT-DECK INTEGRATION · TOP", (0, 1), 2, top_annotations)
    orthographic_render(vertices, faces, outputs["port"], "CVN-69 HULL–FLIGHT-DECK INTEGRATION · PORT", (0, 2), 1, side_annotations, reverse_sort=True)
    orthographic_render(vertices, faces, outputs["starboard"], "CVN-69 HULL–FLIGHT-DECK INTEGRATION · STARBOARD", (0, 2), 1, side_annotations, reverse_sort=False)
    projected_render(vertices, faces, outputs["bow"], "CVN-69 HULL–DECK ASSEMBLY · BOW ISOMETRIC", "GLUE-ONLY · CONCEALED PRINTED LANDING PADS · EXTERNAL HULL AND DECK PLANFORM PRESERVED", -145, 28)
    projected_render(vertices, faces, outputs["stern"], "CVN-69 HULL–DECK ASSEMBLY · STERN ISOMETRIC", "STAGGERED HULL/DECK SEAMS · NO HARDWARE · NO THROUGH-DECK LOCATORS", 35, 28)
    translations = {}
    for name, role in roles.items():
        if role == "interface_pad":
            translations[name] = (0.0, 0.0, 9.0)
        elif role in ("deck_module", "elevator"):
            translations[name] = (0.0, 0.0, 18.0)
        elif role in ("raised_marking", "catapult_track", "arresting_wire"):
            translations[name] = (0.0, 0.0, 26.0)
    projected_render(vertices, faces, outputs["exploded"], "CVN-69 MILESTONE 2 · EXPLODED HULL/DECK ASSEMBLY", "HULL · TWELVE KEYED LANDING PADS · DECK MODULES · REMOVABLE DETAILS", -135, 24, translations)
    section_keyed(outputs["section_keyed"])
    section_direct(outputs["section_direct"])
    update_manifest(list(outputs.values()))
    print(json.dumps({"status": "ok", "renders": {key: str(path) for key, path in outputs.items()}}, indent=2))


if __name__ == "__main__":
    main()
