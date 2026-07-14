#!/usr/bin/env python3
"""Generate Milestone 3 island drawings, guides, plan, and coupon PDF."""

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
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


SCRIPT = Path(__file__).resolve()
ISLAND = SCRIPT.parents[1]
DOCS = ISLAND / "Docs"
RENDER = ISLAND / "Render"
MANIFEST_PATH = ISLAND / "QA" / "build_manifest.json"
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


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleM3", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21, leading=24, textColor=colors.HexColor("#20272A"), alignment=TA_LEFT, spaceAfter=8))
styles.add(ParagraphStyle(name="SubM3", parent=styles["Normal"], fontSize=8.7, leading=11, textColor=colors.HexColor("#58646A"), spaceAfter=7))
styles.add(ParagraphStyle(name="HeadM3", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13.5, leading=16, textColor=colors.HexColor("#293238"), spaceBefore=7, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyM3", parent=styles["BodyText"], fontSize=8.4, leading=11.0, textColor=colors.HexColor("#30383C"), spaceAfter=4.5))
styles.add(ParagraphStyle(name="SmallM3", parent=styles["BodyText"], fontSize=7.0, leading=8.8, textColor=colors.HexColor("#3D484E"), spaceAfter=3))
styles.add(ParagraphStyle(name="CenterM3", parent=styles["SmallM3"], alignment=TA_CENTER))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#B5BCBF"))
    canvas.line(doc.leftMargin, 0.43 * inch, doc.pagesize[0] - doc.rightMargin, 0.43 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#667177"))
    canvas.drawString(doc.leftMargin, 0.27 * inch, "CVN-69 Museum Edition · Milestone 3 Island · Public-reference reconstruction")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.27 * inch, f"Page {doc.page}")
    canvas.restoreState()


def table(data, widths=None, font_size=7.1):
    item = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    item.setStyle(
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
    return item


def bullet(text):
    return Paragraph(f"• {text}", styles["BodyM3"])


def build_drawings(manifest, output):
    doc = SimpleDocTemplate(str(output), pagesize=landscape(letter), rightMargin=0.42 * inch, leftMargin=0.42 * inch, topMargin=0.40 * inch, bottomMargin=0.58 * inch, title="CVN-69 Island Drawings", author="yh598")
    p = manifest["parameters_mm"]
    story = [
        Paragraph("CVN-69 Island Reconstruction Drawings", styles["TitleM3"]),
        Paragraph("MILESTONE 3 · 1:700 · 2023–2024 DEPLOYMENT FIT · GLUE-ONLY · UNRELEASED REVIEW", styles["SubM3"]),
        fitted_image(RENDER / "Island_Top.png", 9.7 * inch, 4.70 * inch),
        table(
            [
                ["Datum / dimension", "Value", "Status"],
                ["Ship X", "0.00 mm bow → 476.00 mm stern", "approved Milestone 2"],
                ["Deck underside / top", f"z = {p['deck_base_z']:.2f} / {p['deck_top_z']:.2f} mm", "approved Milestone 2"],
                ["Island opening bounds", "x 325.00–355.00; y 19.20–33.00 mm", "transformed approved opening"],
                ["Mast top", f"z = {p['deck_top_z'] + p['mast_height_above_deck']:.2f} mm", "photo/source-informed"],
            ],
            widths=[2.4 * inch, 4.1 * inch, 2.8 * inch],
        ),
        PageBreak(),
        Paragraph("Longitudinal elevations", styles["TitleM3"]),
        Table([[fitted_image(RENDER / "Island_Port.png", 4.9 * inch, 4.8 * inch), fitted_image(RENDER / "Island_Starboard.png", 4.9 * inch, 4.8 * inch)]], colWidths=[5.0 * inch, 5.0 * inch]),
        Paragraph("All geometry is in the authoritative bow-origin coordinate system. Window bands and markings are separate recessed/glue-on color objects.", styles["SmallM3"]),
        PageBreak(),
        Paragraph("Forward and aft elevations", styles["TitleM3"]),
        Table([[fitted_image(RENDER / "Island_Forward.png", 4.9 * inch, 4.8 * inch), fitted_image(RENDER / "Island_Aft.png", 4.9 * inch, 4.8 * inch)]], colWidths=[5.0 * inch, 5.0 * inch]),
        PageBreak(),
        Paragraph("Assembly breakdown", styles["TitleM3"]),
        fitted_image(RENDER / "Island_Exploded.png", 9.7 * inch, 5.1 * inch),
        PageBreak(),
        Paragraph("Foundation and interface geometry", styles["TitleM3"]),
        fitted_image(RENDER / "Island_Interface_Section.png", 9.7 * inch, 4.9 * inch),
        table(
            [
                ["Parameter", "Production value", "Acceptance"],
                ["Plug clearance", f"{p['interface_clearance_per_side']:.2f} mm per side", "±0.05 mm from parameter"],
                ["Plug insertion", f"{p['interface_plug_depth']:.2f} mm", "vertical seating error ≤0.10 mm"],
                ["Glue channels", f"{p['glue_channel_width']:.2f} × {p['glue_channel_depth']:.2f} mm", "hidden and open"],
                ["Structural wall", f"≥ {p['minimum_structural_wall']:.2f} mm", "mandatory"],
            ],
            widths=[2.4 * inch, 3.0 * inch, 3.8 * inch],
        ),
        PageBreak(),
        Paragraph("Part and material schedule", styles["TitleM3"]),
        Paragraph("Dimensions are assembly-axis bounding sizes. Print-oriented sizes and exact hashes are in QA/build_manifest.json.", styles["SubM3"]),
    ]
    rows = [["Part", "Role", "Material", "Assembly size x × y × z (mm)"]]
    for item in manifest["parts"]:
        b = item["assembly_bounds_mm"]
        size = f"{b[3]-b[0]:.2f} × {b[4]-b[1]:.2f} × {b[5]-b[2]:.2f}"
        rows.append([item["name"], item["role"], item["material"].replace("Bambu PLA ", ""), size])
    story.append(table(rows, widths=[2.65 * inch, 2.15 * inch, 2.55 * inch, 2.15 * inch], font_size=6.3))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_printing_guide(manifest, output):
    doc = SimpleDocTemplate(str(output), pagesize=letter, rightMargin=0.50 * inch, leftMargin=0.50 * inch, topMargin=0.46 * inch, bottomMargin=0.58 * inch, title="CVN-69 Island Printing Guide", author="yh598")
    story = [
        Paragraph("CVN-69 Milestone 3 Island Printing Guide", styles["TitleM3"]),
        Paragraph("BAMBU X1C / P1S / A1 · A1 MINI PRACTICAL · 0.4 MM NOZZLE · PLA · NO PAINT REQUIRED", styles["SubM3"]),
        fitted_image(RENDER / "Island_Bow_Isometric.png", 7.2 * inch, 4.1 * inch),
        Paragraph("Print files", styles["HeadM3"]),
        table(
            [
                ["3MF", "Objects"],
                ["Print_Plate_01_Island_Body.3mf", "foundation/lower body, navigation bridge, primary flight control, exhaust/uptake"],
                ["Print_Plate_02_Mast_Radar.3mf", "main and secondary masts, yardarm, SPS-48G, SPS-49-family, SPN-50"],
                ["Print_Plate_03_Antennas_Details.3mf", "window inserts, ladder, antennas, signal housings, port/starboard 69"],
                ["Island_Interface_Test_Coupon.3mf", "exact male and female production interface"],
            ],
            widths=[2.45 * inch, 4.35 * inch],
        ),
        PageBreak(),
        Paragraph("Orientation and FDM rules", styles["TitleM3"]),
        bullet("Do not auto-scale. All files are millimetres at 1:700 and already rest at z = 0 in the documented print orientation."),
        bullet("Foundation prints plug-down; the 0.90 mm hidden flange overhang is short and open. Inspect the four glue channels after brim removal."),
        bullet("Masts, radar faces, markings, and ladder are rotated flat where appropriate. Keep detailed radar ribs facing upward."),
        bullet("Minimum structural wall is 1.20 mm; freestanding mast elements are 0.80 mm or larger; railings and non-freestanding antennas are 0.60 mm or larger."),
        bullet("Use a brim only where your bed adhesion requires it. No enclosed support traps are present."),
        fitted_image(RENDER / "Island_Stern_Isometric.png", 7.1 * inch, 4.4 * inch),
        PageBreak(),
        Paragraph("Object-based color mapping", styles["TitleM3"]),
        Paragraph("AMS slots are not assigned. Print colors separately and glue; this avoids inefficient layer-by-layer color changes.", styles["SubM3"]),
    ]
    rows = [["Object", "Material"]] + [[name, material] for name, material in sorted(manifest["material_mapping"].items())]
    story.append(table(rows, widths=[3.45 * inch, 3.25 * inch], font_size=6.5))
    story += [
        PageBreak(),
        Paragraph("Coupon and first-article acceptance", styles["TitleM3"]),
        fitted_image(RENDER / "Island_Interface_Section.png", 7.1 * inch, 4.2 * inch),
        bullet("Print the coupon with the exact production process before committing the full island."),
        bullet("Pass: hand insertion, full broad-face seating, no rocking, no cracked wall, and glue does not lock the part before seating."),
        bullet("Fail: force fit, visible deformation, incomplete seating, or more than 0.10 mm vertical seating error after cleanup."),
        bullet("Correct printer calibration or slicer compensation; never scale the production island."),
        Paragraph("Automated validation is necessary but does not replace a physical coupon and first-article dry fit.", styles["SmallM3"]),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_project_plan(manifest, output):
    doc = SimpleDocTemplate(str(output), pagesize=letter, rightMargin=0.52 * inch, leftMargin=0.52 * inch, topMargin=0.48 * inch, bottomMargin=0.58 * inch, title="CVN-69 Island Project Plan", author="yh598")
    story = [
        Paragraph("CVN-69 Milestone 3 Island Project Plan", styles["TitleM3"]),
        Paragraph("PARAMETRIC RECONSTRUCTION · CONFIGURATION CONTROL · PRINTABILITY · VALIDATION", styles["SubM3"]),
        fitted_image(RENDER / "CVN69_Hull_Deck_Island_Top.png", 7.1 * inch, 3.3 * inch),
        Paragraph("Objective and frozen scope", styles["HeadM3"]),
        bullet("Reconstruct only the island as clean FreeCAD/OpenCascade solids and integrate it with the immutable Milestone 2 hull/deck baseline."),
        bullet("Freeze the 2023–2024 deployment fit using official public references; identify all photo-derived approximation and uncertainty."),
        bullet("Deliver glue-only, no-paint, 0.4 mm-nozzle parts and a physical reproduction of the production interface."),
        bullet("Exclude weapons, aircraft, deck vehicles, ocean base, display stand, electronics, and final-ship release."),
        Paragraph("Release gate", styles["HeadM3"]),
        Paragraph("No completion or production claim is made unless every required file exists and all BRep, STEP, mesh, interface, interference, 3MF, hash, and Bambu Studio checks pass. A physical first article remains a separate real-world gate.", styles["BodyM3"]),
        PageBreak(),
        Paragraph("Work breakdown and evidence", styles["TitleM3"]),
        table(
            [
                ["Stage", "Deterministic output", "Evidence"],
                ["Reference audit", "Configuration_Audit.md; mesh measurements/image", "official URLs, access date, source hashes"],
                ["Parameters", "island_parameters.py", "imports approved integration/deck modules"],
                ["CAD build", "FCStd, STEP, STL, 3MF, OBJ", "new BReps; no STL import"],
                ["Visual review", "14 high-resolution renders", "island and integrated orthographic/isometric views"],
                ["Documentation", "drawings, printing, plan, coupon PDFs", "object/material/interface schedules"],
                ["Validation", "Markdown + JSON QA", "FreeCAD, STEP, STL, 3MF, Bambu Studio"],
            ],
            widths=[1.25 * inch, 2.55 * inch, 2.90 * inch],
        ),
        Paragraph("Accuracy classifications", styles["HeadM3"]),
        bullet("Dimensionally verified: approved deck datum, opening polygon, coordinate transform, CAD interface clearances."),
        bullet("Source-mesh-derived: island placement envelope and approximate mast-height envelope only."),
        bullet("Photo-derived: bridge/PriFly/uptake/mast proportions and major visible platform arrangement."),
        bullet("Visually approximated: minor antennas, ladder, signal housings, and simplified radar face ribs."),
        PageBreak(),
        Paragraph("Change control and reproducibility", styles["TitleM3"]),
        fitted_image(RENDER / "CVN69_Hull_Deck_Island_Bow_Isometric.png", 7.1 * inch, 3.6 * inch),
        bullet("All Milestone 3 work is isolated under Project/Island/. Approved Milestone 1–2 hashes are captured before build and rechecked during validation."),
        bullet("Generation is executable from repository root. The manifest records SHA-256 and byte size for every production output."),
        bullet("The integrated hull/deck/island files are non-production review assemblies and do not duplicate baseline production STLs."),
        bullet("No release tag is created; Milestone 3 stops after commit and push for review."),
        Paragraph(f"Configured production parts: {manifest['counts']['production_parts']}; coupon parts: {manifest['counts']['coupon_parts']}; frozen period: {manifest['configuration_period']}.", styles["BodyM3"]),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_coupon(output):
    doc = SimpleDocTemplate(str(output), pagesize=letter, rightMargin=0.50 * inch, leftMargin=0.50 * inch, topMargin=0.46 * inch, bottomMargin=0.56 * inch, title="CVN-69 Island Interface Coupon Instructions", author="yh598")
    story = [
        Paragraph("CVN-69 Island Interface Coupon", styles["TitleM3"]),
        Paragraph("ONE-PAGE PRINT / FIT / GLUE TEST · RUN BEFORE THE PRODUCTION ISLAND", styles["SubM3"]),
        fitted_image(RENDER / "Island_Interface_Section.png", 7.1 * inch, 3.75 * inch),
        table(
            [
                ["Feature", "Exact production value"],
                ["Female geometry", "approved asymmetric island opening"],
                ["Male geometry", "opening inset 0.25 mm per side"],
                ["Insertion", "2.40 mm"],
                ["Glue channels", "0.60 mm wide × 0.35 mm deep; open"],
                ["Coupon envelope", "40 × 24 mm pieces; under 60 × 60 × 25 mm"],
            ],
            widths=[2.35 * inch, 4.35 * inch],
        ),
        Paragraph("Procedure", styles["HeadM3"]),
        bullet("Print both named objects at 100% with the same printer, 0.4 mm nozzle, PLA, layer height, and XY/elephant-foot compensation planned for production."),
        bullet("Remove brim without filing nominal male/female walls. Dry-fit by hand; do not force."),
        bullet("Pass when the broad faces seat fully, the fit does not rock, and no wall cracks or whitens."),
        bullet("Apply the intended adhesive sparingly through the open channels, seat fully, cure, and record the result."),
        bullet("If it fails, correct calibration or slicer compensation and repeat. Do not scale production files."),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def update_manifest(paths):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for path in paths:
        manifest["outputs"][str(path.relative_to(ISLAND))] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    mapping = DOCS / "Island_Material_Mapping.csv"
    with mapping.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["object_name", "material"])
        for name, material in sorted(manifest["material_mapping"].items()):
            writer.writerow([name, material])
    outputs = [
        DOCS / "Island_Drawings.pdf",
        DOCS / "Island_Printing_Guide.pdf",
        DOCS / "Island_Project_Plan.pdf",
        DOCS / "Island_Interface_Coupon_Instructions.pdf",
    ]
    build_drawings(manifest, outputs[0])
    build_printing_guide(manifest, outputs[1])
    build_project_plan(manifest, outputs[2])
    build_coupon(outputs[3])
    source_files = [
        ISLAND / "README.md",
        ISLAND / "Assembly" / "Glue_Only_Island_Assembly.md",
        ISLAND / "References" / "Configuration_Audit.md",
        ISLAND / "QA" / "Reference_Confidence_Report.md",
        ISLAND / "CAD" / "Python" / "island_parameters.py",
        *sorted((ISLAND / "Scripts").glob("*.py")),
    ]
    update_manifest([*outputs, mapping, *source_files])
    print(json.dumps({"status": "ok", "outputs": [str(path) for path in outputs]}, indent=2))


if __name__ == "__main__":
    main()
