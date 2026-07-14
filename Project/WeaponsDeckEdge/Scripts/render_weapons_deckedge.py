#!/usr/bin/env python3
"""Generate the required Milestone 4 neutral review and print-plate renders."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
PROJECT = ROOT / "Project"
M4 = PROJECT / "WeaponsDeckEdge"
RENDER = M4 / "Render"
RENDER.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = M4 / "QA" / "build_manifest.json"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = load_module("m3_render_utilities", PROJECT / "Island" / "Scripts" / "render_island.py")
COLORS = {
    "ash_gray": np.array([0.58, 0.59, 0.56]),
    "charcoal": np.array([0.20, 0.22, 0.24]),
    "deck_charcoal": np.array([0.20, 0.22, 0.24]),
    "silk_silver": np.array([0.69, 0.72, 0.74]),
    "ivory_white": np.array([0.93, 0.91, 0.85]),
    "basic_black": np.array([0.08, 0.09, 0.10]),
}
R.COLORS = COLORS
R.LABELS = {
    "ash_gray": "Matte Ash Gray — structures",
    "charcoal": "Matte Charcoal — launcher/boat inserts",
    "silk_silver": "Silk Silver — barrels/details",
    "ivory_white": "Matte Ivory White — domes/life rafts",
    "basic_black": "Basic Black — light housings",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_3mf(path):
    vertices = []
    faces = []
    material_keys = list(COLORS)
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
    for obj in root.findall(".//m:object", ns):
        name = obj.attrib.get("name", "unnamed")
        mesh = obj.find("./m:mesh", ns)
        if mesh is None:
            continue
        local = [
            (float(node.attrib["x"]), float(node.attrib["y"]), float(node.attrib["z"]))
            for node in mesh.findall("./m:vertices/m:vertex", ns)
        ]
        offset = len(vertices)
        vertices.extend(local)
        for triangle in mesh.findall("./m:triangles/m:triangle", ns):
            material = material_keys[int(triangle.attrib.get("p1", "0"))]
            indices = tuple(offset + int(triangle.attrib[key]) for key in ("v1", "v2", "v3"))
            faces.append((indices, material, name))
    return np.asarray(vertices, dtype=float), faces


def filter_model(model, predicate):
    vertices, faces = model
    return vertices, [face for face in faces if predicate(face[2], vertices[list(face[0])].mean(axis=0))]


def basic_top_annotations(axis):
    axis.set_xlabel("authoritative longitudinal x [mm]")
    axis.set_ylabel("port (−y) / starboard (+y) [mm]")
    axis.text(3, 46, "BOW", fontsize=7.5, weight="bold")
    axis.text(473, 46, "STERN", fontsize=7.5, weight="bold", ha="right")


def closeup_annotations(axis):
    axis.set_xlabel("authoritative longitudinal x [mm]")
    axis.set_ylabel("port (−y) / starboard (+y) [mm]")


def interface_section(path):
    fig, axis = plt.subplots(figsize=(12, 7.8), dpi=220, facecolor="#F2F0EA")
    axis.set_facecolor("#E8E7E2")
    axis.add_patch(Rectangle((-13, 0), 26, 2.4, facecolor=COLORS["ash_gray"], edgecolor="#263238", linewidth=1.0))
    socket = [(-2.25, 1.2), (2.25, 1.2), (2.25, 2.4), (1.15, 2.4), (-2.25, 2.4)]
    axis.add_patch(Polygon(socket, closed=True, facecolor="#E8E7E2", edgecolor="#A6533B", linewidth=1.0))
    key = [(-2.0, 1.2), (2.0, 1.2), (2.0, 1.3), (0.9, 2.4), (-2.0, 2.4)]
    axis.add_patch(Polygon(key, closed=True, facecolor=COLORS["charcoal"], edgecolor="#263238", linewidth=1.0))
    axis.add_patch(Rectangle((-5.0, 0), 8.0, 0.35, facecolor="#E8E7E2", edgecolor="#A6533B", linewidth=0.8))
    axis.annotate("", xy=(-2.25, 3.1), xytext=(-2.0, 3.1), arrowprops=dict(arrowstyle="<->", color="#A6533B"))
    axis.text(-2.125, 3.35, "0.25 mm/side", ha="center", fontsize=8, color="#A6533B")
    axis.annotate("", xy=(4.0, 1.2), xytext=(4.0, 2.4), arrowprops=dict(arrowstyle="<->", color="#39474E"))
    axis.text(4.35, 1.8, "1.20 mm seating depth", va="center", fontsize=8)
    axis.annotate("", xy=(8.0, 0), xytext=(8.0, 1.2), arrowprops=dict(arrowstyle="<->", color="#39474E"))
    axis.text(8.35, 0.6, "1.20 mm remaining skin", va="center", fontsize=8)
    axis.text(-12.3, 0.65, "2.40 mm additive sponson", fontsize=8, weight="bold")
    axis.text(-4.8, -0.55, "0.60 × 0.35 mm open hidden glue channel", fontsize=8, color="#A6533B")
    axis.text(-2.0, 4.1, "asymmetric chamfer prevents backward installation", fontsize=8.5, weight="bold")
    axis.set_xlim(-14, 14)
    axis.set_ylim(-1.2, 5.2)
    axis.set_aspect("equal")
    axis.grid(True, color="#C9CCC9", linewidth=0.35)
    axis.set_xlabel("representative common foundation interface [mm]")
    axis.set_ylabel("local section z [mm]")
    fig.suptitle("CVN-69 WEAPON FOUNDATION INTERFACE FAMILY", x=0.06, y=0.95, ha="left", fontsize=16.5, weight="bold", color="#20272A")
    fig.text(0.062, 0.90, "GLUE-ONLY · 0.25 MM/SIDE · OPEN SOCKET · NO METAL OR PURCHASED CONNECTORS", fontsize=8.5, color="#58646A")
    fig.subplots_adjust(left=0.08, right=0.97, top=0.84, bottom=0.13)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def plate_render(path, output, title):
    vertices, faces = load_3mf(path)
    max_x, max_y = vertices[:, 0].max(), vertices[:, 1].max()

    def annotate(axis):
        axis.add_patch(Rectangle((0, 0), 240, 240, fill=False, edgecolor="#A6533B", linewidth=0.8, linestyle=(0, (5, 3))))
        axis.text(238, 237, "240 × 240 mm limit", ha="right", va="top", fontsize=7, color="#A6533B")
        axis.text(3, max_y + 3, f"packed extent {max_x:.1f} × {max_y:.1f} mm", fontsize=7.5)
        axis.set_xlabel("plate x [mm]")
        axis.set_ylabel("plate y [mm]")

    R.orthographic_render(vertices, faces, output, title, "NAMED OBJECTS · MATERIALS BY OBJECT NAME · BAMBU P2S / X1C / P1S / A1", (0, 1), 2, False, ((-4, 244), (-4, 244)), annotate, True)


def update_manifest(outputs):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for path in outputs:
        manifest["outputs"][str(path.relative_to(M4))] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    integration = R.load_obj(PROJECT / "Integration" / "OBJ" / "CVN69_Hull_Deck_Assembly.obj")
    island = R.load_obj(PROJECT / "Island" / "OBJ" / "CVN69_Island_Assembly.obj")
    weapons = R.load_obj(M4 / "OBJ" / "CVN69_Weapons_DeckEdge_Assembly.obj")
    full = R.combine(R.combine(integration, island), weapons)
    wv, wf = weapons
    fv, ff = full
    outputs = {
        "ship_port": RENDER / "CVN69_Hull_Deck_Island_Weapons_Port.png",
        "ship_starboard": RENDER / "CVN69_Hull_Deck_Island_Weapons_Starboard.png",
        "ship_top": RENDER / "CVN69_Hull_Deck_Island_Weapons_Top.png",
        "ship_bow": RENDER / "CVN69_Hull_Deck_Island_Weapons_Bow_Isometric.png",
        "ship_stern": RENDER / "CVN69_Hull_Deck_Island_Weapons_Stern_Isometric.png",
        "exploded": RENDER / "Weapons_DeckEdge_Exploded.png",
        "forward_port": RENDER / "Weapon_Area_Forward_Port.png",
        "forward_starboard": RENDER / "Weapon_Area_Forward_Starboard.png",
        "aft_port": RENDER / "Weapon_Area_Aft_Port.png",
        "aft_starboard": RENDER / "Weapon_Area_Aft_Starboard.png",
        "ciws": RENDER / "CIWS_Assembly_Closeup.png",
        "ram": RENDER / "RAM_Assembly_Closeup.png",
        "seasparrow": RENDER / "SeaSparrow_Assembly_Closeup.png",
        "liferaft_boat": RENDER / "LifeRaft_Boat_Area_Closeup.png",
        "interface": RENDER / "Weapon_Interface_Family_Section.png",
    }
    side_limits = ((-7, 483), (-7, 84))
    R.orthographic_render(fv, ff, outputs["ship_port"], "CVN-69 HULL–DECK–ISLAND–WEAPONS · PORT", "MILESTONE 4 NON-PRODUCTION INTEGRATED REVIEW", (0, 2), 1, True, side_limits, R.ship_side_annotations, True)
    R.orthographic_render(fv, ff, outputs["ship_starboard"], "CVN-69 HULL–DECK–ISLAND–WEAPONS · STARBOARD", "FROZEN 2023–2024 VISIBLE FIT · PUBLIC-PHOTO-DERIVED", (0, 2), 1, False, side_limits, R.ship_side_annotations, True)
    R.orthographic_render(fv, ff, outputs["ship_top"], "CVN-69 HULL–DECK–ISLAND–WEAPONS · TOP", "476.00 MM OVERALL LENGTH · ASYMMETRIC DECK-EDGE ARRANGEMENT", (0, 1), 2, False, ((-7, 483), (-49, 49)), basic_top_annotations, True)
    R.projected_render(fv, ff, outputs["ship_bow"], "CVN-69 MILESTONE 4 · BOW ISOMETRIC", "NEUTRAL GEOMETRY REVIEW · NO AIRCRAFT / VEHICLES / OCEAN BASE", -145, 23, full_ship=True)
    R.projected_render(fv, ff, outputs["ship_stern"], "CVN-69 MILESTONE 4 · STERN ISOMETRIC", "GLUE-ONLY DEFENSIVE SYSTEMS AND DECK-EDGE EQUIPMENT", 35, 23, full_ship=True)

    translations = {}
    for record in json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["parts"]:
        name, role = record["name"], record["role"]
        if role in {"weapon_sponson", "boat_access_platform"}:
            translations[name] = (0, 0, -7)
        elif role == "weapon_foundation":
            translations[name] = (0, 0, 4)
        elif record.get("installation"):
            translations[name] = (0, 0, 12 if "Face" not in name and "Dome" not in name and "Barrel" not in name else 20)
        elif role.startswith(("liferaft", "boat")):
            translations[name] = (0, -7 if "Port" in name else 7, 8)
        else:
            translations[name] = (0, 0, 14)
    R.projected_render(wv, wf, outputs["exploded"], "CVN-69 MILESTONE 4 · EXPLODED ASSEMBLY", "43 PRODUCTION OBJECTS · FOUNDATIONS · WEAPONS · LIFE-SAFETY · DECK-EDGE DETAILS", -140, 25, translations)

    areas = (
        ("forward_port", ((65, 130), (-47, -15)), "FORWARD PORT WEAPON AREA"),
        ("forward_starboard", ((65, 130), (15, 47)), "FORWARD STARBOARD WEAPON AREA"),
        ("aft_port", ((405, 480), (-48, -14)), "AFT PORT WEAPON AREA"),
        ("aft_starboard", ((405, 448), (25, 48)), "AFT STARBOARD WEAPON AREA"),
        ("liferaft_boat", ((285, 315), (-47, -30)), "LIFE-RAFT / BOAT ACCESS AREA"),
    )
    for key, limits, title in areas:
        R.orthographic_render(wv, wf, outputs[key], f"CVN-69 · {title}", "AUTHORITATIVE X/Y LOCATION REVIEW · PHOTO-DERIVED PLACEMENT", (0, 1), 2, False, limits, closeup_annotations)

    family_models = {
        "ciws": filter_model(weapons, lambda name, _center: name.startswith("CIWS_01_")),
        "ram": filter_model(weapons, lambda name, _center: name.startswith("RAM_01_")),
        "seasparrow": filter_model(weapons, lambda name, _center: name.startswith("SeaSparrow_01_")),
    }
    for key, model in family_models.items():
        R.projected_render(model[0], model[1], outputs[key], f"CVN-69 · {key.upper()} ASSEMBLY", "SEPARATE FOUNDATION / BODY / FACE OR DOME / FDM-SAFE DETAILS", -135, 24)
    interface_section(outputs["interface"])

    plate_outputs = []
    for index, title in enumerate(("MAJOR WEAPONS", "SPONSONS / FOUNDATIONS", "LIFE RAFTS / BOAT", "DECK-EDGE DETAILS"), 1):
        plate = sorted((M4 / "3MF").glob(f"Print_Plate_{index:02d}_*.3mf"))[0]
        output = RENDER / f"Print_Plate_{index:02d}_Overview.png"
        plate_render(plate, output, f"CVN-69 PRINT PLATE {index:02d} · {title}")
        plate_outputs.append(output)
    all_outputs = [*outputs.values(), *plate_outputs]
    update_manifest(all_outputs)
    print(json.dumps({"status": "ok", "renders": len(all_outputs), "outputs": [str(path.relative_to(M4)) for path in all_outputs]}, indent=2))


if __name__ == "__main__":
    main()
