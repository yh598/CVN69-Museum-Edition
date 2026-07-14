#!/usr/bin/env python3
"""Build Milestone 1 with FreeCAD's Python runtime.

Run from the repository root:
  /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \
    "globals()['__file__']='Project/Scripts/build_milestone_1.py'; \
     exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"

The script is deterministic and may be rerun from any working directory.
It creates editable FreeCAD source, STEP, print-oriented STL/3MF, OBJ, a JSON
build manifest, and individual A1 Mini-compatible component STLs.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
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
PROJECT = SCRIPT.parents[1]
sys.path.insert(0, str(PROJECT / "CAD" / "Python"))
from hull_parameters import HullParameters, make_parameters  # noqa: E402


VERSION = "0.1.0"
SCALE = int(os.environ.get("CVN69_SCALE", "700"))
P = make_parameters(SCALE)

DIRS = {
    "freecad": PROJECT / "CAD" / "FreeCAD",
    "stl": PROJECT / "STL",
    "step": PROJECT / "STEP",
    "3mf": PROJECT / "3MF",
    "obj": PROJECT / "OBJ",
    "render": PROJECT / "Render",
    "docs": PROJECT / "Docs",
    "images": PROJECT / "Images",
    "assembly": PROJECT / "Assembly",
    "print": PROJECT / "Print",
    "qa": PROJECT / "QA",
    "release": PROJECT / "Releases" / f"v{VERSION}",
}
for directory in DIRS.values():
    directory.mkdir(parents=True, exist_ok=True)


MATERIALS = OrderedDict(
    (
        ("ash_gray", ("PLA Matte Ash Gray", "#969890FF")),
        ("charcoal", ("PLA Matte Charcoal", "#34373AFF")),
        ("gold", ("PLA Basic Gold", "#C59A32FF")),
        ("silk_silver", ("PLA Silk Silver", "#AEB4B8FF")),
    )
)


def v(x: float, y: float, z: float) -> App.Vector:
    return App.Vector(float(x), float(y), float(z))


def interp_stations(x_ratio: float, attribute: str) -> float:
    stations = P.stations
    if x_ratio <= stations[0].x_ratio:
        return float(getattr(stations[0], attribute))
    if x_ratio >= stations[-1].x_ratio:
        return float(getattr(stations[-1], attribute))
    for left, right in zip(stations[:-1], stations[1:]):
        if left.x_ratio <= x_ratio <= right.x_ratio:
            t = (x_ratio - left.x_ratio) / (right.x_ratio - left.x_ratio)
            return (1.0 - t) * float(getattr(left, attribute)) + t * float(
                getattr(right, attribute)
            )
    raise RuntimeError("Station interpolation failed")


def section_values(x_ratio: float):
    # Interpolating a C2 transverse curve introduces a small analytic bulge
    # between breadth control points.  This compensation makes the measured
    # tessellated maximum match the configured molded beam (rather than
    # silently exceeding it by about 0.8%).
    half_beam = (P.maximum_hull_beam / 2.0) * 0.9915
    top = half_beam * interp_stations(x_ratio, "top_beam_factor")
    water = half_beam * interp_stations(x_ratio, "waterline_beam_factor")
    lower = half_beam * interp_stations(x_ratio, "lower_beam_factor")
    # Lift the analytic keel datum by a tiny tessellation-safe allowance; the
    # unconstrained C2 transverse spline otherwise overshoots about 0.06 mm
    # below z=0 between its final two control points.
    keel = P.molded_depth * interp_stations(x_ratio, "keel_rise_ratio") + 0.07 * P.scale_factor
    return top, water, lower, keel


def section_wire(x_ratio: float) -> Part.Wire:
    """Create one smooth, closed transverse section at x/L."""
    x = P.overall_length * x_ratio
    top, water, lower, keel = section_values(x_ratio)
    depth = P.molded_depth
    wl = P.waterline_height

    # Starboard deck edge to keel.  Multiple lower points preserve the bulb
    # without introducing hard chines at the default tessellation tolerance.
    side = [
        v(x, top, depth),
        v(x, top, depth * 0.930),
        v(x, top, depth * 0.820),
        v(x, 0.45 * top + 0.55 * water, depth * 0.705),
        v(x, water, wl),
        v(x, 0.96 * water + 0.04 * lower, depth * 0.405),
        v(x, lower, depth * 0.285),
        v(x, lower * 0.82, depth * 0.185 + keel * 0.15),
        v(x, lower * 0.54, depth * 0.090 + keel * 0.45),
        v(x, lower * 0.24, depth * 0.030 + keel * 0.75),
        v(x, 0.0, keel),
    ]

    starboard_curve = Part.BSplineCurve()
    starboard_curve.interpolate(side)
    starboard_edge = starboard_curve.toShape()

    port = [v(point.x, -point.y, point.z) for point in reversed(side)]
    port_curve = Part.BSplineCurve()
    port_curve.interpolate(port)
    port_edge = port_curve.toShape()

    top_edge = Part.makeLine(port[-1], side[0])
    return Part.Wire([starboard_edge, port_edge, top_edge])


def make_outer_hull():
    wires = [section_wire(station.x_ratio) for station in P.stations]
    hull = Part.makeLoft(wires, True, False)
    if hull.isNull() or not hull.isValid() or not hull.isClosed():
        raise RuntimeError("Base hull loft is not a valid closed solid")
    return hull, wires


def groove_wire(x_ratio: float, starboard: bool) -> Part.Wire:
    x = P.overall_length * x_ratio
    _top, water, _lower, _keel = section_values(x_ratio)
    sign = 1.0 if starboard else -1.0
    inner = sign * (water - P.waterline_groove_depth)
    outer = sign * (water + 0.80)
    if not starboard:
        inner, outer = outer, inner
    z0 = P.waterline_height - P.waterline_groove_height / 2.0
    z1 = P.waterline_height + P.waterline_groove_height / 2.0
    points = [v(x, inner, z0), v(x, outer, z0), v(x, outer, z1), v(x, inner, z1)]
    return Part.makePolygon(points + [points[0]])


def add_waterline_groove(hull):
    usable = [s for s in P.stations if s.x_ratio >= 0.010]
    cutters = []
    for side in (True, False):
        wires = [groove_wire(s.x_ratio, side) for s in usable]
        cutters.append(Part.makeLoft(wires, True, False))
    detailed = hull.cut(Part.makeCompound(cutters))
    if not detailed.isValid() or not detailed.isClosed():
        raise RuntimeError("Waterline groove produced invalid geometry")
    return detailed, Part.makeCompound(cutters)


def add_anchor_recesses(hull):
    x_ratio = 0.112
    x = P.overall_length * x_ratio
    top, water, _lower, _keel = section_values(x_ratio)
    z = P.waterline_height + 0.19 * P.molded_depth
    local_beam = 0.64 * top + 0.36 * water
    r = P.anchor_recess_radius
    cutters = []
    for sign in (-1.0, 1.0):
        center = v(x, sign * (local_beam + r * 0.52), z)
        cutters.append(Part.makeSphere(r, center))
    pockets = Part.makeCompound(cutters)
    detailed = hull.cut(pockets)
    if not detailed.isValid() or not detailed.isClosed():
        raise RuntimeError("Anchor recess operation produced invalid geometry")
    return detailed, pockets


def make_box_segment(shape, x0: float, x1: float):
    box = Part.makeBox(x1 - x0 + 0.20, 2.2 * P.maximum_hull_beam, 2.0 * P.molded_depth, v(x0 - 0.10, -1.1 * P.maximum_hull_beam, -0.25 * P.molded_depth))
    return shape.common(box)


def joint_specs(seam_index: int):
    """Two asymmetric keys make orientation and registration unambiguous."""
    sf = P.scale_factor
    return (
        (-0.175 * P.maximum_hull_beam, 0.43 * P.molded_depth, max(5.4, 7.2 * sf), max(3.8, 5.0 * sf)),
        (0.145 * P.maximum_hull_beam, 0.64 * P.molded_depth, max(4.8, 6.2 * sf), max(3.5, 4.6 * sf)),
    )


def male_key(seam: float, spec):
    y, z, width, height = spec
    embed = max(0.80, 1.0 * P.scale_factor)
    return Part.makeBox(P.joint_length + embed, width, height, v(seam - embed, y - width / 2.0, z - height / 2.0))


def female_socket(seam: float, spec):
    y, z, width, height = spec
    c = P.joint_clearance
    return Part.makeBox(P.joint_length + 0.65, width + 2.0 * c, height + 2.0 * c, v(seam - 0.10, y - width / 2.0 - c, z - height / 2.0 - c))


def split_hull(hull):
    seams = [P.overall_length * i / P.module_count for i in range(1, P.module_count)]
    limits = [0.0] + seams + [P.overall_length]
    segments = [make_box_segment(hull, a, b) for a, b in zip(limits[:-1], limits[1:])]

    for seam_index, seam in enumerate(seams):
        specs = joint_specs(seam_index)
        for spec in specs:
            segments[seam_index] = segments[seam_index].fuse(male_key(seam, spec))
            segments[seam_index + 1] = segments[seam_index + 1].cut(female_socket(seam, spec))

    refined = []
    for index, segment in enumerate(segments):
        segment = segment.removeSplitter()
        if not segment.isValid() or not segment.isClosed():
            raise RuntimeError(f"Hull segment {index + 1} failed solid validation")
        refined.append(segment)
    return refined, seams


def prism_between(start: App.Vector, end: App.Vector, radius: float, sides: int = 6):
    axis = end.sub(start)
    length = axis.Length
    points = []
    for i in range(sides):
        angle = 2.0 * math.pi * i / sides + math.pi / 6.0
        points.append(v(0.0, radius * math.cos(angle), radius * math.sin(angle)))
    wire = Part.makePolygon(points + [points[0]])
    prism = Part.Face(wire).extrude(v(length, 0.0, 0.0))
    prism.Placement = App.Placement(start, App.Rotation(v(1, 0, 0), axis))
    return prism


def make_propeller(center: App.Vector, radius: float, bore_radius: float):
    hub = Part.makeCylinder(max(0.90, radius * 0.27), max(1.8, radius * 0.50), center.add(v(-radius * 0.25, 0, 0)), v(1, 0, 0))
    blades = []
    thickness = max(0.48, 0.58 * P.scale_factor)
    root = radius * 0.22
    for blade_index in range(5):
        # A swept, printable five-blade silhouette in the propeller plane.
        poly = [
            v(center.x - thickness / 2.0, center.y + root, center.z - radius * 0.11),
            v(center.x - thickness / 2.0, center.y + radius * 0.92, center.z + radius * 0.09),
            v(center.x - thickness / 2.0, center.y + radius * 0.68, center.z + radius * 0.31),
            v(center.x - thickness / 2.0, center.y + root * 0.75, center.z + radius * 0.12),
        ]
        face = Part.Face(Part.makePolygon(poly + [poly[0]]))
        blade = face.extrude(v(thickness, 0, 0))
        blade.rotate(center, v(1, 0, 0), blade_index * 72.0)
        blades.append(blade)
    propeller = hub.fuse(Part.makeCompound(blades)).removeSplitter()
    # Blind hex-shaft pilot socket.  It is hidden after assembly and prevents
    # a propeller from being glued off-axis.
    bore_start = center.add(v(-radius * 0.31, 0, 0))
    bore = Part.makeCylinder(bore_radius, radius * 0.47, bore_start, v(1, 0, 0))
    propeller = propeller.cut(bore).removeSplitter()
    if not propeller.isValid():
        raise RuntimeError("Propeller solid is invalid")
    return propeller


def make_rudder(y_center: float):
    sf = P.scale_factor
    x0 = P.overall_length * 0.935
    length = max(11.5, 16.0 * sf)
    z0 = -max(4.5, 6.0 * sf)
    height = max(7.0, 9.8 * sf)
    points = [
        v(x0, y_center - P.rudder_thickness / 2.0, z0 + height),
        v(x0 + length * 0.80, y_center - P.rudder_thickness / 2.0, z0 + height * 0.86),
        v(x0 + length, y_center - P.rudder_thickness / 2.0, z0 + height * 0.10),
        v(x0 + length * 0.20, y_center - P.rudder_thickness / 2.0, z0),
    ]
    blade = Part.Face(Part.makePolygon(points + [points[0]])).extrude(v(0, P.rudder_thickness, 0))
    # Concealed rectangular stock enters a matching stern socket.
    pin_width = max(2.8, 3.8 * sf)
    pin_length = max(2.6, 3.5 * sf)
    pin_height = max(2.2, 3.0 * sf)
    pin = Part.makeBox(
        pin_length,
        P.rudder_thickness,
        pin_height,
        v(x0 + length * 0.20, y_center - P.rudder_thickness / 2.0, z0 + height - 0.7),
    )
    rudder = blade.fuse(pin).removeSplitter()
    clearance = P.joint_clearance
    socket = Part.makeBox(
        pin_length + 0.8,
        P.rudder_thickness + 2.0 * clearance,
        (z0 + height + pin_height + 0.2) - min(-0.6 * sf, z0 + height - 1.2),
        v(
            x0 + length * 0.20 - 0.2,
            y_center - P.rudder_thickness / 2.0 - clearance,
            min(-0.6 * sf, z0 + height - 1.2),
        ),
    )
    return rudder, socket


def propulsion_components():
    """Return separate glue-on running gear in assembled coordinates."""
    components = []
    socket_cutters = []
    beam = P.maximum_hull_beam
    sf = P.scale_factor
    lateral = (-0.250 * beam, -0.125 * beam, 0.125 * beam, 0.250 * beam)
    for index, y in enumerate(lateral, 1):
        inner = abs(y) < 0.20 * beam
        start = v(
            P.overall_length * (0.842 if inner else 0.826),
            y * 0.83,
            P.molded_depth * (0.190 if inner else 0.170),
        )
        end = v(
            P.overall_length * (0.943 if inner else 0.925),
            y,
            -max(1.8, (2.2 if inner else 2.6) * sf),
        )
        prop_center = end.add(v(max(1.7, 2.3 * sf), 0, -max(0.15, 0.25 * sf)))
        shaft_tip = prop_center.add(v(max(0.12, 0.20 * sf), 0, 0))
        shaft = prism_between(start, shaft_tip, P.shaft_radius)
        components.append((f"Shaft_{index}", shaft, "silk_silver", "shaft"))

        shaft_axis = shaft_tip.sub(start)
        shaft_unit = shaft_axis.multiply(1.0 / shaft_axis.Length)
        socket_cutters.append(
            prism_between(start, shaft_tip, P.shaft_radius + P.joint_clearance)
        )

        prop = make_propeller(
            prop_center,
            P.propeller_radius,
            P.shaft_radius + P.joint_clearance,
        )
        components.append((f"Propeller_{index}", prop, "gold", "propeller"))

        # Two low-profile A-bracket legs per shaft.
        bracket_x = 0.66 * start.x + 0.34 * end.x
        shaft_z = 0.66 * start.z + 0.34 * end.z
        shaft_y = 0.66 * start.y + 0.34 * end.y
        for leg in (-1, 1):
            hull_point = v(bracket_x - max(2.0, 2.8 * sf), shaft_y + leg * max(1.8, 2.5 * sf), shaft_z + max(3.0, 4.5 * sf))
            shaft_point = v(bracket_x, shaft_y, shaft_z)
            strut_radius = max(0.48, 0.62 * sf)
            strut = prism_between(shaft_point, hull_point, strut_radius)
            components.append((f"Shaft_{index}_Strut_{'P' if leg < 0 else 'S'}", strut, "ash_gray", "strut"))

            strut_axis = hull_point.sub(shaft_point)
            strut_unit = strut_axis.multiply(1.0 / strut_axis.Length)
            socket_cutters.append(
                prism_between(
                    shaft_point,
                    hull_point.add(strut_unit.multiply(max(3.0, 4.0 * sf))),
                    strut_radius + P.joint_clearance,
                )
            )

    rudder_y = 0.155 * beam
    for name, y_center in (("Rudder_Port", -rudder_y), ("Rudder_Starboard", rudder_y)):
        rudder, socket = make_rudder(y_center)
        components.append((name, rudder, "ash_gray", "rudder"))
        socket_cutters.append(socket)
    return components, socket_cutters


def add_accessory_sockets(hull, socket_cutters):
    tools = Part.makeCompound(socket_cutters)
    detailed = hull.cut(tools).removeSplitter()
    if not detailed.isValid() or not detailed.isClosed():
        raise RuntimeError("Running-gear sockets produced invalid hull geometry")
    return detailed, tools


def placed_on_bed(shape, rotation: App.Rotation, target_x: float, target_y: float):
    placed = shape.copy()
    placed.Placement = App.Placement(v(0, 0, 0), rotation)
    bounds = precise_bounds(placed)
    placed.Placement.Base = placed.Placement.Base.add(
        v(target_x - bounds[0], target_y - bounds[1], -bounds[2])
    )
    return placed


def precise_bounds(shape):
    """Return tight tessellated bounds.

    OpenCascade's analytic B-spline bounding boxes are conservative and can
    overstate a Boolean-trimmed module by more than 100 mm.  Plate packing and
    exported dimension QA must use the actual tessellated surface bounds.
    """
    points, _faces = shape.tessellate(P.tessellation_deflection)
    if not points:
        raise RuntimeError("Cannot measure a shape with no tessellated vertices")
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    zs = [point.z for point in points]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def print_layout(segments, propulsion):
    """Arrange the complete default-scale kit inside a 240 x 240 mm plate."""
    layout = []
    lane_y = 0.0
    for index, segment in enumerate(segments):
        oriented = placed_on_bed(segment, App.Rotation(v(1, 0, 0), 180), 0.0, lane_y)
        layout.append((f"Hull_Module_{index + 1}", oriented, "ash_gray", "hull_segment"))
        lane_y = precise_bounds(oriented)[4] + 1.5

    # Accessories occupy a dedicated strip on the same X1/P1/A1 plate.  A1
    # Mini users receive each object as an individual, already oriented STL.
    cursor_y = 0.0
    column_x = max(precise_bounds(item[1])[3] for item in layout) + 4.0
    max_column_width = 0.0
    for name, shape, material, kind in propulsion:
        if kind == "propeller":
            rotation = App.Rotation(v(0, 1, 0), 90)
        elif kind == "rudder":
            rotation = App.Rotation(v(1, 0, 0), 90)
        else:
            # Long hexagonal shafts/struts lie on a flat facet and print
            # without support; rotate their assembled elevation into XY.
            rotation = App.Rotation(v(1, 0, 0), 90)
        oriented = placed_on_bed(shape, rotation, column_x, cursor_y)
        oriented_bounds = precise_bounds(oriented)
        if oriented_bounds[4] > 232.0:
            column_x += max_column_width + 2.0
            cursor_y = 0.0
            max_column_width = 0.0
            oriented = placed_on_bed(shape, rotation, column_x, cursor_y)
            oriented_bounds = precise_bounds(oriented)
        layout.append((name, oriented, material, kind))
        cursor_y = oriented_bounds[4] + 1.5
        max_column_width = max(max_column_width, oriented_bounds[3] - oriented_bounds[0])

    compound = Part.makeCompound([item[1] for item in layout])
    all_bounds = [precise_bounds(item[1]) for item in layout]
    layout_bounds = (
        min(b[0] for b in all_bounds),
        min(b[1] for b in all_bounds),
        min(b[2] for b in all_bounds),
        max(b[3] for b in all_bounds),
        max(b[4] for b in all_bounds),
        max(b[5] for b in all_bounds),
    )
    layout_size = (
        layout_bounds[3] - layout_bounds[0],
        layout_bounds[4] - layout_bounds[1],
        layout_bounds[5] - layout_bounds[2],
    )
    if any(size > 240.0 for size in layout_size):
        raise RuntimeError(
            "Print layout exceeds 240 mm preferred envelope: "
            f"{layout_size[0]:.2f} x {layout_size[1]:.2f} x {layout_size[2]:.2f}"
        )
    return layout, compound, layout_bounds


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
        for tri in triangles:
            a, b, c = (vertices[i] for i in tri)
            facets.append((triangle_normal(a, b, c), a, b, c))
    header = f"CVN-69 Museum Edition v{VERSION} scale 1:{P.scale_denominator}".encode("ascii")[:80].ljust(80, b" ")
    with path.open("wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(facets)))
        for normal, a, b, c in facets:
            handle.write(struct.pack("<12fH", *(normal + a + b + c), 0))
    return len(facets)


def write_3mf(path: Path, named_shapes):
    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    ET.register_namespace("", ns)
    model = ET.Element(f"{{{ns}}}model", {"unit": "millimeter", "xml:lang": "en-US"})
    metadata = ET.SubElement(model, f"{{{ns}}}metadata", {"name": "Title"})
    metadata.text = "USS Dwight D. Eisenhower (CVN-69) — Hull — Museum Edition"
    resources = ET.SubElement(model, f"{{{ns}}}resources")
    base_id = "1"
    bases = ET.SubElement(resources, f"{{{ns}}}basematerials", {"id": base_id})
    material_index = {}
    for index, (key, (name, color)) in enumerate(MATERIALS.items()):
        material_index[key] = index
        ET.SubElement(bases, f"{{{ns}}}base", {"name": name, "displaycolor": color})

    obj = ET.SubElement(resources, f"{{{ns}}}object", {"id": "2", "type": "model", "name": "CVN-69 Hull Print Layout"})
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
                    "pid": base_id,
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
            rgb = tuple(int(color[i : i + 2], 16) / 255.0 for i in (1, 3, 5))
            mtl.write(f"newmtl {key}\n# {name}\nKd {rgb[0]:.6f} {rgb[1]:.6f} {rgb[2]:.6f}\n\n")
    with path.open("w", encoding="utf-8") as obj:
        obj.write(f"mtllib {mtl_path.name}\n")
        vertex_offset = 1
        for name, shape, material, _kind in named_shapes:
            vertices, triangles = triangulate(shape)
            obj.write(f"o {name}\nusemtl {material}\n")
            for x, y, z in vertices:
                obj.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
            for a, b, c in triangles:
                obj.write(f"f {a + vertex_offset} {b + vertex_offset} {c + vertex_offset}\n")
            vertex_offset += len(vertices)


def add_spreadsheet(doc):
    sheet = doc.addObject("Spreadsheet::Sheet", "Parameters")
    rows = [
        ("Parameter", "Value", "Unit / note"),
        ("Scale denominator", P.scale_denominator, "1:n"),
        ("Overall length", P.overall_length, "mm"),
        ("Maximum hull beam", P.maximum_hull_beam, "mm"),
        ("Molded depth", P.molded_depth, "mm"),
        ("Waterline height", P.waterline_height, "mm above keel datum"),
        ("Design draft", P.design_draft, "mm"),
        ("Module count", P.module_count, "A1 Mini-compatible"),
        ("Maximum module length", P.module_max_length, "mm"),
        ("Joint clearance", P.joint_clearance, "mm per side"),
        ("Tessellation deflection", P.tessellation_deflection, "mm"),
    ]
    for row_index, row in enumerate(rows, 1):
        for col_index, value in enumerate(row, 1):
            column = chr(64 + col_index)
            sheet.set(f"{column}{row_index}", str(value))
    sheet.setStyle("A1:C1", "bold", "add")
    sheet.setColumnWidth("A", 190)
    sheet.setColumnWidth("B", 110)
    sheet.setColumnWidth("C", 180)
    return sheet


def create_document(hull, sections, groove_cutters, anchor_cutters, accessory_socket_tools, segments, propulsion, seams):
    doc = App.newDocument("CVN69_Hull_Museum_Edition")
    info = doc.addObject("App::FeaturePython", "MilestoneInformation")
    info.addProperty("App::PropertyString", "ProjectName").ProjectName = "USS Dwight D. Eisenhower (CVN-69) Museum Edition"
    info.addProperty("App::PropertyString", "Milestone").Milestone = "v0.1 Hull"
    info.addProperty("App::PropertyString", "SemanticVersion").SemanticVersion = VERSION
    info.addProperty("App::PropertyInteger", "ScaleDenominator").ScaleDenominator = P.scale_denominator
    info.addProperty("App::PropertyString", "Generator").Generator = str(SCRIPT.relative_to(PROJECT))
    info.addProperty("App::PropertyString", "GeometryStatus").GeometryStatus = "Print-oriented public-data reconstruction; not shipyard lines"
    add_spreadsheet(doc)

    references = doc.addObject("App::DocumentObjectGroup", "ConstructionReferences")
    for index, wire in enumerate(sections):
        obj = doc.addObject("Part::Feature", f"Station_{index:02d}")
        obj.Label = f"Loft Station {P.stations[index].x_ratio:.3f} L"
        obj.Shape = wire
        references.addObject(obj)
        obj.Visibility = False
    waterline = doc.addObject("Part::Feature", "WaterlineGrooveTool")
    waterline.Shape = groove_cutters
    references.addObject(waterline)
    waterline.Visibility = False
    anchors = doc.addObject("Part::Feature", "AnchorRecessTools")
    anchors.Shape = anchor_cutters
    references.addObject(anchors)
    anchors.Visibility = False
    sockets = doc.addObject("Part::Feature", "AccessorySocketTools")
    sockets.Shape = accessory_socket_tools
    references.addObject(sockets)
    sockets.Visibility = False

    assembly = doc.addObject("App::DocumentObjectGroup", "HullAssembly")
    segment_objects = []
    for index, segment in enumerate(segments):
        obj = doc.addObject("Part::Feature", f"Hull_Module_{index + 1}")
        if index == 0:
            obj.Label = "Hull Module 1 — Bow"
        elif index == len(segments) - 1:
            obj.Label = f"Hull Module {index + 1} — Stern"
        else:
            obj.Label = f"Hull Module {index + 1} — Midship"
        obj.Shape = segment
        obj.addProperty("App::PropertyString", "Material").Material = "PLA Matte Ash Gray"
        obj.addProperty("App::PropertyString", "PrintOrientation").PrintOrientation = "Flight-deck interface down"
        try:
            obj.ViewObject.ShapeColor = (0.59, 0.60, 0.56)
        except Exception:
            pass
        assembly.addObject(obj)
        segment_objects.append(obj)

    propulsion_objects = []
    for name, shape, material, kind in propulsion:
        obj = doc.addObject("Part::Feature", name)
        obj.Label = name.replace("_", " ")
        obj.Shape = shape
        obj.addProperty("App::PropertyString", "Material").Material = MATERIALS[material][0]
        obj.addProperty("App::PropertyString", "PartType").PartType = kind
        try:
            if material == "gold":
                obj.ViewObject.ShapeColor = (0.77, 0.60, 0.20)
            elif material == "silk_silver":
                obj.ViewObject.ShapeColor = (0.68, 0.71, 0.73)
            else:
                obj.ViewObject.ShapeColor = (0.59, 0.60, 0.56)
        except Exception:
            pass
        assembly.addObject(obj)
        propulsion_objects.append(obj)

    master = doc.addObject("Part::Feature", "UnsplitHullEnvelope")
    master.Label = "Unsplit Detailed Hull Envelope (reference)"
    master.Shape = hull
    references.addObject(master)
    master.Visibility = False

    seams_feature = doc.addObject("App::FeaturePython", "SplitDefinition")
    seams_feature.addProperty("App::PropertyStringList", "SeamPositions")
    seams_feature.SeamPositions = [f"{seam:.3f} mm" for seam in seams]
    seams_feature.addProperty("App::PropertyString", "JointType").JointType = "Asymmetric paired internal glue keys"
    seams_feature.addProperty("App::PropertyLength", "Clearance").Clearance = P.joint_clearance
    doc.recompute()
    return doc, segment_objects, propulsion_objects


def shape_record(name, shape):
    bounds = precise_bounds(shape)
    return {
        "name": name,
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "volume_mm3": round(float(shape.Volume), 3),
        "bounds_mm": {
            "x": [round(bounds[0], 3), round(bounds[3], 3)],
            "y": [round(bounds[1], 3), round(bounds[4], 3)],
            "z": [round(bounds[2], 3), round(bounds[5], 3)],
        },
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    print(f"Building CVN-69 Hull Museum Edition v{VERSION} at 1:{P.scale_denominator}")
    hull, sections = make_outer_hull()
    hull, groove_cutters = add_waterline_groove(hull)
    hull, anchor_cutters = add_anchor_recesses(hull)
    propulsion, accessory_socket_tools = propulsion_components()
    hull, accessory_socket_tools = add_accessory_sockets(hull, accessory_socket_tools)
    segments, seams = split_hull(hull)
    layout, layout_compound, layout_bounds = print_layout(segments, propulsion)

    doc, segment_objects, propulsion_objects = create_document(
        hull,
        sections,
        groove_cutters,
        anchor_cutters,
        accessory_socket_tools,
        segments,
        propulsion,
        seams,
    )
    fcstd_path = DIRS["freecad"] / "Hull.FCStd"
    doc.recompute()
    doc.saveAs(str(fcstd_path))

    step_path = DIRS["step"] / "Hull.step"
    Part.export(segment_objects + propulsion_objects, str(step_path))

    stl_path = DIRS["stl"] / "Hull.stl"
    facet_count = write_binary_stl(stl_path, layout)
    write_3mf(DIRS["3mf"] / "Hull.3mf", layout)
    assembly_shapes = [
        (f"Hull_Module_{index + 1}", shape, "ash_gray", "hull_segment")
        for index, shape in enumerate(segments)
    ] + propulsion
    # OBJ/STEP are assembled-coordinate interchange formats; STL/3MF are
    # deliberately plate-oriented manufacturing formats.
    write_obj(DIRS["obj"] / "Hull.obj", assembly_shapes)

    # Every A1 Mini part is independently oriented and no larger than 180 mm.
    individual_files = []
    for name, shape, material, kind in layout:
        part_path = DIRS["stl"] / f"{name}.stl"
        write_binary_stl(part_path, [(name, shape, material, kind)])
        individual_files.append(part_path)

    records = [shape_record(f"Hull_Module_{i + 1}", shape) for i, shape in enumerate(segments)]
    records.extend(shape_record(name, shape) for name, shape, _material, _kind in propulsion)
    layout_size = [
        layout_bounds[3] - layout_bounds[0],
        layout_bounds[4] - layout_bounds[1],
        layout_bounds[5] - layout_bounds[2],
    ]
    output_paths = [
        fcstd_path,
        step_path,
        stl_path,
        DIRS["3mf"] / "Hull.3mf",
        DIRS["obj"] / "Hull.obj",
        DIRS["obj"] / "Hull.mtl",
    ] + individual_files
    manifest = {
        "project": "USS Dwight D. Eisenhower (CVN-69) Museum Edition",
        "milestone": "v0.1 Hull",
        "version": VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "freecad_version": ".".join(App.Version()[:3]),
        "scale": f"1:{P.scale_denominator}",
        "parameters_mm": {
            "overall_length": P.overall_length,
            "maximum_hull_beam": P.maximum_hull_beam,
            "molded_depth": P.molded_depth,
            "waterline_height": P.waterline_height,
            "joint_clearance_per_side": P.joint_clearance,
            "module_max_length": P.module_max_length,
            "tessellation_deflection": P.tessellation_deflection,
        },
        "print_layout_bounds_mm": [
            round(layout_size[0], 3),
            round(layout_size[1], 3),
            round(layout_size[2], 3),
        ],
        "stl_facet_count": facet_count,
        "shapes": records,
        "outputs": {str(path.relative_to(PROJECT)): {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in output_paths},
    }
    manifest_path = DIRS["qa"] / "build_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    App.closeDocument(doc.Name)
    print(json.dumps({"status": "ok", "manifest": str(manifest_path), "layout_mm": manifest["print_layout_bounds_mm"], "facets": facet_count}, indent=2))


if __name__ == "__main__":
    main()
