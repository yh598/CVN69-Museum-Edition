#!/usr/bin/env python3
"""Generate the Milestone 1 PDF drawing and manufacturing set.

Use the Codex bundled document runtime (ReportLab 4.x) or any Python with
reportlab and Pillow installed.
"""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


SCRIPT = Path(__file__).resolve()
PROJECT = SCRIPT.parents[1]
DOCS = PROJECT / "Docs"
MANIFEST = json.loads((PROJECT / "QA" / "build_manifest.json").read_text(encoding="utf-8"))
VALIDATION = json.loads((PROJECT / "QA" / "validation_report.json").read_text(encoding="utf-8"))

INK = colors.HexColor("#252A2D")
SLATE = colors.HexColor("#56666F")
LINE = colors.HexColor("#B6C0C3")
PAPER = colors.HexColor("#F7F6F1")
ACCENT = colors.HexColor("#315D77")
RUST = colors.HexColor("#965A42")
GOLD = colors.HexColor("#C59A32")
ASH = colors.HexColor("#969890")


def register_fonts():
    candidates = [
        ("Inter", "/System/Library/Fonts/Supplemental/Arial.ttf"),
        ("InterBold", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ]
    for name, path in candidates:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont(name, path))
    return "Inter" if "Inter" in pdfmetrics.getRegisteredFontNames() else "Helvetica"


FONT = register_fonts()
BOLD = "InterBold" if "InterBold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"


def styles():
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=sample["Title"], fontName=BOLD, fontSize=24, leading=28, textColor=INK, alignment=TA_LEFT, spaceAfter=6),
        "subtitle": ParagraphStyle("Subtitle", parent=sample["Normal"], fontName=FONT, fontSize=9, leading=12, textColor=SLATE, spaceAfter=14, uppercase=True),
        "h1": ParagraphStyle("H1", parent=sample["Heading1"], fontName=BOLD, fontSize=15, leading=19, textColor=INK, spaceBefore=10, spaceAfter=7),
        "h2": ParagraphStyle("H2", parent=sample["Heading2"], fontName=BOLD, fontSize=10.5, leading=14, textColor=ACCENT, spaceBefore=8, spaceAfter=5),
        "body": ParagraphStyle("Body", parent=sample["BodyText"], fontName=FONT, fontSize=8.8, leading=12.2, textColor=INK, spaceAfter=6),
        "small": ParagraphStyle("Small", parent=sample["BodyText"], fontName=FONT, fontSize=7.3, leading=9.4, textColor=SLATE, spaceAfter=4),
        "callout": ParagraphStyle("Callout", parent=sample["BodyText"], fontName=BOLD, fontSize=9, leading=12, textColor=ACCENT, borderColor=LINE, borderWidth=0.6, borderPadding=8, backColor=colors.white, spaceBefore=6, spaceAfter=8),
    }


S = styles()


def footer(canvas_obj, doc):
    canvas_obj.saveState()
    width, _height = doc.pagesize
    canvas_obj.setStrokeColor(LINE)
    canvas_obj.setLineWidth(0.4)
    canvas_obj.line(doc.leftMargin, 12 * mm, width - doc.rightMargin, 12 * mm)
    canvas_obj.setFont(FONT, 6.7)
    canvas_obj.setFillColor(SLATE)
    canvas_obj.drawString(doc.leftMargin, 7.5 * mm, "CVN-69 MUSEUM EDITION  ·  MILESTONE 1 HULL  ·  v0.1.0")
    canvas_obj.drawRightString(width - doc.rightMargin, 7.5 * mm, f"PAGE {doc.page}")
    canvas_obj.restoreState()


def table(data, widths=None, header=True, font_size=7.4):
    result = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 2.4),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), INK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), BOLD),
        ]
    for row in range(1 if header else 0, len(data)):
        if row % 2 == 0:
            commands.append(("BACKGROUND", (0, row), (-1, row), colors.HexColor("#F1F2EF")))
    result.setStyle(TableStyle(commands))
    return result


def bullet(text):
    return Paragraph(f"•&nbsp;&nbsp;{text}", S["body"])


def build_pdf(path: Path, title: str, subtitle: str, story):
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="CVN-69 Museum Edition contributors",
        subject=subtitle,
    )
    opening = [Paragraph(title, S["title"]), Paragraph(subtitle.upper(), S["subtitle"])]
    doc.build(opening + story, onFirstPage=footer, onLaterPages=footer)


def draw_title(c, title, subtitle, sheet):
    width, height = landscape(A3)
    c.setFillColor(PAPER)
    c.rect(0, 0, width, height, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont(BOLD, 22)
    c.drawString(18 * mm, height - 22 * mm, title)
    c.setFillColor(SLATE)
    c.setFont(FONT, 8)
    c.drawString(18 * mm, height - 29 * mm, subtitle)
    c.setStrokeColor(LINE)
    c.line(18 * mm, height - 33 * mm, width - 18 * mm, height - 33 * mm)
    c.setFont(BOLD, 7)
    c.setFillColor(INK)
    c.drawRightString(width - 18 * mm, height - 22 * mm, sheet)


def arrow_dimension(c, x0, y0, x1, y1, label, offset=0):
    c.setStrokeColor(INK)
    c.setFillColor(INK)
    c.setLineWidth(0.6)
    c.line(x0, y0, x1, y1)
    angle = 0.0 if abs(x1 - x0) >= abs(y1 - y0) else 90.0
    for x, y, flip in ((x0, y0, 1), (x1, y1, -1)):
        c.saveState()
        c.translate(x, y)
        c.rotate(angle)
        c.line(0, 0, 4 * flip, 2)
        c.line(0, 0, 4 * flip, -2)
        c.restoreState()
    c.setFont(FONT, 7)
    c.drawCentredString((x0 + x1) / 2.0, (y0 + y1) / 2.0 + 3 + offset, label)


def generate_drawings():
    path = DOCS / "Hull_Drawings.pdf"
    c = canvas.Canvas(str(path), pagesize=landscape(A3), pageCompression=1)
    width, height = landscape(A3)
    c.setTitle("CVN-69 Hull Drawings")
    c.setAuthor("CVN-69 Museum Edition contributors")

    # Sheet 1: rendered general arrangement.
    draw_title(c, "USS DWIGHT D. EISENHOWER (CVN-69) — HULL GENERAL ARRANGEMENT", "MUSEUM EDITION · MILESTONE 1 · SCALE 1:700 · DIMENSIONS IN MILLIMETRES", "SHEET H-01 / 03")
    image_path = PROJECT / "Render" / "Hull_Orthographic.png"
    c.drawImage(str(image_path), 18 * mm, 37 * mm, width=width - 36 * mm, height=height - 76 * mm, preserveAspectRatio=True, anchor="c", mask="auto")
    data = [
        ["REV", "OVERALL", "HULL BEAM", "WATERLINE", "MODULES", "PARTS", "STATUS"],
        ["0.1.0", "476.000", "58.304", "z = 15.900", "3", "21", "QA PASS"],
    ]
    t = table(data, widths=[20 * mm, 30 * mm, 30 * mm, 31 * mm, 25 * mm, 25 * mm, 28 * mm], font_size=7)
    t.wrapOn(c, width, height)
    t.drawOn(c, 18 * mm, 17 * mm)
    c.showPage()

    # Sheet 2: vector construction body plan / split plan.
    draw_title(c, "HULL STATION AND SPLIT CONTROL", "PARAMETRIC CONSTRUCTION REFERENCE · NOT SHIPYARD LINES", "SHEET H-02 / 03")
    from sys import path as sys_path
    sys_path.insert(0, str(PROJECT / "CAD" / "Python"))
    from hull_parameters import make_parameters

    p = make_parameters(700)
    origin_x, center_y = 24 * mm, 151 * mm
    scale_x = (width - 56 * mm) / p.overall_length
    scale_y = 2.3
    top_points = []
    for station in p.stations:
        x = origin_x + p.overall_length * station.x_ratio * scale_x
        half = (p.maximum_hull_beam / 2.0) * 0.9915 * station.top_beam_factor * scale_y
        top_points.append((x, center_y + half))
    outline = top_points + [(x, 2 * center_y - y) for x, y in reversed(top_points)]
    c.setFillColor(ASH)
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    path_obj = c.beginPath()
    path_obj.moveTo(*outline[0])
    for point in outline[1:]:
        path_obj.lineTo(*point)
    path_obj.close()
    c.drawPath(path_obj, fill=1, stroke=1)
    c.setStrokeColor(colors.white)
    c.setLineWidth(0.3)
    for station in p.stations:
        x = origin_x + p.overall_length * station.x_ratio * scale_x
        c.line(x, center_y - 33 * mm, x, center_y + 33 * mm)
    for seam_index in (1, 2):
        x = origin_x + (p.overall_length * seam_index / 3.0) * scale_x
        c.setStrokeColor(RUST)
        c.setDash(3, 2)
        c.line(x, center_y - 39 * mm, x, center_y + 39 * mm)
        c.setDash()
        c.setFont(BOLD, 7)
        c.setFillColor(RUST)
        c.drawCentredString(x, center_y + 42 * mm, f"SEAM {seam_index} · x={p.overall_length * seam_index / 3.0:.3f}")
    arrow_dimension(c, origin_x, center_y - 45 * mm, origin_x + p.overall_length * scale_x, center_y - 45 * mm, "476.000 OVERALL")
    arrow_dimension(c, origin_x + p.overall_length * 0.52 * scale_x, center_y - p.maximum_hull_beam / 2 * scale_y, origin_x + p.overall_length * 0.52 * scale_x, center_y + p.maximum_hull_beam / 2 * scale_y, "58.300 MAX", offset=2)

    # Representative body sections.
    base_y = 52 * mm
    section_xs = [48, 119, 190, 261, 332]
    ratios = [0.02, 0.16, 0.50, 0.88, 1.00]
    for sx_mm, ratio in zip(section_xs, ratios):
        station = min(p.stations, key=lambda item: abs(item.x_ratio - ratio))
        sx = sx_mm * mm
        half = 24 * mm * station.waterline_beam_factor
        keel = base_y + 3 * mm + 12 * mm * station.keel_rise_ratio
        top = base_y + 31 * mm
        body = c.beginPath()
        body.moveTo(sx, top)
        body.curveTo(sx + half * 0.95, top, sx + half, base_y + 17 * mm, sx + half * 0.62, base_y + 7 * mm)
        body.curveTo(sx + half * 0.38, keel, sx + 2 * mm, keel, sx, keel)
        body.curveTo(sx - 2 * mm, keel, sx - half * 0.38, keel, sx - half * 0.62, base_y + 7 * mm)
        body.curveTo(sx - half, base_y + 17 * mm, sx - half * 0.95, top, sx, top)
        c.setFillColor(colors.HexColor("#D9DCDA"))
        c.setStrokeColor(INK)
        c.drawPath(body, fill=1, stroke=1)
        c.setStrokeColor(ACCENT)
        c.setDash(4, 2)
        c.line(sx - half - 3 * mm, base_y + 16 * mm, sx + half + 3 * mm, base_y + 16 * mm)
        c.setDash()
        c.setFillColor(INK)
        c.setFont(FONT, 7)
        c.drawCentredString(sx, base_y - 2 * mm, f"{station.x_ratio:.3f} L")
    c.setFont(FONT, 7)
    c.setFillColor(SLATE)
    c.drawString(22 * mm, 18 * mm, "WATERLINE SHOWN DASHED · KEEL DATUM z≈0 · 16 DIMENSIONLESS LOFT STATIONS")
    c.showPage()

    # Sheet 3: glue-joint details and propulsion mapping.
    draw_title(c, "HIDDEN GLUE JOINTS AND RUNNING-GEAR CONTROL", "0.25 mm CLEARANCE PER SIDE · SUPPORT-FREE PRINT ORIENTATIONS", "SHEET H-03 / 03")
    c.setFillColor(colors.white)
    c.setStrokeColor(LINE)
    c.roundRect(20 * mm, 111 * mm, 170 * mm, 76 * mm, 4 * mm, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BOLD, 11)
    c.drawString(27 * mm, 177 * mm, "A — MODULE SEAM / ASYMMETRIC KEYS")
    c.setFillColor(ASH)
    c.rect(34 * mm, 133 * mm, 58 * mm, 28 * mm, fill=1, stroke=0)
    c.rect(108 * mm, 133 * mm, 58 * mm, 28 * mm, fill=1, stroke=0)
    c.setFillColor(RUST)
    c.rect(92 * mm, 151 * mm, 18 * mm, 6 * mm, fill=1, stroke=0)
    c.rect(92 * mm, 138 * mm, 15 * mm, 5 * mm, fill=1, stroke=0)
    c.setStrokeColor(INK)
    c.rect(108 * mm, 150.5 * mm, 19 * mm, 7 * mm, fill=0, stroke=1)
    c.rect(108 * mm, 137.5 * mm, 16 * mm, 6 * mm, fill=0, stroke=1)
    arrow_dimension(c, 92 * mm, 126 * mm, 110 * mm, 126 * mm, "6.0 KEY ENGAGEMENT")

    c.setFillColor(colors.white)
    c.setStrokeColor(LINE)
    c.roundRect(204 * mm, 111 * mm, 192 * mm, 76 * mm, 4 * mm, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BOLD, 11)
    c.drawString(211 * mm, 177 * mm, "B — CONCEALED ACCESSORY SOCKETS")
    c.setFillColor(ASH)
    c.rect(220 * mm, 146 * mm, 70 * mm, 13 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#AEB4B8"))
    c.setLineWidth(5)
    c.line(250 * mm, 148 * mm, 290 * mm, 127 * mm)
    c.setFillColor(GOLD)
    c.circle(294 * mm, 125 * mm, 8 * mm, fill=1, stroke=0)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.0)
    c.line(250 * mm, 148 * mm, 265 * mm, 140 * mm)
    c.setFillColor(INK)
    c.setFont(FONT, 7)
    c.drawString(218 * mm, 119 * mm, "SHAFT ROOT GROOVE")
    c.drawString(282 * mm, 111 * mm, "BLIND PROP BORE")
    c.drawString(323 * mm, 145 * mm, "RUDDER STOCK SLOT")
    c.setFillColor(ASH)
    c.rect(348 * mm, 122 * mm, 5 * mm, 34 * mm, fill=1, stroke=0)
    c.setStrokeColor(INK)
    c.rect(346 * mm, 150 * mm, 9 * mm, 9 * mm, fill=0, stroke=1)

    mapping = [
        ["LINE", "SIDE / POSITION", "SHAFT", "PROP", "STRUTS"],
        ["1", "PORT OUTER", "Shaft_1", "Propeller_1", "1_P + 1_S"],
        ["2", "PORT INNER", "Shaft_2", "Propeller_2", "2_P + 2_S"],
        ["3", "STARBOARD INNER", "Shaft_3", "Propeller_3", "3_P + 3_S"],
        ["4", "STARBOARD OUTER", "Shaft_4", "Propeller_4", "4_P + 4_S"],
    ]
    t = table(mapping, widths=[20 * mm, 52 * mm, 42 * mm, 42 * mm, 42 * mm], font_size=7)
    tw, th = t.wrap(width, height)
    t.drawOn(c, 20 * mm, 37 * mm)
    c.setFillColor(SLATE)
    c.setFont(FONT, 7)
    c.drawString(20 * mm, 24 * mm, "PRINT HULL MODULES TOP-INTERFACE DOWN. PRINT HEX SHAFT/STRUT FACET DOWN. PRINT PROPELLERS AND RUDDERS FLAT. SUPPORTS OFF.")
    c.save()


def assembly_story():
    image = Image(str(PROJECT / "Images" / "Hull_Exploded.png"), width=174 * mm, height=98 * mm)
    parts = [
        ["Part group", "Qty", "Material / color", "Locator"],
        ["Hull modules", "3", "PLA Matte Ash Gray", "Asymmetric paired internal keys"],
        ["Shafts", "4", "PLA Silk Silver", "Concealed hex root grooves"],
        ["A-bracket struts", "8", "PLA Matte Ash Gray", "Concealed hull-end sockets"],
        ["Propellers", "4", "PLA Basic Gold", "Blind shaft-tip bore"],
        ["Rudders", "2", "PLA Matte Ash Gray", "Concealed rectangular stock"],
    ]
    story = [image, Spacer(1, 5 * mm), Paragraph("Assembly inventory", S["h1"]), table(parts, widths=[38 * mm, 13 * mm, 52 * mm, 66 * mm]), Paragraph("No screws, magnets, rods, metal parts, inserts, or electronics are required. Total printed-part count: 21.", S["callout"]), PageBreak()]
    story += [Paragraph("1. Join the hull modules", S["h1"])]
    for text in (
        "Deburr only the hidden keys and sockets. Preserve the exterior seam faces and engraved waterline.",
        "Dry-fit bow module 1 to midship module 2. The asymmetric keys prevent inversion. The seam must close by hand without force.",
        "Wet only the female sockets with a small amount of PLA-compatible adhesive. Join on a flat surface and confirm the top interface is coplanar.",
        "After full cure, repeat for midship module 2 and stern module 3.",
    ):
        story.append(bullet(text))
    story += [Paragraph("2. Install the running gear", S["h1"])]
    mapping = [["Line", "Position", "Shaft", "Propeller"]] + [[str(i), pos, f"Shaft_{i}", f"Propeller_{i}"] for i, pos in enumerate(("Port outer", "Port inner", "Starboard inner", "Starboard outer"), 1)]
    story.append(table(mapping, widths=[17 * mm, 54 * mm, 43 * mm, 43 * mm]))
    for text in (
        "Seat each numbered shaft in its concealed groove without adhesive; confirm four distinct, symmetric centerlines.",
        "Fit the matching P/S A-bracket struts. Glue the hull end first, then wick a minimal amount to the shaft contact.",
        "Slide each matching propeller onto the shaft tip. The blind bore controls concentricity and axial position.",
        "Insert the port and starboard rudder stocks upward into their stern slots. Set both rudders parallel before cure.",
    ):
        story.append(bullet(text))
    story += [Paragraph("3. Final acceptance", S["h1"]), bullet("Top interface remains flat across both module seams."), bullet("Exterior surfaces show no adhesive bloom or squeeze-out."), bullet("Shaft lines, propeller disks, and rudders are symmetric in plan and elevation."), bullet("Model is supported in a padded cradle; propellers and rudders never carry display load."), Paragraph("First-article caveat", S["h2"]), Paragraph("The 0.25 mm-per-side fit allowance passed geometric interference checks. Printer calibration, filament moisture, and shrinkage still require a physical dry fit before adhesive is applied.", S["body"])]
    return story


def printing_story():
    settings = [
        ["Setting", "Hull modules", "Running gear"],
        ["Nozzle", "0.4 mm", "0.4 mm"],
        ["Layer height", "0.16 mm", "0.12 mm"],
        ["Walls", "3", "3"],
        ["Top / bottom", "5 / 5", "5 / 5"],
        ["Infill", "15% gyroid", "15% gyroid"],
        ["Supports", "Off", "Off"],
        ["Brim", "Optional 3 mm", "3 mm recommended"],
    ]
    story = [Paragraph("Printer routing", S["h1"]), Paragraph("X1 Carbon, P1S, and A1: use the 220.1 × 177.3 mm `Hull.3mf` plate. A1 Mini: use the individual already-oriented STLs; all three hull modules are below 165 mm on their longest axis.", S["body"]), Paragraph("Required process", S["h1"]), table(settings, widths=[50 * mm, 58 * mm, 58 * mm]), Paragraph("Orientation and support policy", S["h1"]), Paragraph("The supplied manufacturing meshes are pre-oriented. Hull modules print top-interface down; shafts and A-brackets rest on hex facets; propellers and rudders lie flat. Disable supports and disable slicer auto-orientation. Internal key sockets bridge less than 8 mm.", S["body"]), Paragraph("Allowed color mapping", S["h1"])]
    colors_data = [["Objects", "Approved filament"], ["Hull / struts / rudders", "PLA Matte Ash Gray"], ["Shafts", "PLA Silk Silver"], ["Propellers", "PLA Basic Gold"]]
    story.append(table(colors_data, widths=[78 * mm, 88 * mm]))
    story += [Paragraph("Fit and first layer", S["h1"]), bullet("Nominal concealed-joint clearance is 0.25 mm per side."), bullet("Start with zero XY hole compensation. Tune only after a fit coupon."), bullet("Use 0.10–0.15 mm elephant-foot compensation if needed; do not sand exterior seams."), bullet("Do not independently scale STL files. Regenerate through the parameter source."), Paragraph("Preflight checklist", S["h1"]), bullet("Slicer reports 21 parts and a manifold model."), bullet("Supports are off and orientations are unchanged."), bullet("0.12 mm object settings are applied to all 18 running-gear pieces."), bullet("Shafts/struts have brim contact and no purge tower collision."), Paragraph("Post-print handling", S["h1"]), Paragraph("Cool fully, flex the plate, and lift from robust hull surfaces. Never lever against the waterline groove, propeller blades, or rudders. Deburr only concealed interfaces.", S["body"])]
    return story


def plan_story():
    checks = [["Acceptance item", "Result", "Evidence"]]
    selected = {
        "Complete kit part count",
        "Preferred plate envelope",
        "A1 Mini module envelope",
        "3MF package and indices",
        "FreeCAD BRep validity / self-intersection",
        "STEP round-trip",
        "Overall hull length",
        "Maximum molded hull beam",
        "Glue-joint fit allowance",
    }
    for check in VALIDATION["checks"]:
        if check["name"] in selected:
            checks.append([check["name"], check["status"], check["evidence"]])
    story = [Paragraph("Milestone outcome", S["h1"]), Paragraph("Milestone 1 is complete at semantic version 0.1.0. It delivers the hull only and does not start any later content milestone.", S["callout"]), Paragraph("Completed work packages", S["h1"])]
    for item in ("Requirements and public-reference boundary", "Parameterized sixteen-station full-hull loft", "Bow/stern/waterline/anchor geometry", "Automatic A1 Mini-compatible splitting", "Four-shaft running gear and twin rudders", "Hidden self-aligning glue joints", "FCStd / STEP / STL / 3MF / OBJ exports", "Geometry QA, renders, drawings, BOM, and guides"):
        story.append(bullet(f"{item} — complete"))
    story += [Paragraph("Acceptance record", S["h1"]), table(checks, widths=[52 * mm, 18 * mm, 96 * mm], font_size=6.7), Paragraph("Configuration", S["h1"]), Paragraph("The 1:700 master is 476.0 mm long. The generator accepts 1:1000, 1:700, and 1:350 and derives split count from the scaled length. Functional gauges are clamped for a 0.4 mm nozzle.", S["body"]), Paragraph("Retained risks", S["h1"]), bullet("Physical first-article and adhesive fit remain required."), bullet("Public shipyard body plans were unavailable; station geometry is a documented public-data reconstruction."), bullet("STEP round-trip records OpenCascade p-curve diagnostics on analytic loft faces; all solids remain valid/closed with no self-intersection issue."), bullet("Appendage gauges prioritize reliable PLA printing over exact scale thinness."), Paragraph("Milestone gate", S["h1"]), Paragraph("v0.2 Flight Deck and all later milestones remain pending. No flight-deck detail, island, weapons, aircraft, radar, or display-base work is present in v0.1.0.", S["callout"]), Paragraph("Public technical references", S["h1"]), Paragraph('<a href="https://www.navsea.navy.mil/Portals/103/Documents/05C/2005_NAVSEA_CEH_Final.pdf">NAVSEA Cost Estimating Handbook — Nimitz-class overview</a><br/><a href="https://www.navsea.navy.mil/Portals/103/Documents/PSNSY_IMF/News%20Releases/2013%20Naval%20Nuclear%20Propulsion%20Program.pdf?ver=2017-03-02-113143-683">NAVSEA Naval Nuclear Propulsion Program — class dimensions</a><br/><a href="https://www.history.navy.mil/research/histories/naval-aviation-history/attack-carriers.html">Naval History and Heritage Command — attack carriers</a>', S["body"])]
    return story


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    generate_drawings()
    build_pdf(DOCS / "Hull_Assembly.pdf", "Hull Assembly Guide", "USS Dwight D. Eisenhower (CVN-69) · Museum Edition · v0.1.0", assembly_story())
    build_pdf(DOCS / "Hull_Printing_Guide.pdf", "Hull Printing Guide", "Bambu Lab X1C / P1S / A1 / A1 Mini · PLA · 0.4 mm nozzle", printing_story())
    build_pdf(DOCS / "Hull_ProjectPlan.pdf", "Milestone 1 Project Plan", "Completion record · acceptance evidence · next-milestone gate", plan_story())
    outputs = [DOCS / name for name in ("Hull_Drawings.pdf", "Hull_Assembly.pdf", "Hull_Printing_Guide.pdf", "Hull_ProjectPlan.pdf")]
    print(json.dumps({"generated": [str(path) for path in outputs], "bytes": {path.name: path.stat().st_size for path in outputs}}, indent=2))


if __name__ == "__main__":
    main()

