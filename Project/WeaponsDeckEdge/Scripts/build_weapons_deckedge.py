#!/usr/bin/env python3
"""Build Milestone 4 as new parametric FreeCAD BReps.

Approved Milestones 1–3 are opened only for datums and review geometry.  The
supplied STL package is never opened by this production builder.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import struct
import sys
import zipfile
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import FreeCAD as App
import Part


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
PROJECT = ROOT / "Project"
M4 = PROJECT / "WeaponsDeckEdge"
sys.path.insert(0, str(M4 / "CAD" / "Python"))
from weapons_deckedge_parameters import make_parameters  # noqa: E402


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = make_parameters()
UTIL = load_module("m3_cad_export_utilities", PROJECT / "Island" / "Scripts" / "build_island.py")
UTIL.P = P

DIRS = {
    "freecad": M4 / "CAD" / "FreeCAD",
    "step": M4 / "STEP",
    "stl": M4 / "STL",
    "3mf": M4 / "3MF",
    "obj": M4 / "OBJ",
    "render": M4 / "Render",
    "images": M4 / "Images",
    "docs": M4 / "Docs",
    "assembly": M4 / "Assembly",
    "references": M4 / "References",
    "qa": M4 / "QA",
}
for directory in DIRS.values():
    directory.mkdir(parents=True, exist_ok=True)

MATERIALS = OrderedDict(
    (
        ("ash_gray", ("Bambu PLA Matte Ash Gray", "#969890FF")),
        ("charcoal", ("Bambu PLA Matte Charcoal", "#34383CFF")),
        ("silk_silver", ("Bambu PLA Silk Silver", "#AEB4B8FF")),
        ("ivory_white", ("Bambu PLA Matte Ivory White", "#ECE8D9FF")),
        ("basic_black", ("Bambu PLA Basic Black", "#151719FF")),
    )
)
UTIL.MATERIALS = MATERIALS

APPROVED_PATHS = (
    PROJECT / "CAD" / "FreeCAD" / "Hull.FCStd",
    PROJECT / "CAD" / "Python" / "hull_parameters.py",
    PROJECT / "FlightDeck" / "CAD" / "FreeCAD" / "CVN69_Flight_Deck_Reconstruction.FCStd",
    PROJECT / "FlightDeck" / "CAD" / "Python" / "deck_parameters.py",
    PROJECT / "Integration" / "CAD" / "FreeCAD" / "CVN69_Hull_Deck_Integration.FCStd",
    PROJECT / "Integration" / "CAD" / "Python" / "integration_parameters.py",
    PROJECT / "Integration" / "STEP" / "CVN69_Hull_Deck_Assembly.step",
    PROJECT / "Island" / "CAD" / "FreeCAD" / "CVN69_Island.FCStd",
    PROJECT / "Island" / "CAD" / "Python" / "island_parameters.py",
    PROJECT / "Island" / "STEP" / "CVN69_Hull_Deck_Island_Review.step",
    PROJECT / "Island" / "References" / "Configuration_Audit.md",
    PROJECT / "Island" / "QA" / "Reference_Confidence_Report.md",
)


@dataclass
class PartSpec:
    name: str
    shape: object
    material: str
    role: str
    evidence: str
    classification: str
    installation: str = ""
    print_rotation: Optional[object] = None
    print_override: Optional[object] = None
    print_note: str = "Base down; exported STL minimum z = 0"
    minimum_feature_mm: float = 1.20
    allow_multiple: bool = False


v = UTIL.v
precise_bounds = UTIL.precise_bounds
validate_shape = UTIL.validate_shape
polygon_prism = UTIL.polygon_prism
loft_solid = UTIL.loft_solid
fuse_all = UTIL.fuse_all
compound = UTIL.compound
bar_between = UTIL.bar_between
transform_shape = UTIL.transform_shape
triangulate = UTIL.triangulate
print_shape = UTIL.print_shape
pack_plate = UTIL.pack_plate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rotate_xy(x: float, y: float, angle_deg: float):
    angle = math.radians(angle_deg)
    return x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)


def asym_key_points(cx=0.0, cy=0.0, clearance=0.0, width=None, depth=None, chamfer=None, heading=0.0):
    width = (P.key_width if width is None else width) + 2.0 * clearance
    depth = (P.key_depth_xy if depth is None else depth) + 2.0 * clearance
    chamfer = (P.key_chamfer if chamfer is None else chamfer) + clearance
    raw = (
        (-width / 2.0, -depth / 2.0),
        (width / 2.0, -depth / 2.0),
        (width / 2.0, depth / 2.0 - chamfer),
        (width / 2.0 - chamfer, depth / 2.0),
        (-width / 2.0, depth / 2.0),
    )
    return tuple((cx + rotate_xy(x, y, heading)[0], cy + rotate_xy(x, y, heading)[1]) for x, y in raw)


def local_asym_key(z0, height, clearance=0.0, width=None, depth=None, chamfer=None):
    return polygon_prism(asym_key_points(clearance=clearance, width=width, depth=depth, chamfer=chamfer), z0, height)


def place_local(shape, x, y, z, heading=0.0):
    result = shape.copy()
    if abs(heading) > 1.0e-9:
        result.rotate(v(0, 0, 0), v(0, 0, 1), heading)
    result.translate(v(x, y, z))
    return result


def platform_top(platform):
    return P.deck_top_z + platform.top_z_offset


def make_platform(platform):
    top = platform_top(platform)
    body = Part.makeBox(
        platform.x1 - platform.x0,
        platform.y1 - platform.y0,
        P.platform_thickness,
        v(platform.x0, platform.y0, top - P.platform_thickness),
    )
    for interface_name in platform.interface_names:
        item = P.installation(interface_name)
        socket = polygon_prism(
            asym_key_points(item.x, item.y, P.interface_clearance_per_side, heading=item.heading_deg),
            top - P.key_depth - 0.02,
            P.key_depth + 0.04,
        )
        body = body.cut(socket)
    # Open underside glue channel along the ship-side edge.  It cannot trap
    # support and remains hidden against the approved deck/hull edge.
    port = 0.5 * (platform.y0 + platform.y1) < 0.0
    channel_y = platform.y1 - P.glue_channel_depth if port else platform.y0
    channel = Part.makeBox(
        platform.x1 - platform.x0 - 2.0,
        P.glue_channel_depth,
        P.glue_channel_width,
        v(platform.x0 + 1.0, channel_y, top - P.platform_thickness),
    )
    body = body.cut(channel)
    return validate_shape(platform.name, body.removeSplitter())


def upper_socket(center_x, center_y, heading, foundation_top):
    return polygon_prism(
        asym_key_points(
            center_x,
            center_y,
            P.interface_clearance_per_side,
            width=2.40,
            depth=3.20,
            chamfer=0.70,
            heading=heading,
        ),
        foundation_top - P.upper_key_depth - 0.02,
        P.upper_key_depth + 0.04,
    )


def make_foundation(item):
    top = platform_top(P.platform(item.platform))
    key = polygon_prism(asym_key_points(item.x, item.y, heading=item.heading_deg), top - P.key_depth, P.key_depth + 0.05)
    pedestal = Part.makeCylinder(2.70, P.foundation_pedestal_height, v(item.x, item.y, top))
    shape = fuse_all((key, pedestal)).cut(
        upper_socket(item.x, item.y, item.heading_deg, top + P.foundation_pedestal_height)
    )
    return validate_shape(f"{item.name}_Foundation", shape.removeSplitter())


def upper_key_local():
    return local_asym_key(
        -P.upper_key_depth,
        P.upper_key_depth + 0.05,
        width=2.40,
        depth=3.20,
        chamfer=0.70,
    )


def make_ciws(item):
    base_z = platform_top(P.platform(item.platform)) + P.foundation_pedestal_height
    upper = fuse_all(
        (
            upper_key_local(),
            Part.makeCylinder(2.20, 0.85, v(0, 0, 0)),
            Part.makeBox(3.60, 3.20, 2.25, v(-1.80, -1.60, 0.80)),
            Part.makeCylinder(1.35, 1.20, v(0, 0, 3.00)),
        )
    )
    upper = place_local(upper, item.x, item.y, base_z, item.heading_deg)

    dome_local = fuse_all(
        (
            Part.makeCylinder(1.45, 0.55, v(0, 0, 0)),
            Part.makeCone(1.45, 0.35, P.ciws_dome_height - 0.50, v(0, 0, 0.50)),
        )
    )
    dome = place_local(dome_local, item.x, item.y, base_z + P.ciws_body_height, item.heading_deg)

    barrel_local = fuse_all(
        (
            Part.makeBox(1.20, 0.60, 1.20, v(-0.60, 1.60, -0.60)),
            Part.makeCylinder(
                P.preferred_barrel_diameter / 2.0,
                P.ciws_barrel_length,
                v(0, 2.10, 0),
                v(0, 1, 0),
            ),
        )
    )
    barrel = place_local(barrel_local, item.x, item.y, base_z + 2.05, item.heading_deg)
    return (
        validate_shape(f"{item.name}_Upper_Body", upper),
        validate_shape(f"{item.name}_Radar_Dome", dome),
        validate_shape(f"{item.name}_Barrel", barrel),
    )


def launcher_core(width, depth, height):
    lower = ((-width / 2, -depth / 2), (width / 2, -depth / 2), (width / 2, depth / 2), (-width / 2, depth / 2))
    upper = ((-width / 2 + 0.30, -depth / 2 - 0.30), (width / 2 - 0.30, -depth / 2 - 0.30), (width / 2 - 0.30, depth / 2 - 0.30), (-width / 2 + 0.30, depth / 2 - 0.30))
    return loft_solid(lower, 0.75, upper, height)


def launcher_face(width, height, columns, rows):
    base = Part.makeBox(width, P.minimum_insert, height, v(-width / 2.0, 0, 0))
    rib = P.minimum_raised_width
    raised = [Part.makeBox(width, P.minimum_raised_height, rib, v(-width / 2.0, P.minimum_insert, 0))]
    for row in range(1, rows + 1):
        z_value = row * height / (rows + 1) - rib / 2.0
        raised.append(Part.makeBox(width, P.minimum_raised_height, rib, v(-width / 2.0, P.minimum_insert, z_value)))
    for column in range(columns + 1):
        x_value = -width / 2.0 + column * width / columns - rib / 2.0
        raised.append(Part.makeBox(rib, P.minimum_raised_height, height, v(x_value, P.minimum_insert, 0)))
    return fuse_all((base, *raised))


def make_launcher(item, ram=True):
    base_z = platform_top(P.platform(item.platform)) + P.foundation_pedestal_height
    width = 4.80 if ram else 5.40
    depth = 3.20 if ram else 3.60
    height = P.ram_launcher_height if ram else P.seasparrow_launcher_height
    body_local = fuse_all((upper_key_local(), Part.makeCylinder(2.10, 0.80, v(0, 0, 0)), launcher_core(width, depth, height)))
    body = place_local(body_local, item.x, item.y, base_z, item.heading_deg)
    face_local = launcher_face(width - 0.50, height - 1.20, 4, 3 if ram else 2)
    face_local.translate(v(0, depth / 2.0, 0.75))
    face = place_local(face_local, item.x, item.y, base_z, item.heading_deg)
    return validate_shape(f"{item.name}_Launcher", body), validate_shape(f"{item.name}_Launcher_Face", face)


def make_liferaft_group(count):
    spacing = 1.36
    length = (count - 1) * spacing + P.liferaft_canister_diameter
    backing = Part.makeBox(length, 0.75, 1.20, v(-length / 2.0, -0.20, 0))
    pieces = [backing]
    for index in range(count):
        x_value = -length / 2.0 + P.liferaft_canister_diameter / 2.0 + index * spacing
        pieces.append(
            Part.makeCylinder(
                P.liferaft_canister_diameter / 2.0,
                P.liferaft_canister_length,
                v(x_value, 0.40, P.liferaft_canister_diameter / 2.0),
                v(0, 1, 0),
            )
        )
    return fuse_all(pieces)


def make_boat_set():
    platform = P.platform("Boat_Access_Platform_Port")
    top = platform_top(platform)
    lower = ((-6.0, -1.25), (4.9, -1.25), (6.2, 0), (4.9, 1.25), (-6.0, 1.25))
    upper = ((-5.8, -1.75), (4.7, -1.75), (6.6, 0), (4.7, 1.75), (-5.8, 1.75))
    hull_local = loft_solid(lower, 0.0, upper, 2.10)
    hull = place_local(hull_local, 301.0, -38.7, top + 1.00, 0.0)

    cockpit_local = Part.makeBox(4.8, 2.2, 0.60, v(-2.1, -1.1, 0))
    cockpit = place_local(cockpit_local, 301.0, -38.7, top + 3.10, 0.0)

    cradle_local = fuse_all(
        (
            Part.makeBox(12.2, 0.80, 0.70, v(-6.1, -0.40, 0)),
            Part.makeBox(0.80, 4.2, 1.00, v(-3.6, -2.1, 0)),
            Part.makeBox(0.80, 4.2, 1.00, v(2.8, -2.1, 0)),
        )
    )
    cradle = place_local(cradle_local, 301.0, -38.7, top, 0.0)

    davit_local = fuse_all(
        (
            Part.makeCylinder(0.55, 6.0, v(0, 0, 0)),
            bar_between((0, 0, 5.5), (0, -4.0, 6.8), 1.00),
            bar_between((0, -4.0, 6.8), (0, -4.0, 5.5), 0.80),
        )
    )
    davit = place_local(davit_local, 309.0, -35.6, top, 0.0)
    return hull, cockpit, cradle, davit


def make_railing(platform_name):
    platform = P.platform(platform_name)
    top = platform_top(platform)
    port = 0.5 * (platform.y0 + platform.y1) < 0.0
    y_value = platform.y0 + 0.35 if port else platform.y1 - 0.35
    x0, x1 = platform.x0 + 1.0, platform.x1 - 1.0
    z1 = top + 2.20
    pieces = [bar_between((x0, y_value, z1), (x1, y_value, z1), 0.70)]
    post_count = max(2, int((x1 - x0) / 6.0) + 1)
    for index in range(post_count):
        x_value = x0 + index * (x1 - x0) / (post_count - 1)
        pieces.append(bar_between((x_value, y_value, top), (x_value, y_value, z1), 0.70))
    return fuse_all(pieces)


def make_ladder(port=True):
    x_value = 365.0
    y_value = -37.5 if port else 37.5
    z0 = P.deck_top_z - 5.0
    direction = -1.0 if port else 1.0
    rails = (
        Part.makeBox(P.minimum_ladder, P.minimum_ladder, 5.0, v(x_value - 1.7, y_value, z0)),
        Part.makeBox(P.minimum_ladder, P.minimum_ladder, 5.0, v(x_value + 1.1, y_value, z0)),
    )
    rungs = [
        Part.makeBox(3.40, P.minimum_ladder, P.minimum_ladder, v(x_value - 1.7, y_value, z0 + index * 1.1))
        for index in range(5)
    ]
    shape = fuse_all((*rails, *rungs))
    if direction > 0:
        return shape
    return shape


def make_navigation_lights():
    shapes = []
    for y_value in (-20.5, 20.5):
        shapes.append(
            fuse_all(
                (
                    Part.makeBox(1.60, 1.20, 1.20, v(41.0, y_value - 0.60, P.deck_top_z)),
                    Part.makeCylinder(0.45, 1.20, v(41.8, y_value, P.deck_top_z + 1.15)),
                )
            )
        )
    return compound(shapes)


def make_lockers(port=True):
    y_value = -37.4 if port else 36.2
    pieces = []
    for index in range(3):
        pieces.append(Part.makeBox(1.80, 1.20, 2.20, v(351.0 + index * 1.75, y_value, P.deck_top_z - 2.20)))
    return fuse_all(pieces)


def build_parts():
    parts = []
    for platform in P.platforms:
        parts.append(
            PartSpec(
                platform.name,
                make_platform(platform),
                "ash_gray",
                "weapon_sponson" if platform.interface_names else "boat_access_platform",
                platform.evidence,
                "official-photo-derived / derived from approved deck datum",
                minimum_feature_mm=P.minimum_structural_wall,
            )
        )

    for item in P.installations:
        prefix = item.name
        parts.append(
            PartSpec(
                f"{prefix}_Foundation",
                make_foundation(item),
                "ash_gray",
                "weapon_foundation",
                item.evidence,
                "official-photo-derived placement; new parametric engineering interface",
                item.name,
            )
        )
        if item.family == "CIWS":
            upper, dome, barrel = make_ciws(item)
            parts.extend(
                (
                    PartSpec(f"{prefix}_Upper_Body", upper, "ash_gray", "ciws_upper_body", item.evidence, "photo-derived FDM-safe representation", item.name),
                    PartSpec(f"{prefix}_Radar_Dome", dome, "ivory_white", "ciws_radar_dome", item.evidence, "photo-derived FDM-safe representation", item.name),
                    PartSpec(f"{prefix}_Barrel", barrel, "silk_silver", "ciws_barrel", item.evidence, "deliberately enlarged for FDM printability", item.name, minimum_feature_mm=P.preferred_barrel_diameter),
                )
            )
        else:
            launcher, face = make_launcher(item, item.family == "RAM")
            family_role = "ram" if item.family == "RAM" else "seasparrow"
            parts.extend(
                (
                    PartSpec(f"{prefix}_Launcher", launcher, "ash_gray", f"{family_role}_launcher", item.evidence, "manufacturer-public-dimension-informed and photo-derived", item.name),
                    PartSpec(f"{prefix}_Launcher_Face", face, "charcoal", f"{family_role}_launcher_face", item.evidence, "deliberately simplified/enlarged FDM-safe cell representation", item.name, minimum_feature_mm=P.minimum_raised_width),
                )
            )

    liferaft_local = make_liferaft_group(6)
    for name, x_value, y_value, count, heading in P.liferaft_groups:
        shape = place_local(liferaft_local, x_value, y_value, P.deck_top_z - 1.20, heading)
        parts.append(
            PartSpec(name, shape, "ivory_white", "liferaft_group", "2024 official port/starboard imagery", "official-photo-derived grouping; canisters enlarged for FDM", minimum_feature_mm=P.liferaft_canister_diameter)
        )

    boat, cockpit, cradle, davit = make_boat_set()
    parts.extend(
        (
            PartSpec("Boat_01_Port_Utility", boat, "ash_gray", "boat", "2024 port-side major-equipment envelope", "visually approximated external utility boat"),
            PartSpec("Boat_01_Charcoal_Insert", cockpit, "charcoal", "boat_insert", "no-paint material separation", "visually approximated", minimum_feature_mm=P.minimum_insert),
            PartSpec("Boat_Cradle_01_Port", cradle, "ash_gray", "boat_cradle", "derived from boat envelope", "new parametric engineering geometry"),
            PartSpec("Boat_Davit_01_Port", davit, "ash_gray", "boat_davit", "2024 photo-informed major handling gear", "visually approximated; deliberately enlarged for FDM", minimum_feature_mm=0.80),
            PartSpec("Railing_Forward_Starboard", make_railing("Sponson_Forward_Starboard"), "ash_gray", "railing", "printable major platform railing", "photo-derived FDM-safe representation", minimum_feature_mm=P.minimum_railing),
            PartSpec("Railing_Aft_Port", make_railing("Sponson_Aft_Port_RAM"), "ash_gray", "railing", "printable major platform railing", "photo-derived FDM-safe representation", minimum_feature_mm=P.minimum_railing),
            PartSpec("DeckEdge_Access_Ladder_Port", make_ladder(True), "ash_gray", "ladder", "major visible deck-edge access", "visually approximated FDM-safe representation", minimum_feature_mm=P.minimum_ladder),
            PartSpec("DeckEdge_Access_Ladder_Starboard", make_ladder(False), "ash_gray", "ladder", "major visible deck-edge access", "visually approximated FDM-safe representation", minimum_feature_mm=P.minimum_ladder),
            PartSpec("Navigation_Light_Housings", make_navigation_lights(), "basic_black", "navigation_lights", "public-photo-visible housings; lens colors not asserted", "visually approximated", allow_multiple=True),
            PartSpec("Emergency_Locker_Group_Port", make_lockers(True), "ash_gray", "emergency_lockers", "major permanently mounted deck-edge boxes", "visually approximated"),
            PartSpec("Emergency_Locker_Group_Starboard", make_lockers(False), "ash_gray", "emergency_lockers", "major permanently mounted deck-edge boxes", "visually approximated"),
        )
    )
    if not 20 <= len(parts) <= 45:
        raise RuntimeError(f"Printable part count {len(parts)} is outside the requested 20–45 range")
    for spec in parts:
        validate_shape(spec.name, spec.shape, spec.allow_multiple)
    return parts


def make_coupon():
    male_base = Part.makeBox(P.coupon_width, P.coupon_depth, P.coupon_base_thickness, v(0, 0, 0))
    male_key = polygon_prism(
        asym_key_points(P.coupon_width / 2.0, P.coupon_depth / 2.0),
        P.coupon_base_thickness,
        P.key_depth,
    )
    male = fuse_all((male_base, male_key))
    channel = Part.makeBox(8.0, P.glue_channel_width, P.glue_channel_depth, v(0, P.coupon_depth / 2.0 - P.glue_channel_width / 2.0, P.coupon_base_thickness - P.glue_channel_depth))
    male = male.cut(channel)

    female = Part.makeBox(P.coupon_width, P.coupon_depth, P.coupon_base_thickness + P.key_depth, v(0, 0, 0))
    socket = polygon_prism(
        asym_key_points(P.coupon_width / 2.0, P.coupon_depth / 2.0, P.interface_clearance_per_side),
        P.coupon_base_thickness,
        P.key_depth + 0.05,
    )
    female = female.cut(socket)
    return validate_shape("Weapon_Mount_Coupon_Male", male), validate_shape("Weapon_Mount_Coupon_Female", female)


def write_binary_stl(path: Path, spec: PartSpec, shape):
    vertices, triangles = triangulate(shape)
    header = f"CVN-69 M4 {spec.name}".encode("ascii", "replace")[:80].ljust(80, b" ")
    with path.open("wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(triangles)))
        for a_index, b_index, c_index in triangles:
            a, b, c = vertices[a_index], vertices[b_index], vertices[c_index]
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            normal = (0.0, 0.0, 0.0) if length <= 1.0e-16 else (nx / length, ny / length, nz / length)
            handle.write(struct.pack("<12fH", *(normal + a + b + c), 0))
    return len(triangles)


def deterministic_zip_write(archive, name, data):
    info = zipfile.ZipInfo(name, (2024, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def write_3mf(path: Path, specs, title: str, shapes=None):
    shapes = shapes or [spec.shape for spec in specs]
    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    ET.register_namespace("", ns)
    model = ET.Element(f"{{{ns}}}model", {"unit": "millimeter", "xml:lang": "en-US"})
    metadata = ET.SubElement(model, f"{{{ns}}}metadata", {"name": "Title"})
    metadata.text = title
    resources = ET.SubElement(model, f"{{{ns}}}resources")
    bases = ET.SubElement(resources, f"{{{ns}}}basematerials", {"id": "1"})
    material_index = {}
    for index, (key, (name, color)) in enumerate(MATERIALS.items()):
        material_index[key] = index
        ET.SubElement(bases, f"{{{ns}}}base", {"name": name, "displaycolor": color})
    build = ET.SubElement(model, f"{{{ns}}}build")
    for object_id, (spec, shape) in enumerate(zip(specs, shapes), 2):
        obj = ET.SubElement(resources, f"{{{ns}}}object", {"id": str(object_id), "type": "model", "name": spec.name})
        mesh = ET.SubElement(obj, f"{{{ns}}}mesh")
        vertices_node = ET.SubElement(mesh, f"{{{ns}}}vertices")
        triangles_node = ET.SubElement(mesh, f"{{{ns}}}triangles")
        vertices, triangles = triangulate(shape)
        for x_value, y_value, z_value in vertices:
            ET.SubElement(vertices_node, f"{{{ns}}}vertex", {"x": f"{x_value:.6f}", "y": f"{y_value:.6f}", "z": f"{z_value:.6f}"})
        for a, b, c in triangles:
            ET.SubElement(
                triangles_node,
                f"{{{ns}}}triangle",
                {"v1": str(a), "v2": str(b), "v3": str(c), "pid": "1", "p1": str(material_index[spec.material])},
            )
        ET.SubElement(build, f"{{{ns}}}item", {"objectid": str(object_id)})
    model_xml = ET.tostring(model, encoding="utf-8", xml_declaration=True)
    content_types = b'''<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'''
    rels = b'''<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'''
    with zipfile.ZipFile(path, "w") as archive:
        deterministic_zip_write(archive, "[Content_Types].xml", content_types)
        deterministic_zip_write(archive, "_rels/.rels", rels)
        deterministic_zip_write(archive, "3D/3dmodel.model", model_xml)


def write_obj(path: Path, specs):
    UTIL.write_obj(path, specs)


def add_spreadsheet(doc):
    sheet = doc.addObject("Spreadsheet::Sheet", "WeaponsDeckEdgeParameters")
    rows = [
        ("Parameter", "Value", "Unit / provenance"),
        ("Overall length", P.overall_length, "mm; approved hull/integration import"),
        ("Deck base", P.deck_base_z, "mm; approved integration import"),
        ("Deck top", P.deck_top_z, "mm; approved integration import"),
        ("Island opening bounds", ", ".join(f"{value:.3f}" for value in P.island_bounds), "mm; approved island import"),
        ("Interface clearance", P.interface_clearance_per_side, "mm per side"),
        ("Key depth", P.key_depth, "mm"),
        ("Platform thickness", P.platform_thickness, "mm"),
        ("Remaining socket skin", P.platform_thickness - P.key_depth, "mm"),
        ("Minimum wall", P.minimum_structural_wall, "mm"),
        ("Minimum raised feature", f"{P.minimum_raised_width} × {P.minimum_raised_height}", "mm"),
        ("Configuration", P.configuration_period, "public-reference freeze"),
        ("System count", len(P.installations), "2 CIWS + 2 RAM + 2 Mk 29/ESSM"),
    ]
    for row_index, row in enumerate(rows, 1):
        for column_index, value in enumerate(row, 1):
            sheet.set(f"{chr(64 + column_index)}{row_index}", str(value))
    sheet.setStyle("A1:C1", "bold", "add")
    sheet.setColumnWidth("A", 210)
    sheet.setColumnWidth("B", 320)
    sheet.setColumnWidth("C", 330)


def add_part(doc, group, spec):
    obj = doc.addObject("Part::Feature", spec.name)
    obj.Label = spec.name.replace("_", " ")
    obj.Shape = spec.shape
    obj.addProperty("App::PropertyString", "WeaponsDeckEdgeRole").WeaponsDeckEdgeRole = spec.role
    obj.addProperty("App::PropertyString", "Material").Material = MATERIALS[spec.material][0]
    obj.addProperty("App::PropertyString", "EvidenceBasis").EvidenceBasis = spec.evidence
    obj.addProperty("App::PropertyString", "AccuracyClassification").AccuracyClassification = spec.classification
    obj.addProperty("App::PropertyString", "InstallationName").InstallationName = spec.installation
    obj.addProperty("App::PropertyString", "PrintOrientation").PrintOrientation = spec.print_note
    obj.addProperty("App::PropertyLength", "MinimumDesignedFeature").MinimumDesignedFeature = spec.minimum_feature_mm
    colors = {
        "ash_gray": (0.59, 0.60, 0.56),
        "charcoal": (0.20, 0.22, 0.24),
        "silk_silver": (0.68, 0.71, 0.73),
        "ivory_white": (0.92, 0.90, 0.84),
        "basic_black": (0.08, 0.09, 0.10),
    }
    try:
        obj.ViewObject.ShapeColor = colors[spec.material]
    except Exception:
        pass
    group.addObject(obj)
    return obj


def create_document(parts, coupons):
    doc = App.newDocument("CVN69_Weapons_DeckEdge")
    info = doc.addObject("App::FeaturePython", "MilestoneInformation")
    info.addProperty("App::PropertyString", "ProjectName").ProjectName = "USS Dwight D. Eisenhower (CVN-69) 1:700 Museum Edition"
    info.addProperty("App::PropertyString", "Milestone").Milestone = P.milestone
    info.addProperty("App::PropertyString", "Version").Version = P.version
    info.addProperty("App::PropertyString", "ConfigurationPeriod").ConfigurationPeriod = P.configuration_period
    info.addProperty("App::PropertyString", "CoordinateSystem").CoordinateSystem = "X=0 bow to 476 stern; Y port(-)/starboard(+); Z keel datum"
    info.addProperty("App::PropertyString", "GeometryStatus").GeometryStatus = "New parametric BRep geometry; source meshes are reference-only"
    info.addProperty("App::PropertyString", "ScopeBoundary").ScopeBoundary = "Defensive systems and major deck-edge equipment only"
    info.addProperty("App::PropertyString", "Generator").Generator = str(SCRIPT.relative_to(ROOT))
    add_spreadsheet(doc)

    refs = doc.addObject("App::DocumentObjectGroup", "ConstructionReferences")
    deck_datum = doc.addObject("Part::Feature", "Approved_Deck_Top_Datum")
    deck_datum.Shape = Part.makePlane(P.overall_length, 90.0, v(0, -45, P.deck_top_z))
    deck_datum.Visibility = False
    refs.addObject(deck_datum)
    island_ref = doc.addObject("Part::Feature", "Approved_Island_Opening_Bounds")
    x0, y0, x1, y1 = P.island_bounds
    island_ref.Shape = Part.makePolygon((v(x0, y0, P.deck_top_z), v(x1, y0, P.deck_top_z), v(x1, y1, P.deck_top_z), v(x0, y1, P.deck_top_z), v(x0, y0, P.deck_top_z)))
    island_ref.Visibility = False
    refs.addObject(island_ref)

    assembly = doc.addObject("App::DocumentObjectGroup", "WeaponsDeckEdgeAssembly")
    groups = {
        "platform": doc.addObject("App::DocumentObjectGroup", "SponsonsPlatforms"),
        "weapon": doc.addObject("App::DocumentObjectGroup", "DefensiveSystems"),
        "life": doc.addObject("App::DocumentObjectGroup", "LifeRaftsBoats"),
        "detail": doc.addObject("App::DocumentObjectGroup", "DeckEdgeDetails"),
        "coupon": doc.addObject("App::DocumentObjectGroup", "InterfaceCoupon"),
    }
    for group in groups.values():
        assembly.addObject(group)
    objects = []
    for spec in parts:
        if spec.role in {"weapon_sponson", "boat_access_platform"}:
            group = groups["platform"]
        elif spec.role.startswith(("ciws", "ram", "seasparrow")) or spec.role == "weapon_foundation":
            group = groups["weapon"]
        elif spec.role.startswith(("liferaft", "boat")):
            group = groups["life"]
        else:
            group = groups["detail"]
        objects.append(add_part(doc, group, spec))
    coupon_objects = [add_part(doc, groups["coupon"], spec) for spec in coupons]
    for obj in coupon_objects:
        obj.Visibility = False
    doc.recompute()
    return doc, objects, coupon_objects


def load_review_baseline():
    records = []
    sources = (
        (PROJECT / "Integration" / "CAD" / "FreeCAD" / "CVN69_Hull_Deck_Integration.FCStd", "IntegrationRole", "approved Milestone 2 BRep"),
        (PROJECT / "Island" / "CAD" / "FreeCAD" / "CVN69_Island.FCStd", "IslandRole", "approved Milestone 3 BRep"),
    )
    for path, role_property, evidence in sources:
        doc = App.openDocument(str(path))
        try:
            for obj in doc.Objects:
                role = str(getattr(obj, role_property, ""))
                if not role or role in {"test_coupon", "interface_coupon"} or not hasattr(obj, "Shape") or obj.Shape.isNull():
                    continue
                material = UTIL.material_key(str(getattr(obj, "Material", "Bambu PLA Matte Ash Gray")))
                records.append(
                    PartSpec(
                        f"Approved_{obj.Name}",
                        obj.Shape.copy(),
                        material,
                        "approved_review_baseline",
                        evidence,
                        "dimensionally approved project baseline",
                        allow_multiple=len(obj.Shape.Solids) != 1,
                    )
                )
        finally:
            App.closeDocument(doc.Name)
    if not records:
        raise RuntimeError("Could not load approved Milestone 2–3 review BReps")
    return records


def export_step(path, specs):
    doc = App.newDocument(path.stem)
    objects = []
    try:
        for spec in specs:
            obj = doc.addObject("Part::Feature", spec.name)
            obj.Shape = spec.shape
            objects.append(obj)
        doc.recompute()
        Part.export(objects, str(path))
    finally:
        App.closeDocument(doc.Name)


def approved_input_records():
    return {
        str(path.relative_to(ROOT)): {"bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in APPROVED_PATHS
        if path.is_file()
    }


def shape_record(spec, printed):
    bounds = precise_bounds(spec.shape)
    print_bounds = precise_bounds(printed)
    messages = []
    try:
        spec.shape.check(True)
    except ValueError as exc:
        messages = [line.strip() for line in str(exc).splitlines() if line.strip()]
    return {
        "name": spec.name,
        "role": spec.role,
        "installation": spec.installation,
        "material": MATERIALS[spec.material][0],
        "evidence_basis": spec.evidence,
        "accuracy_classification": spec.classification,
        "valid": bool(spec.shape.isValid()),
        "closed_solids": all(solid.isClosed() for solid in spec.shape.Solids),
        "solid_count": len(spec.shape.Solids),
        "volume_mm3": round(float(spec.shape.Volume), 6),
        "strict_bop_messages": messages,
        "assembly_bounds_mm": [round(value, 5) for value in bounds],
        "print_bounds_mm": [round(value, 5) for value in print_bounds],
        "print_size_mm": [round(print_bounds[3] - print_bounds[0], 5), round(print_bounds[4] - print_bounds[1], 5), round(print_bounds[5] - print_bounds[2], 5)],
        "minimum_designed_feature_mm": spec.minimum_feature_mm,
        "print_note": spec.print_note,
    }


def clean_generated():
    patterns = (
        (DIRS["stl"], "*.stl"),
        (DIRS["step"], "*.step"),
        (DIRS["3mf"], "*.3mf"),
        (DIRS["obj"], "CVN69_Weapons_DeckEdge_Assembly.*"),
    )
    for directory, pattern in patterns:
        for path in directory.glob(pattern):
            path.unlink()


def main():
    print("Building CVN-69 Milestone 4 defensive systems and deck-edge equipment")
    clean_generated()
    parts = build_parts()
    male, female = make_coupon()
    coupons = [
        PartSpec("Weapon_Mount_Coupon_Male", male, "ash_gray", "interface_coupon", "exact common production male key and glue channel", "new parametric engineering geometry"),
        PartSpec("Weapon_Mount_Coupon_Female", female, "charcoal", "interface_coupon", "exact common production female socket at 0.25 mm/side", "new parametric engineering geometry"),
    ]
    baseline = load_review_baseline()
    approved = approved_input_records()

    inspection = {
        "inspected_utc": datetime.now(timezone.utc).isoformat(),
        "freecad_version": ".".join(App.Version()[:3]),
        "coordinate_system": {"x": "0 bow to 476 stern", "y": "port negative / starboard positive", "z": "keel datum"},
        "deck_base_z_mm": P.deck_base_z,
        "deck_top_z_mm": P.deck_top_z,
        "island_bounds_mm": list(P.island_bounds),
        "hull_seams_mm": list(P.hull_seams),
        "deck_seams_mm": list(P.deck_seams),
        "approved_files": approved,
        "read_only_policy": "Approved Milestones 1–3 are opened read-only and are never overwritten.",
    }
    inspection_path = DIRS["qa"] / "Approved_Input_Inspection.json"
    inspection_path.write_text(json.dumps(inspection, indent=2) + "\n", encoding="utf-8")

    doc, objects, coupon_objects = create_document(parts, coupons)
    fcstd = DIRS["freecad"] / "CVN69_Weapons_DeckEdge.FCStd"
    doc.saveAs(str(fcstd))
    assembly_step = DIRS["step"] / "CVN69_Weapons_DeckEdge_Assembly.step"
    coupon_step = DIRS["step"] / "CVN69_Weapon_Mount_Interface_Coupon.step"
    review_step = DIRS["step"] / "CVN69_Hull_Deck_Island_Weapons_Review.step"
    Part.export(objects, str(assembly_step))
    Part.export(coupon_objects, str(coupon_step))
    export_step(review_step, [*baseline, *parts])

    obj_path = DIRS["obj"] / "CVN69_Weapons_DeckEdge_Assembly.obj"
    write_obj(obj_path, parts)
    assembly_3mf = DIRS["3mf"] / "CVN69_Weapons_DeckEdge_Assembly.3mf"
    review_3mf = DIRS["3mf"] / "CVN69_Hull_Deck_Island_Weapons_Review.3mf"
    write_3mf(assembly_3mf, parts, "CVN-69 Milestone 4 Weapons and Deck Edge Assembly")
    write_3mf(review_3mf, [*baseline, *parts], "CVN-69 Hull Deck Island Weapons Review")

    foundations = [part for part in parts if part.role == "weapon_foundation"]
    plate_groups = (
        ("Print_Plate_01_Major_Weapons.3mf", [part for part in parts if part.installation and part.role != "weapon_foundation"], "Major Defensive Systems"),
        ("Print_Plate_02_Sponsons_Foundations.3mf", [part for part in parts if part.role in {"weapon_sponson", "weapon_foundation"}], "Sponsons and Foundations"),
        ("Print_Plate_03_LifeRafts_Boats.3mf", [part for part in parts if part.role.startswith(("liferaft", "boat"))], "Life Rafts and Boat Equipment"),
        ("Print_Plate_04_DeckEdge_Details.3mf", [part for part in parts if not part.installation and part.role not in {"weapon_sponson", "boat_access_platform"} and not part.role.startswith(("liferaft", "boat"))], "Deck Edge Details"),
    )
    plate_paths = []
    for filename, group, title in plate_groups:
        if not group:
            continue
        packed_specs, packed_shapes = pack_plate(group)
        path = DIRS["3mf"] / filename
        write_3mf(path, packed_specs, f"CVN-69 Milestone 4 — {title}", packed_shapes)
        plate_paths.append(path)

    coupon_packed, coupon_shapes = pack_plate(coupons, max_size=60.0)
    coupon_3mf = DIRS["3mf"] / "Weapon_Mount_Interface_Test_Coupon.3mf"
    write_3mf(coupon_3mf, coupon_packed, "CVN-69 Weapon Mount Interface Test Coupon", coupon_shapes)

    print_versions = {spec.name: print_shape(spec) for spec in [*parts, *coupons]}
    stl_facets = {}
    stl_paths = []
    for spec in [*parts, *coupons]:
        path = DIRS["stl"] / f"{spec.name}.stl"
        stl_facets[path.name] = write_binary_stl(path, spec, print_versions[spec.name])
        stl_paths.append(path)

    output_paths = [
        fcstd,
        assembly_step,
        coupon_step,
        review_step,
        obj_path,
        obj_path.with_suffix(".mtl"),
        assembly_3mf,
        review_3mf,
        *plate_paths,
        coupon_3mf,
        *stl_paths,
        inspection_path,
    ]
    geometry_hash = hashlib.sha256(
        "".join(f"{path.name}:{sha256(path)}\n" for path in sorted(stl_paths)).encode("utf-8")
    ).hexdigest()
    manifest = {
        "project": "USS Dwight D. Eisenhower (CVN-69) 1:700 Museum Edition",
        "milestone": P.milestone,
        "version": P.version,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "freecad_version": ".".join(App.Version()[:3]),
        "configuration_period": P.configuration_period,
        "coordinate_system": {"x": "0 mm bow to 476 mm stern", "y": "port negative / starboard positive", "z": "vertical from keel datum"},
        "parameters_mm": {
            "overall_length": P.overall_length,
            "deck_base_z": P.deck_base_z,
            "deck_top_z": P.deck_top_z,
            "interface_clearance_per_side": P.interface_clearance_per_side,
            "key_depth": P.key_depth,
            "platform_thickness": P.platform_thickness,
            "remaining_platform_skin": P.platform_thickness - P.key_depth,
            "minimum_structural_wall": P.minimum_structural_wall,
            "minimum_fragile_diameter": P.minimum_fragile_diameter,
            "minimum_railing": P.minimum_railing,
            "minimum_ladder": P.minimum_ladder,
        },
        "counts": {
            "production_parts": len(parts),
            "coupon_parts": len(coupons),
            "weapon_installations": len(P.installations),
            "CIWS": sum(item.family == "CIWS" for item in P.installations),
            "RAM": sum(item.family == "RAM" for item in P.installations),
            "SeaSparrow": sum(item.family == "SeaSparrow" for item in P.installations),
        },
        "installations": [item.__dict__ for item in P.installations],
        "material_mapping": {spec.name: MATERIALS[spec.material][0] for spec in parts},
        "parts": [shape_record(spec, print_versions[spec.name]) for spec in parts],
        "coupon_parts": [shape_record(spec, print_versions[spec.name]) for spec in coupons],
        "stl_facets": stl_facets,
        "approved_input_hashes": approved,
        "deterministic_geometry_sha256": geometry_hash,
        "outputs": {
            str(path.relative_to(M4)): {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in output_paths
        },
    }
    manifest_path = DIRS["qa"] / "build_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    App.closeDocument(doc.Name)
    print(json.dumps({"status": "ok", "production_parts": len(parts), "coupon_parts": len(coupons), "stl_files": len(stl_paths), "geometry_sha256": geometry_hash}, indent=2))


if __name__ == "__main__":
    main()
