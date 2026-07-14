#!/usr/bin/env python3
"""Build Milestone 2 hull/flight-deck integration with FreeCAD.

Approved hull and flight-deck BReps are imported from their FCStd files.  Only
concealed socket cuts and new printed interface pads are introduced.
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
INTEGRATION = SCRIPT.parents[1]
PROJECT = INTEGRATION.parent
REPO = PROJECT.parent
sys.path.insert(0, str(INTEGRATION / "CAD" / "Python"))
from integration_parameters import make_parameters  # noqa: E402


P = make_parameters()

DIRS = {
    "freecad": INTEGRATION / "CAD" / "FreeCAD",
    "step": INTEGRATION / "STEP",
    "stl": INTEGRATION / "STL",
    "3mf": INTEGRATION / "3MF",
    "obj": INTEGRATION / "OBJ",
    "render": INTEGRATION / "Render",
    "docs": INTEGRATION / "Docs",
    "assembly": INTEGRATION / "Assembly",
    "qa": INTEGRATION / "QA",
}
for directory in DIRS.values():
    directory.mkdir(parents=True, exist_ok=True)


MATERIALS = OrderedDict(
    (
        ("ash_gray", ("Bambu PLA Matte Ash Gray", "#969890FF")),
        ("deck_charcoal", ("Bambu PLA Matte Charcoal", "#34383CFF")),
        ("ivory_white", ("Bambu PLA Matte Ivory White", "#ECE8D9FF")),
        ("silk_silver", ("Bambu PLA Silk Silver", "#AEB4B8FF")),
    )
)


HULL_FCSTD = PROJECT / "CAD" / "FreeCAD" / "Hull.FCStd"
DECK_FCSTD = PROJECT / "FlightDeck" / "CAD" / "FreeCAD" / "CVN69_Flight_Deck_Reconstruction.FCStd"
HULL_STEP = PROJECT / "STEP" / "Hull.step"
DECK_STEP = PROJECT / "FlightDeck" / "STEP" / "CVN69_Flight_Deck_Assembly.step"
HULL_MANIFEST = PROJECT / "QA" / "build_manifest.json"
DECK_MANIFEST = PROJECT / "FlightDeck" / "QA" / "build_manifest.json"


def v(x: float, y: float, z: float) -> App.Vector:
    return App.Vector(float(x), float(y), float(z))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def precise_bounds(shape):
    points, _faces = shape.tessellate(P.tessellation_deflection)
    if not points:
        raise RuntimeError("Cannot measure an empty shape")
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    zs = [point.z for point in points]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def validate_solid(name: str, shape):
    if shape.isNull() or not shape.isValid() or not shape.isClosed() or len(shape.Solids) != 1:
        raise RuntimeError(
            f"{name} is not one valid closed solid: valid={shape.isValid()} "
            f"closed={shape.isClosed()} solids={len(shape.Solids)}"
        )
    return shape


def load_approved_inputs():
    hull_doc = App.openDocument(str(HULL_FCSTD))
    hull_modules = []
    hull_accessories = []
    try:
        for index, source_name in enumerate(("Hull_Module_1", "Hull_Module_2", "Hull_Module_3"), 1):
            hull_modules.append((source_name, hull_doc.getObject(source_name).Shape.copy()))
        accessory_names = [
            item["name"]
            for item in json.loads(HULL_MANIFEST.read_text(encoding="utf-8"))["shapes"]
            if not item["name"].startswith("Hull_Module_")
        ]
        for name in accessory_names:
            hull_accessories.append((name, hull_doc.getObject(name).Shape.copy()))
    finally:
        App.closeDocument(hull_doc.Name)

    deck_doc = App.openDocument(str(DECK_FCSTD))
    deck_parts = []
    try:
        for obj in deck_doc.Objects:
            if not hasattr(obj, "PartCategory") or not hasattr(obj, "Shape") or obj.Shape.isNull():
                continue
            mirrored = obj.Shape.mirror(
                v(P.overall_length / 2.0, 0.0, 0.0),
                v(1.0, 0.0, 0.0),
            )
            mirrored.translate(v(0.0, 0.0, P.deck_base_z))
            deck_parts.append((obj.Name, str(obj.PartCategory), mirrored))
    finally:
        App.closeDocument(deck_doc.Name)
    return hull_modules, hull_accessories, deck_parts


def socket_centers():
    return [
        (station_index, side_name, x_center, y_center)
        for station_index, x_center in enumerate(P.pad_x_stations, 1)
        for side_name, y_center in (("Port", P.pad_y_centers[0]), ("Starboard", P.pad_y_centers[1]))
    ]


def make_socket_tools():
    hull_tools = []
    deck_tools = []
    for _station_index, _side_name, x_center, y_center in socket_centers():
        x0 = x_center - P.socket_length / 2.0
        y0 = y_center - P.socket_width / 2.0
        hull_tools.append(
            Part.makeBox(
                P.socket_length,
                P.socket_width,
                P.hull_socket_depth + P.socket_opening_allowance,
                v(x0, y0, P.hull.molded_depth - P.hull_socket_depth),
            )
        )
        deck_tools.append(
            Part.makeBox(
                P.socket_length,
                P.socket_width,
                P.deck_socket_depth + P.socket_opening_allowance,
                v(x0, y0, P.deck_base_z - P.socket_opening_allowance),
            )
        )
    return Part.makeCompound(hull_tools), Part.makeCompound(deck_tools)


def integrate_hull_modules(hull_modules, hull_socket_tools):
    result = []
    labels = ("Hull_Module_1_Bow", "Hull_Module_2_Midship", "Hull_Module_3_Stern")
    for label, (source_name, source_shape) in zip(labels, hull_modules):
        shape = source_shape.cut(hull_socket_tools).removeSplitter()
        validate_solid(label, shape)
        result.append((label, shape, "ash_gray", "hull_module", source_name))
    return result


def integrate_deck_parts(deck_parts, deck_socket_tools):
    module_map = {
        "Main_Deck_Module_3": "Deck_Module_1_Bow",
        "Main_Deck_Module_2": "Deck_Module_2_Midship",
        "Main_Deck_Module_1": "Deck_Module_3_Stern",
    }
    result = []
    for source_name, category, source_shape in deck_parts:
        name = module_map.get(source_name, source_name)
        shape = source_shape
        if category == "main_deck_body":
            shape = shape.cut(deck_socket_tools).removeSplitter()
        validate_solid(name, shape)
        if category == "main_deck_body":
            material, kind = "deck_charcoal", "deck_module"
        elif category == "elevator":
            material, kind = "deck_charcoal", "elevator"
        elif category == "raised_marking":
            material, kind = "ivory_white", "raised_marking"
        elif category in ("catapult_track", "arresting_wire"):
            material, kind = "silk_silver", category
        else:
            raise RuntimeError(f"Unsupported approved deck category: {category}")
        result.append((name, shape, material, kind, source_name))
    order = {"Deck_Module_1_Bow": 0, "Deck_Module_2_Midship": 1, "Deck_Module_3_Stern": 2}
    result.sort(key=lambda item: (0, order[item[0]]) if item[0] in order else (1, item[0]))
    return result


def classify_hull_accessories(hull_accessories):
    result = []
    for name, shape in hull_accessories:
        validate_solid(name, shape)
        if name.startswith(("Shaft_", "Propeller_")) and "Strut" not in name:
            material = "silk_silver"
        else:
            material = "ash_gray"
        if name.startswith("Propeller_"):
            kind = "propeller"
        elif "Strut" in name:
            kind = "strut"
        elif name.startswith("Shaft_"):
            kind = "shaft"
        elif name.startswith("Rudder_"):
            kind = "rudder"
        else:
            kind = "hull_accessory"
        result.append((name, shape, material, kind, name))
    return result


def make_interface_pads():
    result = []
    z0 = P.hull.molded_depth - P.pad_hull_insertion
    for station_index, side_name, x_center, y_center in socket_centers():
        name = f"Interface_Pad_{station_index:02d}_{side_name}"
        shape = Part.makeBox(
            P.pad_length,
            P.pad_width,
            P.pad_total_height,
            v(
                x_center - P.pad_length / 2.0,
                y_center - P.pad_width / 2.0,
                z0,
            ),
        )
        validate_solid(name, shape)
        result.append((name, shape, "ash_gray", "interface_pad", "new integration geometry"))
    return result


def make_test_coupon():
    width = 25.0
    depth = 20.0
    male_base_height = 4.0
    male = Part.makeBox(width, depth, male_base_height, v(0, 0, 0))
    male_pad = Part.makeBox(
        P.pad_length,
        P.pad_width,
        P.pad_deck_insertion,
        v(
            width / 2.0 - P.pad_length / 2.0,
            depth / 2.0 - P.pad_width / 2.0,
            male_base_height,
        ),
    )
    male = male.fuse(male_pad).removeSplitter()

    female_z = male_base_height
    female = Part.makeBox(width, depth, P.deck.deck_thickness, v(0, 0, female_z))
    female_socket = Part.makeBox(
        P.socket_length,
        P.socket_width,
        P.deck_socket_depth + P.socket_opening_allowance,
        v(
            width / 2.0 - P.socket_length / 2.0,
            depth / 2.0 - P.socket_width / 2.0,
            female_z - P.socket_opening_allowance,
        ),
    )
    female = female.cut(female_socket).removeSplitter()
    validate_solid("Interface_Test_Coupon_Male", male)
    validate_solid("Interface_Test_Coupon_Female", female)
    return [
        ("Interface_Test_Coupon_Male", male, "ash_gray", "test_coupon", "new integration geometry"),
        ("Interface_Test_Coupon_Female", female, "deck_charcoal", "test_coupon", "new integration geometry"),
    ]


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
    if length <= 1.0e-16:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def write_binary_stl(path: Path, named_shapes):
    facets = []
    for _name, shape, _material, _kind, _source in named_shapes:
        vertices, triangles = triangulate(shape)
        for triangle in triangles:
            a, b, c = (vertices[index] for index in triangle)
            facets.append((triangle_normal(a, b, c), a, b, c))
    header = b"CVN-69 Milestone 2 hull-deck integration"[:80].ljust(80, b" ")
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
    for _name, shape, material, _kind, _source in named_shapes:
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
        for name, shape, material, _kind, _source in named_shapes:
            vertices, triangles = triangulate(shape)
            obj.write(f"o {name}\nusemtl {material}\n")
            for x, y, z in vertices:
                obj.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
            for a, b, c in triangles:
                obj.write(f"f {a + offset} {b + offset} {c + offset}\n")
            offset += len(vertices)


def placed_on_bed(shape, rotation=None, target_x=0.0, target_y=0.0):
    result = shape.copy()
    if rotation is not None:
        result.Placement = App.Placement(v(0, 0, 0), rotation)
    bounds = precise_bounds(result)
    result.translate(v(target_x - bounds[0], target_y - bounds[1], -bounds[2]))
    return result


def make_hull_plate(hull_parts):
    modules = [item for item in hull_parts if item[3] == "hull_module"]
    accessories = [item for item in hull_parts if item[3] != "hull_module"]
    layout = []
    lane_y = 0.0
    for name, shape, material, kind, source in modules:
        oriented = placed_on_bed(shape, App.Rotation(v(1, 0, 0), 180), 0.0, lane_y)
        layout.append((name, oriented, material, kind, source))
        lane_y = precise_bounds(oriented)[4] + 1.5
    column_x = max(precise_bounds(item[1])[3] for item in layout) + 4.0
    cursor_y = 0.0
    max_width = 0.0
    for name, shape, material, kind, source in accessories:
        rotation = App.Rotation(v(0, 1, 0), 90) if kind == "propeller" else App.Rotation(v(1, 0, 0), 90)
        oriented = placed_on_bed(shape, rotation, column_x, cursor_y)
        bounds = precise_bounds(oriented)
        if bounds[4] > 232.0:
            column_x += max_width + 2.0
            cursor_y = 0.0
            max_width = 0.0
            oriented = placed_on_bed(shape, rotation, column_x, cursor_y)
            bounds = precise_bounds(oriented)
        layout.append((name, oriented, material, kind, source))
        cursor_y = bounds[4] + 1.5
        max_width = max(max_width, bounds[3] - bounds[0])
    return layout


def make_deck_plate(deck_parts):
    layout = []
    lane_y = 0.0
    for item in [part for part in deck_parts if part[3] == "deck_module"]:
        name, shape, material, kind, source = item
        oriented = placed_on_bed(shape, None, 0.0, lane_y)
        layout.append((name, oriented, material, kind, source))
        lane_y = precise_bounds(oriented)[4] + 2.5
    return layout


def pack_plate(parts, max_size=235.0, gap=2.5):
    layout = []
    cursor_x = 0.0
    cursor_y = 0.0
    row_height = 0.0
    for name, shape, material, kind, source in parts:
        oriented = placed_on_bed(shape)
        bounds = precise_bounds(oriented)
        width = bounds[3] - bounds[0]
        depth = bounds[4] - bounds[1]
        if width > max_size or depth > max_size:
            raise RuntimeError(f"{name} exceeds detail-plate envelope")
        if cursor_x > 0.0 and cursor_x + width > max_size:
            cursor_x = 0.0
            cursor_y += row_height + gap
            row_height = 0.0
        if cursor_y + depth > max_size:
            raise RuntimeError(f"Detail plate overflow while placing {name}")
        oriented.translate(v(cursor_x, cursor_y, 0.0))
        layout.append((name, oriented, material, kind, source))
        cursor_x += width + gap
        row_height = max(row_height, depth)
    return layout


def add_spreadsheet(doc):
    sheet = doc.addObject("Spreadsheet::Sheet", "IntegrationParameters")
    rows = [
        ("Parameter", "Value", "Unit / note"),
        ("Overall length", P.overall_length, "mm; imported from approved inputs"),
        ("Coordinate X", "0 bow → 476 stern", "authoritative"),
        ("Coordinate Y", "port (-) → starboard (+)", "authoritative"),
        ("Coordinate Z", "vertical", "hull keel datum"),
        ("Deck source transform", "x' = 476 - x", "mirror about x=238 mm"),
        ("Deck base elevation", P.deck_base_z, "mm"),
        ("Hull seams", ", ".join(f"{value:.3f}" for value in P.hull_module_seams), "x mm"),
        ("Deck seams", ", ".join(f"{value:.3f}" for value in P.deck_authoritative_seams), "x mm"),
        ("Pad stations", ", ".join(f"{value:.1f}" for value in P.pad_x_stations), "x mm"),
        ("Pad size", f"{P.pad_length} × {P.pad_width} × {P.pad_total_height}", "mm"),
        ("Socket size", f"{P.socket_length} × {P.socket_width}", "mm"),
        ("Clearance", P.interface_clearance_per_side, "mm per side"),
        ("Hull insertion", P.pad_hull_insertion, "mm"),
        ("Deck insertion", P.pad_deck_insertion, "mm"),
        ("Deck socket depth", P.deck_socket_depth, "mm"),
        ("Deck top skin", P.deck_top_skin_over_socket, "mm"),
        ("Seating gap", P.seating_gap, "mm nominal"),
    ]
    for row_index, row in enumerate(rows, 1):
        for column_index, value in enumerate(row, 1):
            sheet.set(f"{chr(64 + column_index)}{row_index}", str(value))
    sheet.setStyle("A1:C1", "bold", "add")
    sheet.setColumnWidth("A", 190)
    sheet.setColumnWidth("B", 190)
    sheet.setColumnWidth("C", 220)
    return sheet


def add_part(doc, group, item):
    name, shape, material, kind, source = item
    obj = doc.addObject("Part::Feature", name)
    obj.Label = name.replace("_", " ")
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "IntegrationRole").IntegrationRole = kind
    obj.addProperty("App::PropertyString", "Material").Material = MATERIALS[material][0]
    obj.addProperty("App::PropertyString", "SourceObject").SourceObject = source
    obj.addProperty("App::PropertyString", "PrintOrientation").PrintOrientation = "See print-oriented STL; minimum z = 0"
    colors = {
        "ash_gray": (0.59, 0.60, 0.56),
        "deck_charcoal": (0.20, 0.22, 0.24),
        "ivory_white": (0.92, 0.90, 0.84),
        "silk_silver": (0.68, 0.71, 0.73),
    }
    try:
        obj.ViewObject.ShapeColor = colors[material]
    except Exception:
        pass
    group.addObject(obj)
    return obj


def create_document(hull_parts, deck_parts, interface_pads, coupon_parts, hull_tools, deck_tools):
    doc = App.newDocument("CVN69_Hull_Deck_Integration")
    info = doc.addObject("App::FeaturePython", "MilestoneInformation")
    info.addProperty("App::PropertyString", "ProjectName").ProjectName = "USS Dwight D. Eisenhower (CVN-69) Museum Edition"
    info.addProperty("App::PropertyString", "Milestone").Milestone = P.milestone
    info.addProperty("App::PropertyString", "Version").Version = P.version
    info.addProperty("App::PropertyString", "CoordinateSystem").CoordinateSystem = "X bow→stern; Y port(-)→starboard(+); Z vertical"
    info.addProperty("App::PropertyString", "ApprovedInputs").ApprovedInputs = "Hull v0.1.0 and FlightDeck review package; external shapes preserved"
    info.addProperty("App::PropertyString", "Interface").Interface = "Twelve separate keyed landing pads; 0.25 mm clearance per side; direct hidden seating/glue plane"
    info.addProperty("App::PropertyString", "ScopeBoundary").ScopeBoundary = "No island, weapons, aircraft, radar, ocean base, or display stand"
    info.addProperty("App::PropertyString", "Generator").Generator = str(SCRIPT.relative_to(REPO))
    add_spreadsheet(doc)

    references = doc.addObject("App::DocumentObjectGroup", "ConstructionReferences")
    centerline = doc.addObject("Part::Feature", "Authoritative_Centerline")
    centerline.Shape = Part.makeLine(v(0, 0, P.deck_base_z), v(P.overall_length, 0, P.deck_base_z))
    centerline.Visibility = False
    references.addObject(centerline)
    for name, x_value in (("Bow_Datum", 0.0), ("Stern_Datum", P.overall_length)):
        datum = doc.addObject("Part::Feature", name)
        datum.Shape = Part.makeLine(v(x_value, -45, P.deck_base_z), v(x_value, 45, P.deck_base_z))
        datum.Visibility = False
        references.addObject(datum)
    hull_tool_obj = doc.addObject("Part::Feature", "Hull_Interface_Socket_Tools")
    hull_tool_obj.Shape = hull_tools
    hull_tool_obj.Visibility = False
    references.addObject(hull_tool_obj)
    deck_tool_obj = doc.addObject("Part::Feature", "Deck_Interface_Socket_Tools")
    deck_tool_obj.Shape = deck_tools
    deck_tool_obj.Visibility = False
    references.addObject(deck_tool_obj)

    assembly = doc.addObject("App::DocumentObjectGroup", "HullDeckAssembly")
    hull_group = doc.addObject("App::DocumentObjectGroup", "IntegratedHull")
    deck_group = doc.addObject("App::DocumentObjectGroup", "IntegratedFlightDeck")
    pads_group = doc.addObject("App::DocumentObjectGroup", "ConcealedInterfacePads")
    coupon_group = doc.addObject("App::DocumentObjectGroup", "InterfaceTestCoupon")
    for group in (hull_group, deck_group, pads_group, coupon_group):
        assembly.addObject(group)

    production_objects = []
    for item in hull_parts:
        production_objects.append(add_part(doc, hull_group, item))
    for item in deck_parts:
        production_objects.append(add_part(doc, deck_group, item))
    for item in interface_pads:
        production_objects.append(add_part(doc, pads_group, item))
    coupon_objects = [add_part(doc, coupon_group, item) for item in coupon_parts]
    for obj in coupon_objects:
        obj.Visibility = False
    doc.recompute()
    return doc, production_objects, coupon_objects


def shape_record(item):
    name, shape, material, kind, source = item
    bounds = precise_bounds(shape)
    return {
        "name": name,
        "kind": kind,
        "material": MATERIALS[material][0],
        "source": source,
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "volume_mm3": round(float(shape.Volume), 5),
        "bounds_mm": {
            "x": [round(bounds[0], 5), round(bounds[3], 5)],
            "y": [round(bounds[1], 5), round(bounds[4], 5)],
            "z": [round(bounds[2], 5), round(bounds[5], 5)],
            "size": [round(bounds[3] - bounds[0], 5), round(bounds[4] - bounds[1], 5), round(bounds[5] - bounds[2], 5)],
        },
    }


def input_inspection():
    records = []
    for path in (HULL_FCSTD, HULL_STEP, HULL_MANIFEST, DECK_FCSTD, DECK_STEP, DECK_MANIFEST):
        records.append(
            {
                "path": str(path.relative_to(REPO)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    report = {
        "inspected_utc": datetime.now(timezone.utc).isoformat(),
        "freecad_version": ".".join(App.Version()[:3]),
        "authoritative_coordinate_system": {
            "x": "0 mm bow to 476 mm stern",
            "y": "port negative to starboard positive",
            "z": "vertical; hull keel datum",
        },
        "approved_hull": {
            "overall_length_mm": P.hull.overall_length,
            "molded_depth_mm": P.hull.molded_depth,
            "module_seams_x_mm": list(P.hull_module_seams),
        },
        "approved_flight_deck": {
            "overall_length_mm": P.deck.overall_length,
            "source_seams_x_mm": list(P.deck_source_seams),
            "authoritative_seams_x_mm": list(P.deck_authoritative_seams),
            "transform": "mirror about x=238 mm; preserve y; translate z by hull molded depth",
        },
        "files": records,
    }
    path = DIRS["qa"] / "Approved_Input_Inspection.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path


def main():
    print("Building CVN-69 Milestone 2 hull/deck integration")
    inspection_path = input_inspection()
    source_hull_modules, source_hull_accessories, source_deck_parts = load_approved_inputs()
    hull_tools, deck_tools = make_socket_tools()
    hull_modules = integrate_hull_modules(source_hull_modules, hull_tools)
    hull_accessories = classify_hull_accessories(source_hull_accessories)
    hull_parts = hull_modules + hull_accessories
    deck_parts = integrate_deck_parts(source_deck_parts, deck_tools)
    interface_pads = make_interface_pads()
    coupon_parts = make_test_coupon()
    production_parts = hull_parts + deck_parts + interface_pads

    doc, production_objects, coupon_objects = create_document(
        hull_parts,
        deck_parts,
        interface_pads,
        coupon_parts,
        hull_tools,
        deck_tools,
    )
    fcstd_path = DIRS["freecad"] / "CVN69_Hull_Deck_Integration.FCStd"
    doc.saveAs(str(fcstd_path))

    assembly_step = DIRS["step"] / "CVN69_Hull_Deck_Assembly.step"
    Part.export(production_objects, str(assembly_step))
    coupon_step = DIRS["step"] / "Interface_Test_Coupon.step"
    Part.export(coupon_objects, str(coupon_step))

    obj_path = DIRS["obj"] / "CVN69_Hull_Deck_Assembly.obj"
    write_obj(obj_path, production_parts)
    assembly_3mf = DIRS["3mf"] / "CVN69_Hull_Deck_Assembly.3mf"
    write_3mf(assembly_3mf, production_parts, "CVN-69 Hull and Flight Deck Assembly")

    hull_plate = make_hull_plate(hull_parts)
    deck_plate = make_deck_plate(deck_parts)
    detail_parts = [item for item in deck_parts if item[3] != "deck_module"] + interface_pads
    details_plate = pack_plate(detail_parts)
    plate_paths = [
        DIRS["3mf"] / "Print_Plate_01_Hull.3mf",
        DIRS["3mf"] / "Print_Plate_02_Deck.3mf",
        DIRS["3mf"] / "Print_Plate_03_Details.3mf",
    ]
    write_3mf(plate_paths[0], hull_plate, "CVN-69 Integration — Hull Plate")
    write_3mf(plate_paths[1], deck_plate, "CVN-69 Integration — Flight Deck Plate")
    write_3mf(plate_paths[2], details_plate, "CVN-69 Integration — Detail and Interface Plate")

    coupon_print = []
    cursor_x = 0.0
    for item in coupon_parts:
        name, shape, material, kind, source = item
        oriented = placed_on_bed(shape, None, cursor_x, 0.0)
        coupon_print.append((name, oriented, material, kind, source))
        cursor_x = precise_bounds(oriented)[3] + 3.0
    coupon_3mf = DIRS["3mf"] / "Interface_Test_Coupon.3mf"
    write_3mf(coupon_3mf, coupon_print, "CVN-69 Deck-to-Hull Interface Test Coupon")

    output_paths = [
        inspection_path,
        fcstd_path,
        assembly_step,
        coupon_step,
        obj_path,
        obj_path.with_suffix(".mtl"),
        assembly_3mf,
        *plate_paths,
        coupon_3mf,
    ]
    stl_facets = {}
    print_parts = []
    for item in production_parts:
        name, shape, material, kind, source = item
        if kind == "hull_module":
            oriented = placed_on_bed(shape, App.Rotation(v(1, 0, 0), 180))
        elif kind == "propeller":
            oriented = placed_on_bed(shape, App.Rotation(v(0, 1, 0), 90))
        elif kind in ("shaft", "strut", "rudder"):
            oriented = placed_on_bed(shape, App.Rotation(v(1, 0, 0), 90))
        else:
            oriented = placed_on_bed(shape)
        print_item = (name, oriented, material, kind, source)
        print_parts.append(print_item)
        stl_path = DIRS["stl"] / f"{name}.stl"
        stl_facets[stl_path.name] = write_binary_stl(stl_path, [print_item])
        output_paths.append(stl_path)
    for item in coupon_parts:
        name, shape, material, kind, source = item
        oriented = placed_on_bed(shape)
        stl_path = DIRS["stl"] / f"{name}.stl"
        stl_facets[stl_path.name] = write_binary_stl(stl_path, [(name, oriented, material, kind, source)])
        output_paths.append(stl_path)

    records = [shape_record(item) for item in production_parts]
    coupon_records = [shape_record(item) for item in coupon_parts]
    manifest = {
        "project": "USS Dwight D. Eisenhower (CVN-69) Museum Edition",
        "milestone": P.milestone,
        "version": P.version,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "freecad_version": ".".join(App.Version()[:3]),
        "coordinate_system": {
            "x": "0 bow to 476 stern",
            "y": "port negative to starboard positive",
            "z": "vertical from hull keel datum",
            "deck_source_transform": "x_authoritative = 476 - x_source; y unchanged; z += 31.5",
        },
        "parameters_mm": {
            "overall_length": P.overall_length,
            "deck_base_z": P.deck_base_z,
            "hull_module_seams": list(P.hull_module_seams),
            "deck_module_seams": list(P.deck_authoritative_seams),
            "interface_clearance_per_side": P.interface_clearance_per_side,
            "pad_size": [P.pad_length, P.pad_width, P.pad_total_height],
            "pad_x_stations": list(P.pad_x_stations),
            "pad_y_centers": list(P.pad_y_centers),
            "hull_socket_depth": P.hull_socket_depth,
            "deck_socket_depth": P.deck_socket_depth,
            "deck_top_skin_over_socket": P.deck_top_skin_over_socket,
            "vertical_pad_tip_clearance": P.vertical_pad_tip_clearance,
            "nominal_seating_gap": P.seating_gap,
        },
        "counts": {
            "hull_modules": len(hull_modules),
            "hull_accessories": len(hull_accessories),
            "deck_modules": sum(item[3] == "deck_module" for item in deck_parts),
            "deck_details": sum(item[3] != "deck_module" for item in deck_parts),
            "interface_pads": len(interface_pads),
            "production_parts": len(production_parts),
            "coupon_parts": len(coupon_parts),
        },
        "material_mapping": {item[0]: MATERIALS[item[2]][0] for item in production_parts},
        "shapes": records,
        "coupon_shapes": coupon_records,
        "stl_facets": stl_facets,
        "approved_input_hashes": {
            str(path.relative_to(REPO)): sha256(path)
            for path in (HULL_FCSTD, HULL_STEP, HULL_MANIFEST, DECK_FCSTD, DECK_STEP, DECK_MANIFEST)
        },
        "outputs": {
            str(path.relative_to(INTEGRATION)): {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in output_paths
        },
    }
    manifest_path = DIRS["qa"] / "build_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    App.closeDocument(doc.Name)
    print(
        json.dumps(
            {
                "status": "ok",
                "production_parts": len(production_parts),
                "coupon_parts": len(coupon_parts),
                "stl_files": len(stl_facets),
                "manifest": str(manifest_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
