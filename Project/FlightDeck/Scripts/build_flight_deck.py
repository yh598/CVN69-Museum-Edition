#!/usr/bin/env python3
"""Build the CVN-69 flight-deck reconstruction with FreeCAD's OCC kernel.

This is a BRep reconstruction.  Source STL triangles are never imported into
the production document or reused in an export.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
import zipfile
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import FreeCAD as App
import Part


SCRIPT = Path(__file__).resolve()
DECK_PROJECT = SCRIPT.parents[1]
ROOT_PROJECT = DECK_PROJECT.parent
sys.path.insert(0, str(DECK_PROJECT / "CAD" / "Python"))
from deck_parameters import make_parameters  # noqa: E402


P = make_parameters()
VERSION = "0.2.0-review"

DIRS = {
    "freecad": DECK_PROJECT / "CAD" / "FreeCAD",
    "step": DECK_PROJECT / "STEP",
    "stl": DECK_PROJECT / "STL",
    "3mf": DECK_PROJECT / "3MF",
    "3mf_individual": DECK_PROJECT / "3MF" / "Individual",
    "obj": DECK_PROJECT / "OBJ",
    "render": DECK_PROJECT / "Render",
    "qa": DECK_PROJECT / "QA",
}
for directory in DIRS.values():
    directory.mkdir(parents=True, exist_ok=True)


MATERIALS = OrderedDict(
    (
        ("deck_charcoal", ("PLA Matte Charcoal", "#34383CFF")),
        ("elevator_gray", ("PLA Neutral Gray", "#666D73FF")),
        ("marking_white", ("PLA Basic White", "#F1F1EBFF")),
        ("track_silver", ("PLA Silk Silver", "#AEB4B8FF")),
        ("wire_yellow", ("PLA Signal Yellow", "#D6B32AFF")),
    )
)


def v(x: float, y: float, z: float) -> App.Vector:
    return App.Vector(float(x), float(y), float(z))


def polygon_wire(points, z=0.0):
    vectors = [v(x, y, z) for x, y in points]
    return Part.makePolygon(vectors + [vectors[0]])


def polygon_prism(points, z0: float, height: float):
    return Part.Face(polygon_wire(points, z0)).extrude(v(0, 0, height))


def rectangle_points(x0: float, x1: float, y0: float, y1: float, chamfer=0.0):
    if chamfer <= 0.0:
        return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    c = min(chamfer, (x1 - x0) / 4.0, (y1 - y0) / 4.0)
    return (
        (x0 + c, y0),
        (x1 - c, y0),
        (x1, y0 + c),
        (x1, y1 - c),
        (x1 - c, y1),
        (x0 + c, y1),
        (x0, y1 - c),
        (x0, y0 + c),
    )


def precise_bounds(shape):
    points, _faces = shape.tessellate(P.tessellation_deflection)
    if not points:
        raise RuntimeError("Cannot measure an empty shape")
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    zs = [point.z for point in points]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def validate_solid(name: str, shape, allow_multiple=False):
    shape.check(True)
    if shape.isNull() or not shape.isValid() or not shape.isClosed():
        raise RuntimeError(f"{name} is not a valid closed BRep")
    if not shape.Solids:
        raise RuntimeError(f"{name} contains no solid")
    if not allow_multiple and len(shape.Solids) != 1:
        raise RuntimeError(f"{name} contains {len(shape.Solids)} solids; expected one")
    return shape


def make_deck_master():
    deck = polygon_prism(P.outline_points, 0.0, P.deck_thickness)

    island_tool = polygon_prism(P.island_opening, -0.1, P.deck_thickness + 0.2)
    deck = deck.cut(island_tool)

    elevator_tools = []
    for elevator in P.elevators:
        clearance = P.fit_clearance_per_side
        recess = polygon_prism(
            rectangle_points(
                elevator.x0 - clearance,
                elevator.x1 + clearance,
                elevator.y0 - clearance,
                elevator.y1 + clearance,
                chamfer=0.8 + clearance,
            ),
            P.elevator_shelf_thickness,
            P.deck_thickness - P.elevator_shelf_thickness + 0.1,
        )
        elevator_tools.append(recess)
        deck = deck.cut(recess)

    deck = deck.removeSplitter()
    validate_solid("UnsplitDeck", deck)
    return deck, island_tool, Part.makeCompound(elevator_tools)


def make_elevators():
    elevators = []
    for elevator in P.elevators:
        shape = polygon_prism(
            rectangle_points(
                elevator.x0,
                elevator.x1,
                elevator.y0,
                elevator.y1,
                chamfer=0.8,
            ),
            P.elevator_shelf_thickness,
            P.elevator_plate_thickness,
        ).removeSplitter()
        validate_solid(elevator.name, shape)
        elevators.append((elevator.name, shape, "elevator_gray", "elevator"))
    return elevators


def seam_keys(seam: float):
    tongues = []
    sockets = []
    for center_y in (-15.0, 15.0):
        embed = 1.0
        tongues.append(
            Part.makeBox(
                P.glue_tongue_length + embed,
                P.glue_tongue_width,
                P.glue_tongue_thickness,
                v(seam - embed, center_y - P.glue_tongue_width / 2.0, 0.0),
            )
        )
        clearance = P.fit_clearance_per_side
        sockets.append(
            Part.makeBox(
                P.glue_tongue_length + clearance + 0.15,
                P.glue_tongue_width + 2.0 * clearance,
                P.glue_socket_depth + 0.05,
                v(seam - 0.10, center_y - P.glue_tongue_width / 2.0 - clearance, -0.05),
            )
        )
    return tongues, sockets


def split_deck(deck):
    limits = (0.0,) + P.split_seams + (P.overall_length,)
    modules = []
    for x0, x1 in zip(limits[:-1], limits[1:]):
        clip = Part.makeBox(x1 - x0, 120.0, 8.0, v(x0, -60.0, -1.0))
        modules.append(deck.common(clip))

    all_tongues = []
    all_sockets = []
    for index, seam in enumerate(P.split_seams):
        tongues, sockets = seam_keys(seam)
        all_tongues.extend(tongues)
        all_sockets.extend(sockets)
        modules[index] = modules[index].fuse(Part.makeCompound(tongues))
        modules[index + 1] = modules[index + 1].cut(Part.makeCompound(sockets))

    result = []
    for index, module in enumerate(modules, 1):
        module = module.removeSplitter()
        validate_solid(f"Main_Deck_Module_{index}", module)
        result.append(module)
    return result, Part.makeCompound(all_tongues), Part.makeCompound(all_sockets)


def line_prism(start, end, width: float, z0: float, height: float):
    x0, y0 = start
    x1, y1 = end
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        raise ValueError("Linear feature has zero length")
    nx, ny = -dy / length * width / 2.0, dx / length * width / 2.0
    points = (
        (x0 + nx, y0 + ny),
        (x1 + nx, y1 + ny),
        (x1 - nx, y1 - ny),
        (x0 - nx, y0 - ny),
    )
    return polygon_prism(points, z0, height)


def point_along(start, end, x_value):
    x0, y0 = start
    x1, y1 = end
    t = (x_value - x0) / (x1 - x0)
    return (x_value, y0 + t * (y1 - y0))


def landing_marking(name: str, x0: float, x1: float, crossbars):
    center_start = (10.0, 0.5)
    center_end = (302.0, -22.0)
    p0 = point_along(center_start, center_end, x0)
    p1 = point_along(center_start, center_end, x1)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy)
    nx, ny = -dy / length, dx / length
    half_width = 10.5
    shapes = [
        line_prism(p0, p1, P.raised_marking_width, P.deck_thickness, P.raised_marking_height),
        line_prism(
            (p0[0] + nx * half_width, p0[1] + ny * half_width),
            (p1[0] + nx * half_width, p1[1] + ny * half_width),
            P.raised_marking_width,
            P.deck_thickness,
            P.raised_marking_height,
        ),
        line_prism(
            (p0[0] - nx * half_width, p0[1] - ny * half_width),
            (p1[0] - nx * half_width, p1[1] - ny * half_width),
            P.raised_marking_width,
            P.deck_thickness,
            P.raised_marking_height,
        ),
    ]
    for x_value in crossbars:
        center = point_along(center_start, center_end, x_value)
        shapes.append(
            line_prism(
                (center[0] - nx * half_width, center[1] - ny * half_width),
                (center[0] + nx * half_width, center[1] + ny * half_width),
                P.raised_marking_width,
                P.deck_thickness,
                P.raised_marking_height,
            )
        )
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    result = result.removeSplitter()
    validate_solid(name, result)
    return result


def rectangular_frame(name: str, x0: float, x1: float, y0: float, y1: float):
    width = P.raised_marking_width
    shapes = [
        line_prism((x0, y0), (x1, y0), width, P.deck_thickness, P.raised_marking_height),
        line_prism((x1, y0), (x1, y1), width, P.deck_thickness, P.raised_marking_height),
        line_prism((x1, y1), (x0, y1), width, P.deck_thickness, P.raised_marking_height),
        line_prism((x0, y1), (x0, y0), width, P.deck_thickness, P.raised_marking_height),
    ]
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    result = result.removeSplitter()
    validate_solid(name, result)
    return result


def make_markings():
    markings = [
        (
            "Raised_Marking_Landing_Aft",
            landing_marking("Raised_Marking_Landing_Aft", 10.0, 188.5, (12.0, 60.0, 120.0, 185.0)),
            "marking_white",
            "raised_marking",
        ),
        (
            "Raised_Marking_Landing_Forward",
            landing_marking("Raised_Marking_Landing_Forward", 191.5, 302.0, (195.0, 245.0, 300.0)),
            "marking_white",
            "raised_marking",
        ),
    ]

    bow_lines = [
        line_prism((335.0, 0.0), (468.0, 0.0), P.raised_marking_width, P.deck_thickness, P.raised_marking_height),
    ]
    for x_value in (336.0, 390.0, 450.0, 467.0):
        bow_lines.append(
            line_prism((x_value, -2.8), (x_value, 2.8), P.raised_marking_width, P.deck_thickness, P.raised_marking_height)
        )
    bow = bow_lines[0]
    for shape in bow_lines[1:]:
        bow = bow.fuse(shape)
    bow = bow.removeSplitter()
    validate_solid("Raised_Marking_Bow_Centerline", bow)
    markings.append(("Raised_Marking_Bow_Centerline", bow, "marking_white", "raised_marking"))

    for elevator in P.elevators:
        name = f"Raised_Marking_{elevator.name}"
        frame = rectangular_frame(name, elevator.x0 + 0.9, elevator.x1 - 0.9, elevator.y0 + 0.9, elevator.y1 - 0.9)
        markings.append((name, frame, "marking_white", "raised_marking"))
    return markings


def make_catapults():
    result = []
    for catapult in P.catapults:
        shape = line_prism(
            catapult.start,
            catapult.end,
            P.catapult_width,
            P.deck_thickness,
            P.catapult_height,
        ).removeSplitter()
        validate_solid(catapult.name, shape)
        result.append((catapult.name, shape, "track_silver", "catapult_track"))
    return result


def make_arresting_wires():
    center_start = (10.0, 0.5)
    center_end = (302.0, -22.0)
    dx, dy = center_end[0] - center_start[0], center_end[1] - center_start[1]
    length = math.hypot(dx, dy)
    nx, ny = -dy / length, dx / length
    result = []
    for index, x_value in enumerate((56.0, 68.0, 80.0, 92.0), 1):
        center = point_along(center_start, center_end, x_value)
        half_length = 15.0
        start = (center[0] - nx * half_length, center[1] - ny * half_length)
        end = (center[0] + nx * half_length, center[1] + ny * half_length)
        name = f"Arresting_Wire_{index}"
        shape = line_prism(
            start,
            end,
            P.arresting_wire_width,
            P.deck_thickness,
            P.arresting_wire_height,
        ).removeSplitter()
        validate_solid(name, shape)
        result.append((name, shape, "wire_yellow", "arresting_wire"))
    return result


def triangulate(shape, deflection=None):
    points, faces = shape.tessellate(deflection or P.tessellation_deflection)
    vertices = [(float(point.x), float(point.y), float(point.z)) for point in points]
    triangles = [(int(a), int(b), int(c)) for a, b, c in faces]
    return vertices, triangles


def triangle_normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length <= 1e-16:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def write_binary_stl(path: Path, named_shapes):
    facets = []
    for _name, shape, _material, _kind in named_shapes:
        vertices, triangles = triangulate(shape)
        for triangle in triangles:
            a, b, c = (vertices[index] for index in triangle)
            facets.append((triangle_normal(a, b, c), a, b, c))
    header = b"CVN-69 Flight Deck clean FreeCAD BRep reconstruction"[:80].ljust(80, b" ")
    with path.open("wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(facets)))
        for normal, a, b, c in facets:
            handle.write(struct.pack("<12fH", *(normal + a + b + c), 0))
    return len(facets)


def write_3mf(path: Path, named_shapes, title: str):
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

    obj = ET.SubElement(resources, f"{{{ns}}}object", {"id": "2", "type": "model", "name": title})
    mesh = ET.SubElement(obj, f"{{{ns}}}mesh")
    vertices_node = ET.SubElement(mesh, f"{{{ns}}}vertices")
    triangles_node = ET.SubElement(mesh, f"{{{ns}}}triangles")
    offset = 0
    for _name, shape, material, _kind in named_shapes:
        vertices, triangles = triangulate(shape)
        for x, y, z in vertices:
            ET.SubElement(vertices_node, f"{{{ns}}}vertex", {"x": f"{x:.6f}", "y": f"{y:.6f}", "z": f"{z:.6f}"})
        for a, b, c in triangles:
            ET.SubElement(
                triangles_node,
                f"{{{ns}}}triangle",
                {
                    "v1": str(a + offset),
                    "v2": str(b + offset),
                    "v3": str(c + offset),
                    "pid": "1",
                    "p1": str(material_index[material]),
                },
            )
        offset += len(vertices)
    build = ET.SubElement(model, f"{{{ns}}}build")
    ET.SubElement(build, f"{{{ns}}}item", {"objectid": "2"})

    model_xml = ET.tostring(model, encoding="utf-8", xml_declaration=True)
    content_types = b'''<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'''
    rels = b'''<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'''
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("3D/3dmodel.model", model_xml)


def write_obj(path: Path, named_shapes):
    mtl_path = path.with_suffix(".mtl")
    with mtl_path.open("w", encoding="utf-8") as mtl:
        for key, (name, color) in MATERIALS.items():
            rgb = tuple(int(color[index:index + 2], 16) / 255.0 for index in (1, 3, 5))
            mtl.write(f"newmtl {key}\n# {name}\nKd {rgb[0]:.6f} {rgb[1]:.6f} {rgb[2]:.6f}\n\n")
    with path.open("w", encoding="utf-8") as obj:
        obj.write(f"mtllib {mtl_path.name}\n")
        offset = 1
        for name, shape, material, _kind in named_shapes:
            vertices, triangles = triangulate(shape)
            obj.write(f"o {name}\nusemtl {material}\n")
            for x, y, z in vertices:
                obj.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
            for a, b, c in triangles:
                obj.write(f"f {a + offset} {b + offset} {c + offset}\n")
            offset += len(vertices)


def print_oriented(shape):
    result = shape.copy()
    bounds = precise_bounds(result)
    result.translate(v(-bounds[0], -bounds[1], -bounds[2]))
    return result


def translate_to(shape, x: float, y: float):
    result = print_oriented(shape)
    result.translate(v(x, y, 0.0))
    return result


def pack_plate(named_shapes, max_size=235.0, gap=2.5):
    layout = []
    cursor_x = 0.0
    cursor_y = 0.0
    row_height = 0.0
    for name, shape, material, kind in named_shapes:
        oriented = print_oriented(shape)
        bounds = precise_bounds(oriented)
        width = bounds[3] - bounds[0]
        depth = bounds[4] - bounds[1]
        if width > max_size or depth > max_size:
            raise RuntimeError(f"{name} exceeds the {max_size:.1f} mm packing envelope")
        if cursor_x > 0.0 and cursor_x + width > max_size:
            cursor_x = 0.0
            cursor_y += row_height + gap
            row_height = 0.0
        if cursor_y + depth > max_size:
            return layout, named_shapes[len(layout):]
        oriented.translate(v(cursor_x, cursor_y, 0.0))
        layout.append((name, oriented, material, kind))
        cursor_x += width + gap
        row_height = max(row_height, depth)
    return layout, []


def add_spreadsheet(doc):
    sheet = doc.addObject("Spreadsheet::Sheet", "DeckParameters")
    rows = [
        ("Parameter", "Value", "Unit / note"),
        ("Scale denominator", P.scale_denominator, "1:n"),
        ("Overall length", P.overall_length, "mm"),
        ("Deck thickness", P.deck_thickness, "mm"),
        ("Minimum wall", P.minimum_wall, "mm"),
        ("Elevator shelf", P.elevator_shelf_thickness, "mm"),
        ("Elevator plate", P.elevator_plate_thickness, "mm"),
        ("Fit clearance", P.fit_clearance_per_side, "mm per side"),
        ("Split seams", ", ".join(str(value) for value in P.split_seams), "x mm"),
        ("Glue tongue", f"{P.glue_tongue_length} x {P.glue_tongue_width} x {P.glue_tongue_thickness}", "mm"),
        ("Raised marking", f"{P.raised_marking_width} x {P.raised_marking_height}", "width x height mm"),
        ("Catapult track", f"{P.catapult_width} x {P.catapult_height}", "width x height mm"),
        ("Arresting wire", f"{P.arresting_wire_width} x {P.arresting_wire_height}", "width x height mm"),
        ("Tessellation", P.tessellation_deflection, "mm linear deflection"),
    ]
    for row_index, row in enumerate(rows, 1):
        for column_index, value in enumerate(row, 1):
            sheet.set(f"{chr(64 + column_index)}{row_index}", str(value))
    sheet.setStyle("A1:C1", "bold", "add")
    sheet.setColumnWidth("A", 190)
    sheet.setColumnWidth("B", 150)
    sheet.setColumnWidth("C", 190)
    return sheet


def add_part_object(doc, group, name, shape, material, kind):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = name.replace("_", " ")
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "PartCategory").PartCategory = kind
    obj.addProperty("App::PropertyString", "Material").Material = MATERIALS[material][0]
    obj.addProperty("App::PropertyString", "PrintOrientation").PrintOrientation = "Flat; exported STL/3MF translated to z=0"
    colors = {
        "deck_charcoal": (0.20, 0.22, 0.24),
        "elevator_gray": (0.40, 0.43, 0.46),
        "marking_white": (0.94, 0.94, 0.90),
        "track_silver": (0.68, 0.71, 0.73),
        "wire_yellow": (0.84, 0.70, 0.16),
    }
    try:
        obj.ViewObject.ShapeColor = colors[material]
    except Exception:
        pass
    group.addObject(obj)
    return obj


def create_document(master_deck, modules, island_tool, elevator_tools, tongues, sockets, details):
    doc = App.newDocument("CVN69_Flight_Deck_Reconstruction")
    info = doc.addObject("App::FeaturePython", "ReconstructionInformation")
    info.addProperty("App::PropertyString", "ProjectName").ProjectName = "USS Dwight D. Eisenhower (CVN-69) Flight Deck"
    info.addProperty("App::PropertyString", "Scope").Scope = "Flight deck only; island, weapons, aircraft, hull redesign, and ocean base excluded"
    info.addProperty("App::PropertyString", "GeometryMethod").GeometryMethod = "Clean scripted OpenCascade BRep reconstruction from numerical STL reference trace"
    info.addProperty("App::PropertyString", "SourcePolicy").SourcePolicy = "Source meshes are reference only; no mesh-to-solid conversion and no reused source triangles"
    info.addProperty("App::PropertyString", "Generator").Generator = str(SCRIPT.relative_to(ROOT_PROJECT))
    info.addProperty("App::PropertyString", "Version").Version = VERSION
    add_spreadsheet(doc)

    references = doc.addObject("App::DocumentObjectGroup", "ConstructionReferences")
    outline = doc.addObject("Part::Feature", "Deck_Outline_Trace")
    outline.Label = "Deck outline trace from source bands"
    outline.Shape = polygon_wire(P.outline_points)
    outline.Visibility = False
    references.addObject(outline)
    island = doc.addObject("Part::Feature", "Island_Opening_Tool")
    island.Shape = island_tool
    island.Visibility = False
    references.addObject(island)
    recesses = doc.addObject("Part::Feature", "Elevator_Recess_Tools")
    recesses.Shape = elevator_tools
    recesses.Visibility = False
    references.addObject(recesses)
    tongue_obj = doc.addObject("Part::Feature", "Glue_Tongue_Tools")
    tongue_obj.Shape = tongues
    tongue_obj.Visibility = False
    references.addObject(tongue_obj)
    socket_obj = doc.addObject("Part::Feature", "Glue_Socket_Tools")
    socket_obj.Shape = sockets
    socket_obj.Visibility = False
    references.addObject(socket_obj)
    master = doc.addObject("Part::Feature", "Unsplit_Deck_Reference")
    master.Shape = master_deck
    master.Visibility = False
    references.addObject(master)

    assembly = doc.addObject("App::DocumentObjectGroup", "FlightDeckAssembly")
    category_groups = {}
    for label in ("MainDeckBody", "Elevators", "RaisedDeckMarkings", "CatapultTracks", "ArrestingWires"):
        category_groups[label] = doc.addObject("App::DocumentObjectGroup", label)
        assembly.addObject(category_groups[label])

    production_objects = []
    for index, module in enumerate(modules, 1):
        production_objects.append(
            add_part_object(doc, category_groups["MainDeckBody"], f"Main_Deck_Module_{index}", module, "deck_charcoal", "main_deck_body")
        )
    group_for_kind = {
        "elevator": "Elevators",
        "raised_marking": "RaisedDeckMarkings",
        "catapult_track": "CatapultTracks",
        "arresting_wire": "ArrestingWires",
    }
    for name, shape, material, kind in details:
        production_objects.append(add_part_object(doc, category_groups[group_for_kind[kind]], name, shape, material, kind))
    doc.recompute()
    return doc, production_objects


def shape_record(name, shape, kind):
    bounds = precise_bounds(shape)
    return {
        "name": name,
        "kind": kind,
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "volume_mm3": round(float(shape.Volume), 4),
        "bounds_mm": {
            "x": [round(bounds[0], 4), round(bounds[3], 4)],
            "y": [round(bounds[1], 4), round(bounds[4], 4)],
            "z": [round(bounds[2], 4), round(bounds[5], 4)],
            "size": [round(bounds[3] - bounds[0], 4), round(bounds[4] - bounds[1], 4), round(bounds[5] - bounds[2], 4)],
        },
    }


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    print("Building clean CVN-69 flight-deck BRep reconstruction")
    master_deck, island_tool, elevator_tools = make_deck_master()
    modules, tongues, sockets = split_deck(master_deck)
    elevators = make_elevators()
    markings = make_markings()
    catapults = make_catapults()
    arresting_wires = make_arresting_wires()
    details = elevators + markings + catapults + arresting_wires
    assembled = [
        (f"Main_Deck_Module_{index}", shape, "deck_charcoal", "main_deck_body")
        for index, shape in enumerate(modules, 1)
    ] + details

    doc, production_objects = create_document(
        master_deck,
        modules,
        island_tool,
        elevator_tools,
        tongues,
        sockets,
        details,
    )
    fcstd_path = DIRS["freecad"] / "CVN69_Flight_Deck_Reconstruction.FCStd"
    doc.saveAs(str(fcstd_path))

    step_path = DIRS["step"] / "CVN69_Flight_Deck_Assembly.step"
    Part.export(production_objects, str(step_path))
    write_obj(DIRS["obj"] / "CVN69_Flight_Deck_Assembly.obj", assembled)
    assembly_3mf = DIRS["3mf"] / "CVN69_Flight_Deck_Assembly.3mf"
    write_3mf(assembly_3mf, assembled, "CVN-69 Flight Deck Assembly Reference")

    output_paths = [
        fcstd_path,
        step_path,
        assembly_3mf,
        DIRS["obj"] / "CVN69_Flight_Deck_Assembly.obj",
        DIRS["obj"] / "CVN69_Flight_Deck_Assembly.mtl",
    ]
    total_facets = 0
    individual_print_parts = []
    for name, shape, material, kind in assembled:
        print_shape = print_oriented(shape)
        item = (name, print_shape, material, kind)
        individual_print_parts.append(item)
        stl_path = DIRS["stl"] / f"{name}.stl"
        total_facets += write_binary_stl(stl_path, [item])
        part_3mf = DIRS["3mf_individual"] / f"{name}.3mf"
        write_3mf(part_3mf, [item], name.replace("_", " "))
        output_paths.extend((stl_path, part_3mf))

    deck_layout = []
    cursor_y = 0.0
    for item in individual_print_parts[:3]:
        name, shape, material, kind = item
        placed = translate_to(shape, 0.0, cursor_y)
        bounds = precise_bounds(placed)
        deck_layout.append((name, placed, material, kind))
        cursor_y = bounds[4] + 2.5
    deck_plate = DIRS["3mf"] / "Print_Plate_01_Main_Deck.3mf"
    write_3mf(deck_plate, deck_layout, "CVN-69 Flight Deck — Main Deck Modules")
    output_paths.append(deck_plate)

    remaining = individual_print_parts[3:]
    plate_index = 2
    while remaining:
        layout, leftover = pack_plate(remaining)
        if not layout:
            raise RuntimeError("Detail packing made no progress")
        plate_path = DIRS["3mf"] / f"Print_Plate_{plate_index:02d}_Details.3mf"
        write_3mf(plate_path, layout, f"CVN-69 Flight Deck — Detail Plate {plate_index - 1}")
        output_paths.append(plate_path)
        remaining = leftover
        plate_index += 1

    records = [shape_record(name, shape, kind) for name, shape, _material, kind in assembled]
    manifest = {
        "project": "USS Dwight D. Eisenhower (CVN-69) 1:700 Flight Deck Reconstruction",
        "version": VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "freecad_version": ".".join(App.Version()[:3]),
        "geometry_method": "scripted OpenCascade BRep; source meshes used only as numerical and visual references",
        "scale": "1:700",
        "parameters_mm": {
            "overall_length": P.overall_length,
            "maximum_deck_width": max(y for _x, y in P.outline_points) - min(y for _x, y in P.outline_points),
            "deck_thickness": P.deck_thickness,
            "minimum_wall": P.minimum_wall,
            "raised_detail_minimum": [P.arresting_wire_width, P.arresting_wire_height],
            "fit_clearance_per_side": P.fit_clearance_per_side,
            "module_seams_x": list(P.split_seams),
        },
        "counts": {
            "main_deck_modules": 3,
            "elevators": len(elevators),
            "raised_marking_parts": len(markings),
            "catapult_tracks": len(catapults),
            "arresting_wires": len(arresting_wires),
            "printable_parts": len(assembled),
        },
        "shapes": records,
        "individual_stl_facets": total_facets,
        "outputs": {
            str(path.relative_to(DECK_PROJECT)): {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in output_paths
        },
    }
    manifest_path = DIRS["qa"] / "build_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    App.closeDocument(doc.Name)
    print(json.dumps({"status": "ok", "parts": len(assembled), "outputs": len(output_paths), "manifest": str(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()
