#!/usr/bin/env python3
"""Generate Milestone 5 neutral review, family, layout, and plate renders."""

from __future__ import annotations

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
M5 = PROJECT / "AirWing"
RENDER = M5 / "Render"
RENDER.mkdir(parents=True, exist_ok=True)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = load_module("m5_render_utilities", PROJECT / "Island" / "Scripts" / "render_island.py")
sys.path.insert(0, str(M5 / "CAD" / "Python"))
from airwing_parameters import make_parameters  # noqa: E402
P = make_parameters()
MATERIAL_KEYS = ("blue_grey", "charcoal", "ivory", "silver")
COLORS = {
    "ash_gray": np.array([0.58, 0.59, 0.56]), "charcoal": np.array([0.20, 0.22, 0.24]),
    "deck_charcoal": np.array([0.20, 0.22, 0.24]), "silk_silver": np.array([0.69, 0.72, 0.74]),
    "ivory_white": np.array([0.93, 0.91, 0.85]), "basic_black": np.array([0.08, 0.09, 0.10]),
    "blue_grey": np.array([0.45, 0.51, 0.55]), "ivory": np.array([0.93, 0.91, 0.85]),
    "silver": np.array([0.69, 0.72, 0.74]),
}
R.COLORS = COLORS
R.LABELS = {
    "blue_grey": "Basic Blue Grey — aircraft exterior", "charcoal": "Charcoal — canopy inserts",
    "ivory": "Ivory — dome / identity inserts", "silver": "Silver — rotors / details",
    "ash_gray": "Approved ship baseline", "deck_charcoal": "Approved flight deck",
}


def combine_many(models):
    result = models[0]
    for model in models[1:]:
        result = R.combine(result, model)
    return result


def filter_model(model, prefix=None, roles=None):
    vertices, faces = model
    if prefix:
        faces = [face for face in faces if face[2].startswith(prefix)]
    if roles:
        faces = [face for face in faces if any(role in face[2] for role in roles)]
    return vertices, faces


def load_3mf(path):
    vertices, faces = [], []
    keys = list(MATERIAL_KEYS)
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
    for obj in root.findall("./m:resources/m:object", ns):
        name = obj.attrib.get("name", "unnamed")
        mesh = obj.find("./m:mesh", ns)
        local = [(float(node.attrib["x"]), float(node.attrib["y"]), float(node.attrib["z"])) for node in mesh.findall("./m:vertices/m:vertex", ns)]
        offset = len(vertices)
        vertices.extend(local)
        for tri in mesh.findall("./m:triangles/m:triangle", ns):
            faces.append((tuple(offset + int(tri.attrib[key]) for key in ("v1", "v2", "v3")), keys[int(tri.attrib.get("p1", "0"))], name))
    return np.asarray(vertices), faces


def ship_top_annotations(axis):
    axis.set_xlabel("authoritative x [mm] — bow 0 to stern 476")
    axis.set_ylabel("port (−y) / starboard (+y) [mm]")
    axis.text(2, 46, "BOW", fontsize=7.5, weight="bold")
    axis.text(474, 46, "STERN", fontsize=7.5, weight="bold", ha="right")


def layout_map(config_path, output, title):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    outline = [(P.overall_length-x, y) for x, y in P.integration.deck.outline_points]
    fig, axis = plt.subplots(figsize=(15, 5.2), dpi=220, facecolor="#F2F0EA")
    axis.set_facecolor("#E8E7E2")
    axis.add_patch(Polygon(outline, closed=True, facecolor="#34383C", edgecolor="#1F272B", linewidth=0.8))
    palette = {item.code: COLORS["blue_grey"] for item in P.aircraft_types}
    for entry in config["entries"]:
        x, y = entry["x"], entry["y"]
        angle = np.deg2rad(entry["heading"])
        axis.scatter([x], [y], s=28, c=[palette[entry["type"]]], edgecolors="#ECE8D9", linewidths=0.35, zorder=3)
        axis.arrow(x, y, 5*np.cos(angle), 5*np.sin(angle), width=0.15, head_width=1.2, color="#ECE8D9", length_includes_head=True, zorder=4)
    x0, y0, x1, y1 = P.island_bounds
    axis.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, facecolor="#969890", edgecolor="#ECE8D9", linewidth=0.5))
    axis.text((x0+x1)/2, (y0+y1)/2, "ISLAND", fontsize=6.5, ha="center", va="center")
    axis.set_xlim(-5, 481); axis.set_ylim(-48, 48); axis.set_aspect("equal")
    axis.grid(True, color="#BEC2C1", linewidth=0.25)
    axis.set_xlabel("x [mm] bow → stern"); axis.set_ylabel("y [mm]")
    fig.suptitle(title, x=0.055, y=0.96, ha="left", fontsize=15, weight="bold", color="#20272A")
    fig.text(0.057, 0.89, f"{len(config['entries'])} AIRCRAFT · HEADING ARROWS · 0.20 MM/SIDE CLEARANCE · EXACT BREP INTERFERENCE PASS", fontsize=8, color="#58646A")
    fig.subplots_adjust(left=0.055, right=0.98, top=0.82, bottom=0.18)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    integration = R.load_obj(PROJECT / "Integration" / "OBJ" / "CVN69_Hull_Deck_Assembly.obj")
    island = R.load_obj(PROJECT / "Island" / "OBJ" / "CVN69_Island_Assembly.obj")
    weapons = R.load_obj(PROJECT / "WeaponsDeckEdge" / "OBJ" / "CVN69_Weapons_DeckEdge_Assembly.obj")
    aircraft = R.load_obj(M5 / "OBJ" / "CVN69_AirWing_Default_Layout.obj")
    master = R.load_obj(M5 / "OBJ" / "CVN69_AirWing_Master.obj")
    full = combine_many((integration, island, weapons, aircraft))
    fv, ff = full
    av, af = aircraft
    outputs = []

    specs = (
        ("CVN69_AirWing_Top.png", lambda p: R.orthographic_render(fv, ff, p, "CVN-69 MILESTONE 5 · DEFAULT AIR WING · TOP", "32-AIRCRAFT FROZEN-PERIOD REVIEW · APPROVED M2–M4 BASELINE", (0, 1), 2, False, ((-7, 483), (-49, 49)), ship_top_annotations, True)),
        ("CVN69_AirWing_Port.png", lambda p: R.orthographic_render(fv, ff, p, "CVN-69 MILESTONE 5 · PORT", "1:700 PARAMETRIC AIR WING · GLUE-ONLY · NO BASELINE CHANGES", (0, 2), 1, True, ((-7, 483), (-7, 84)), R.ship_side_annotations, True)),
        ("CVN69_AirWing_Starboard.png", lambda p: R.orthographic_render(fv, ff, p, "CVN-69 MILESTONE 5 · STARBOARD", "FROZEN 14 OCT 2023–14 JUL 2024 CVW-3 CONFIGURATION", (0, 2), 1, False, ((-7, 483), (-7, 84)), R.ship_side_annotations, True)),
        ("CVN69_AirWing_Bow_Isometric.png", lambda p: R.projected_render(fv, ff, p, "CVN-69 AIR WING · BOW ISOMETRIC", "NEUTRAL GEOMETRY REVIEW · NO OCEAN BASE", -145, 24, full_ship=True)),
        ("CVN69_AirWing_Stern_Isometric.png", lambda p: R.projected_render(fv, ff, p, "CVN-69 AIR WING · STERN ISOMETRIC", "APPROVED SHIP + PARAMETRIC AIRCRAFT REVIEW", 35, 24, full_ship=True)),
        ("Default_Deployment_Close_Top.png", lambda p: R.orthographic_render(av, af, p, "DEFAULT DEPLOYMENT AIR-WING LAYOUT", "32 NAMED AIRCRAFT · SQUADRON/TYPE/VARIANT METADATA", (0, 1), 2, False, ((120, 455), (-38, 38)), ship_top_annotations, True)),
    )
    for filename, function in specs:
        path = RENDER / filename; function(path); outputs.append(path)

    for filename, config, title in (
        ("Layout_Light_16.png", "light_deck_layout.json", "LIGHT DECK LAYOUT"),
        ("Layout_Default_32.png", "default_deployment_layout.json", "DEFAULT DEPLOYMENT LAYOUT"),
        ("Layout_Full_36.png", "full_deck_layout.json", "FULL FOLDED-WING DECK LAYOUT"),
    ):
        path = RENDER / filename; layout_map(M5 / "Layout" / config, path, title); outputs.append(path)

    for item in P.aircraft_types:
        model = filter_model(master, prefix=item.code)
        path = RENDER / f"Family_{item.code}.png"
        R.projected_render(model[0], model[1], path, f"{item.name} · {item.squadron}", "SPREAD/FOLDED/LAUNCH OR ROTOR VARIANTS · NO-PAINT INSERTS", -135, 27)
        outputs.append(path)

    comparisons = (
        ("Fixed_Wing_Variant_Comparison.png", ("Spread_Body", "Folded_Body", "Launch_Body"), "FIXED-WING VARIANT COMPARISON"),
        ("Helicopter_Rotor_Comparison.png", ("MH60", "Main_Rotor"), "MH-60 BODY / DEPLOYED / FOLDED ROTOR COMPARISON"),
        ("No_Paint_Insert_Comparison.png", ("Canopy_Insert", "Rotodome", "Squadron_ID_Insert"), "NO-PAINT INSERT FAMILY"),
    )
    for filename, roles, title in comparisons:
        model = filter_model(master, roles=roles)
        path = RENDER / filename
        R.projected_render(model[0], model[1], path, title, "BLUE GREY · CHARCOAL · IVORY · SILVER OBJECT SEPARATION", -135, 28)
        outputs.append(path)

    plate = load_3mf(M5 / "3MF" / "Print_Plate_00_First_Article.3mf")
    path = RENDER / "Print_Plate_00_First_Article.png"
    R.orthographic_render(plate[0], plate[1], path, "AIR WING FIRST-ARTICLE PLATE", "≤120 × 120 MM · REPRESENTATIVE HARD FAMILIES · REAL 0.12/0.16 MM SLICE PASS", (0, 1), 2, False, ((0, 120), (0, 120)), None, True)
    outputs.append(path)
    print(json.dumps({"status": "ok", "renders": len(outputs), "outputs": [str(path.relative_to(M5)) for path in outputs]}, indent=2))


if __name__ == "__main__":
    main()
