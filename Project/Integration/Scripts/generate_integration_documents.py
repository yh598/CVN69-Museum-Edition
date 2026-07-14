#!/usr/bin/env python3
"""Generate Milestone 2 drawings, printing guide, and coupon instructions."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
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
INTEGRATION = SCRIPT.parents[1]
DOCS = INTEGRATION / "Docs"
RENDER = INTEGRATION / "Render"
MANIFEST_PATH = INTEGRATION / "QA" / "build_manifest.json"
DOCS.mkdir(parents=True, exist_ok=True)


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fitted_image(path: Path, max_width: float, max_height: float):
    with PILImage.open(path) as image:
        width, height = image.size
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(name="TitleM2", parent=base["Title"], fontName="Helvetica-Bold", fontSize=22, leading=25, textColor=colors.HexColor("#20272A"), alignment=TA_LEFT, spaceAfter=10))
    base.add(ParagraphStyle(name="SubM2", parent=base["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#58646A"), spaceAfter=8))
    base.add(ParagraphStyle(name="HeadM2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.HexColor("#293238"), spaceBefore=8, spaceAfter=6))
    base.add(ParagraphStyle(name="BodyM2", parent=base["BodyText"], fontSize=8.5, leading=11.2, textColor=colors.HexColor("#30383C"), spaceAfter=5))
    base.add(ParagraphStyle(name="SmallM2", parent=base["BodyText"], fontSize=7.1, leading=9, textColor=colors.HexColor("#3D484E"), spaceAfter=3))
    base.add(ParagraphStyle(name="CenterM2", parent=base["SmallM2"], alignment=TA_CENTER))
    return base


S = styles()


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#B5BCBF"))
    canvas.line(doc.leftMargin, 0.43 * inch, doc.pagesize[0] - doc.rightMargin, 0.43 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#667177"))
    canvas.drawString(doc.leftMargin, 0.27 * inch, "CVN-69 Museum Edition · Milestone 2 Integration · Unreleased Review")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.27 * inch, f"Page {doc.page}")
    canvas.restoreState()


def styled_table(data, widths=None, font_size=7.2):
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#36434A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("LEADING", (0, 0), (-1, -1), font_size + 2),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB2B6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F6F5F0"), colors.HexColor("#EDEDE9")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def bullet(text):
    return Paragraph(f"• {text}", S["BodyM2"])


def build_drawings(manifest, output: Path):
    doc = SimpleDocTemplate(
        str(output),
        pagesize=landscape(letter),
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.43 * inch,
        bottomMargin=0.58 * inch,
        title="CVN-69 Hull–Deck Integration Drawings",
        author="yh598",
    )
    story = [
        Paragraph("CVN-69 Hull–Flight-Deck Integration Drawings", S["TitleM2"]),
        Paragraph("MILESTONE 2 · 1:700 · 476.00 MM OVERALL · GLUE-ONLY · UNRELEASED REVIEW", S["SubM2"]),
        fitted_image(RENDER / "CVN69_Hull_Deck_Top.png", 9.6 * inch, 4.55 * inch),
        Spacer(1, 0.08 * inch),
        styled_table(
            [
                ["Datum", "Authoritative definition", "Measured/nominal"],
                ["X", "Bow to stern", "0.00 to 476.00 mm"],
                ["Y", "Port negative to starboard positive", "centerline y = 0.00 mm"],
                ["Z", "Vertical from hull keel datum", "deck underside z = 31.50 mm"],
                ["Deck transform", "Mirror approved deck about x = 238 mm", "x′ = 476 − x; y unchanged"],
            ],
            widths=[1.1 * inch, 4.0 * inch, 3.9 * inch],
        ),
        PageBreak(),
        Paragraph("Module seam and interface station plan", S["TitleM2"]),
        Paragraph("Deck and hull seams remain intentionally staggered. Landing pads are paired at y = ±8 mm and avoid all seams, elevators, and the island opening.", S["SubM2"]),
        fitted_image(RENDER / "CVN69_Hull_Deck_Top.png", 9.7 * inch, 4.35 * inch),
        Spacer(1, 0.08 * inch),
        styled_table(
            [
                ["Feature", "X positions (mm)", "Engineering purpose"],
                ["Hull seams", "158.667, 317.333", "Approved concealed hull keys"],
                ["Deck seams", "146.000, 286.000", "Staggered; supported over single hull modules"],
                ["Landing-pad stations", "32, 105, 205, 270, 370, 445", "Paired port/starboard self-alignment"],
            ],
            widths=[1.7 * inch, 3.0 * inch, 4.3 * inch],
        ),
        PageBreak(),
        Paragraph("Interface sections", S["TitleM2"]),
        Paragraph("The keyed pad supplies repeatable lateral/longitudinal registration. The remaining overlapping hull-top area supplies continuous support and hidden glue surface.", S["SubM2"]),
        Table(
            [[
                fitted_image(RENDER / "Section_Keyed_Landing_Pad.png", 4.9 * inch, 4.7 * inch),
                fitted_image(RENDER / "Section_Direct_Support.png", 4.9 * inch, 4.7 * inch),
            ]],
            colWidths=[5.0 * inch, 5.0 * inch],
        ),
        styled_table(
            [
                ["Parameter", "Value", "Requirement"],
                ["Pad", "6.00 × 6.00 × 2.40 mm", "Printed Ash Gray PLA"],
                ["Socket", "6.50 × 6.50 mm", "0.25 mm clearance per side"],
                ["Hull insertion", "1.20 mm", "Meets minimum structural feature"],
                ["Deck socket", "1.45 mm deep", "Leaves 1.55 mm top skin"],
                ["Seating gap", "0.00 mm nominal", "≤ 0.30 mm"],
            ],
            widths=[2.2 * inch, 3.0 * inch, 4.0 * inch],
        ),
        PageBreak(),
        Paragraph("Assembly and exploded reference", S["TitleM2"]),
        Paragraph("All sockets and pads are concealed after assembly. No magnets, screws, metal pins, heat-set inserts, or purchased connectors are used.", S["SubM2"]),
        fitted_image(RENDER / "CVN69_Hull_Deck_Exploded.png", 9.7 * inch, 5.1 * inch),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_printing_guide(manifest, output: Path, mapping_csv: Path):
    doc = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        rightMargin=0.52 * inch,
        leftMargin=0.52 * inch,
        topMargin=0.48 * inch,
        bottomMargin=0.58 * inch,
        title="CVN-69 Hull–Deck Printing Guide",
        author="yh598",
    )
    story = [
        Paragraph("CVN-69 Milestone 2 Printing Guide", S["TitleM2"]),
        Paragraph("BAMBU-READY · 0.4 MM NOZZLE · GLUE-ONLY · 1:700", S["SubM2"]),
        fitted_image(RENDER / "CVN69_Hull_Deck_Bow_Isometric.png", 7.2 * inch, 3.6 * inch),
        Paragraph("Print files", S["HeadM2"]),
        styled_table(
            [
                ["3MF", "Contents", "Validated size (mm)"],
                ["Print_Plate_01_Hull.3mf", "3 hull modules + approved running gear", "220.06 × 177.29 × 31.43"],
                ["Print_Plate_02_Deck.3mf", "3 socketed deck modules", "197.00 × 217.95 × 3.00"],
                ["Print_Plate_03_Details.3mf", "19 deck details + 12 interface pads", "216.80 × 171.59 × 2.40"],
                ["Interface_Test_Coupon.3mf", "male/female clearance test", "53.00 × 20.00 × 5.20"],
            ],
            widths=[1.75 * inch, 3.25 * inch, 1.7 * inch],
        ),
        Paragraph("Orientation and support", S["HeadM2"]),
        bullet("Hull modules print with their flat hull-top datum downward. Interface sockets are open to the bed; maximum socket roof span is 6.50 mm."),
        bullet("Deck modules print underside down. The new sockets are open and shallow; visible deck surfaces and planform are unchanged."),
        bullet("Elevators, markings, tracks, wires, and landing pads print flat. Use a brim only if your build surface needs it for the longest thin details."),
        bullet("Do not auto-scale. Every production STL and print 3MF is already millimetres at 1:700."),
        PageBreak(),
        Paragraph("Material mapping by object name", S["TitleM2"]),
        Paragraph(f"This table is also supplied as {mapping_csv.name}. AMS slot numbers are deliberately not assigned.", S["SubM2"]),
    ]
    mapping_rows = [["Object name", "Material"]] + [[name, material] for name, material in sorted(manifest["material_mapping"].items())]
    story.append(styled_table(mapping_rows, widths=[3.65 * inch, 3.05 * inch], font_size=6.6))
    story += [
        PageBreak(),
        Paragraph("Interface fit and assembly readiness", S["TitleM2"]),
        Paragraph("Print and test the coupon before the complete assembly. The designed lateral clearance is 0.25 mm per side; the deck should seat flat before adhesive is applied.", S["SubM2"]),
        fitted_image(RENDER / "Section_Keyed_Landing_Pad.png", 7.1 * inch, 4.6 * inch),
        Paragraph("Acceptance checks", S["HeadM2"]),
        bullet("Male feature enters without force and has no elephant-foot interference."),
        bullet("Female face seats against the male base with no visible rocking or gap over 0.30 mm."),
        bullet("A small amount of the intended adhesive cures without locking the parts before full seating."),
        bullet("If the coupon fails, adjust slicer compensation or reprint; do not scale the production model."),
        PageBreak(),
        Paragraph("Glue-only assembly sequence", S["TitleM2"]),
        Paragraph("Use the complete procedure in Assembly/Glue_Only_Assembly.md. The short sequence is:", S["SubM2"]),
        bullet("Assemble and cure the approved hull modules on a straight datum."),
        bullet("Assemble and cure the transformed deck modules on a flat datum."),
        bullet("Dry-fit all twelve pads in the hull, then lower the deck vertically and verify full seating."),
        bullet("Apply a thin adhesive film only to hidden seating areas and sockets; reinstall without longitudinal sliding."),
        bullet("Install elevators and raised details after the hull/deck bond has cured."),
        Spacer(1, 0.14 * inch),
        fitted_image(RENDER / "CVN69_Hull_Deck_Exploded.png", 7.1 * inch, 3.6 * inch),
        Paragraph("This automated package does not replace a physical first-article print. Record the coupon result before full bonding.", S["SmallM2"]),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_coupon_instruction(output: Path):
    doc = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.50 * inch,
        bottomMargin=0.58 * inch,
        title="CVN-69 Interface Test Coupon Instructions",
        author="yh598",
    )
    story = [
        Paragraph("CVN-69 Deck-to-Hull Interface Coupon", S["TitleM2"]),
        Paragraph("ONE-PAGE PRINT / FIT / GLUE TEST · RUN BEFORE THE FULL MILESTONE 2 PRINT", S["SubM2"]),
        fitted_image(RENDER / "Section_Keyed_Landing_Pad.png", 7.0 * inch, 3.8 * inch),
        styled_table(
            [
                ["Coupon feature", "Actual production value"],
                ["Male feature", "6.00 × 6.00 mm; 1.20 mm protrusion"],
                ["Female opening", "6.50 × 6.50 mm; 1.45 mm depth"],
                ["Nominal clearance", "0.25 mm per side"],
                ["Female top wall", "1.55 mm"],
                ["Combined print layout", "53 × 20 × 5.2 mm"],
            ],
            widths=[2.6 * inch, 4.0 * inch],
        ),
        Paragraph("Procedure", S["HeadM2"]),
        bullet("Print `3MF/Interface_Test_Coupon.3mf` at 100% scale with the same nozzle, layer height, material, and XY compensation planned for production."),
        bullet("Remove brim and elephant foot without filing the nominal male or female walls."),
        bullet("Dry-fit: the male must enter by hand, the broad faces must fully touch, and the fit must not rock or require force."),
        bullet("Glue-fit: apply the intended adhesive sparingly, fully seat, allow it to cure, and record material, slicer profile, measured gap, and result."),
        bullet("Pass: full seating and stable alignment. Fail: force fit, more than 0.30 mm seating gap, cracked wall, or adhesive lock before seating."),
        Paragraph("Do not scale the production model to compensate for a failed coupon. Correct printer calibration or slicer XY compensation, then repeat the coupon.", S["BodyM2"]),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def update_manifest(paths):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for path in paths:
        manifest["outputs"][str(path.relative_to(INTEGRATION))] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    mapping_csv = DOCS / "Material_Mapping.csv"
    with mapping_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["object_name", "material"])
        for name, material in sorted(manifest["material_mapping"].items()):
            writer.writerow([name, material])

    drawings = DOCS / "Hull_Deck_Integration_Drawings.pdf"
    printing = DOCS / "Hull_Deck_Printing_Guide.pdf"
    coupon = DOCS / "Interface_Test_Coupon_Instructions.pdf"
    build_drawings(manifest, drawings)
    build_printing_guide(manifest, printing, mapping_csv)
    build_coupon_instruction(coupon)
    paths = [
        drawings,
        printing,
        coupon,
        mapping_csv,
        INTEGRATION / "README.md",
        INTEGRATION / "Assembly" / "Glue_Only_Assembly.md",
        INTEGRATION / "CAD" / "Python" / "integration_parameters.py",
        INTEGRATION / "Scripts" / "build_hull_deck_integration.py",
        INTEGRATION / "Scripts" / "render_hull_deck_integration.py",
        INTEGRATION / "Scripts" / "run_bambu_integration_checks.py",
        INTEGRATION / "Scripts" / "generate_integration_documents.py",
        INTEGRATION / "Scripts" / "validate_hull_deck_integration.py",
    ]
    update_manifest(paths)
    print(json.dumps({"status": "ok", "outputs": [str(path) for path in paths]}, indent=2))


if __name__ == "__main__":
    main()
