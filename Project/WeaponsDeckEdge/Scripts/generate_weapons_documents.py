#!/usr/bin/env python3
"""Generate Milestone 4 drawings, printing guide, project plan, and coupon PDF."""

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
M4 = SCRIPT.parents[1]
DOCS = M4 / "Docs"
RENDER = M4 / "Render"
MANIFEST_PATH = M4 / "QA" / "build_manifest.json"
DOCS.mkdir(parents=True, exist_ok=True)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fitted_image(path, max_width, max_height):
    with PILImage.open(path) as source:
        width, height = source.size
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleM4", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=23, textColor=colors.HexColor("#20272A"), alignment=TA_LEFT, spaceAfter=7))
styles.add(ParagraphStyle(name="SubM4", parent=styles["Normal"], fontSize=8.5, leading=10.5, textColor=colors.HexColor("#58646A"), spaceAfter=6))
styles.add(ParagraphStyle(name="HeadM4", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=15, textColor=colors.HexColor("#293238"), spaceBefore=6, spaceAfter=4))
styles.add(ParagraphStyle(name="BodyM4", parent=styles["BodyText"], fontSize=8.2, leading=10.7, textColor=colors.HexColor("#30383C"), spaceAfter=4))
styles.add(ParagraphStyle(name="SmallM4", parent=styles["BodyText"], fontSize=6.9, leading=8.5, textColor=colors.HexColor("#3D484E"), spaceAfter=3))
styles.add(ParagraphStyle(name="CenterM4", parent=styles["SmallM4"], alignment=TA_CENTER))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#B5BCBF"))
    canvas.line(doc.leftMargin, 0.43 * inch, doc.pagesize[0] - doc.rightMargin, 0.43 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#667177"))
    canvas.drawString(doc.leftMargin, 0.27 * inch, "CVN-69 Museum Edition · Milestone 4 · Public-reference reconstruction")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.27 * inch, f"Page {doc.page}")
    canvas.restoreState()


def table(data, widths=None, font_size=7.0):
    item = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    item.setStyle(TableStyle([
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
    ]))
    return item


def bullet(text):
    return Paragraph(f"• {text}", styles["BodyM4"])


def build_drawings(manifest, output):
    doc = SimpleDocTemplate(str(output), pagesize=landscape(letter), rightMargin=0.40 * inch, leftMargin=0.40 * inch, topMargin=0.38 * inch, bottomMargin=0.58 * inch, title="CVN-69 Weapons and Deck-Edge Drawings", author="yh598")
    p = manifest["parameters_mm"]
    story = [
        Paragraph("CVN-69 Defensive Systems and Deck-Edge Drawings", styles["TitleM4"]),
        Paragraph("MILESTONE 4 · 1:700 · 2023–2024 DEPLOYMENT FIT · GLUE-ONLY · PUBLIC-PHOTO-DERIVED REVIEW", styles["SubM4"]),
        fitted_image(RENDER / "CVN69_Hull_Deck_Island_Weapons_Top.png", 9.7 * inch, 4.55 * inch),
        table([
            ["Datum / count", "Value", "Classification"],
            ["Ship coordinate system", "X 0.00 bow → 476.00 stern; port Y negative; starboard Y positive", "approved Milestones 1–3"],
            ["Deck underside / top", f"z = {p['deck_base_z']:.2f} / {p['deck_top_z']:.2f} mm", "approved integration datum"],
            ["Defensive fit", "2 CIWS · 2 RAM · 2 Mk 29 / ESSM", "official-system evidence + cross-image count"],
            ["Production objects", f"{manifest['counts']['production_parts']} plus 2 coupon objects", "new parametric BReps"],
        ], widths=[2.15 * inch, 4.75 * inch, 2.45 * inch]),
        PageBreak(),
        Paragraph("Authoritative installation coordinates and footprints", styles["TitleM4"]),
    ]
    coordinate_rows = [["Installation", "Family", "X", "Y", "Z seat", "Platform", "Confidence"]]
    for item in manifest["installations"]:
        coordinate_rows.append([item["name"], item["family"], f"{item['x']:.2f}", f"{item['y']:.2f}", f"{p['deck_top_z']:.2f}", item["platform"], item["confidence"]])
    story += [table(coordinate_rows, widths=[2.25 * inch, 0.75 * inch, 0.55 * inch, 0.55 * inch, 0.65 * inch, 1.95 * inch, 2.55 * inch], font_size=6.6), Spacer(1, 0.12 * inch)]
    story.append(Table([[fitted_image(RENDER / "Weapon_Area_Forward_Port.png", 4.85 * inch, 2.65 * inch), fitted_image(RENDER / "Weapon_Area_Forward_Starboard.png", 4.85 * inch, 2.65 * inch)]], colWidths=[5.0 * inch, 5.0 * inch]))
    story += [PageBreak(), Paragraph("Aft weapon areas", styles["TitleM4"]), Table([[fitted_image(RENDER / "Weapon_Area_Aft_Port.png", 4.85 * inch, 4.7 * inch), fitted_image(RENDER / "Weapon_Area_Aft_Starboard.png", 4.85 * inch, 4.7 * inch)]], colWidths=[5.0 * inch, 5.0 * inch])]
    story += [PageBreak(), Paragraph("Major system dimensions and part breakdown", styles["TitleM4"]), Table([[fitted_image(RENDER / "CIWS_Assembly_Closeup.png", 3.2 * inch, 3.4 * inch), fitted_image(RENDER / "RAM_Assembly_Closeup.png", 3.2 * inch, 3.4 * inch), fitted_image(RENDER / "SeaSparrow_Assembly_Closeup.png", 3.2 * inch, 3.4 * inch)]], colWidths=[3.35 * inch] * 3)]
    story.append(table([
        ["Representation", "Major CAD envelope / minimum", "Print orientation"],
        ["CIWS", "foundation + upper body + dome + fixed 1.00 mm barrel", "foundation key-down; body/dome base-down; barrel z=0 export"],
        ["Mk 49 RAM", "foundation + 5.80 mm launcher + separate 4×3 FDM-safe face", "bases down; dark face flat"],
        ["Mk 29 / ESSM", "foundation + 4.80 mm launcher + separate 4×2 FDM-safe face", "bases down; dark face flat"],
        ["Common platform", "2.40 mm thick; 1.20 mm socket; 1.20 mm remaining skin", "broad face down"],
    ], widths=[2.0 * inch, 4.1 * inch, 3.5 * inch]))
    story += [PageBreak(), Paragraph("Exploded assembly", styles["TitleM4"]), fitted_image(RENDER / "Weapons_DeckEdge_Exploded.png", 9.75 * inch, 5.4 * inch)]
    story += [PageBreak(), Paragraph("Common glue-only interface section", styles["TitleM4"]), fitted_image(RENDER / "Weapon_Interface_Family_Section.png", 9.7 * inch, 4.8 * inch), table([
        ["Interface parameter", "Production value", "Acceptance"],
        ["Nominal clearance", f"{p['interface_clearance_per_side']:.2f} mm per side", "coupon dry-fit; no forcing"],
        ["Key / socket depth", f"{p['key_depth']:.2f} mm", "vertical seating error < 0.10 mm"],
        ["Remaining platform skin", f"{p['remaining_platform_skin']:.2f} mm", "≥ 1.20 mm"],
        ["Glue channel", "0.60 × 0.35 mm; open and hidden", "no trapped cavity"],
        ["Installed lean", "0.00° CAD intent", "< 0.30°"],
    ], widths=[2.35 * inch, 3.25 * inch, 3.75 * inch])]
    story += [PageBreak(), Paragraph("Print-plate layouts and material assignments", styles["TitleM4"]), Table([
        [fitted_image(RENDER / "Print_Plate_01_Overview.png", 4.85 * inch, 2.35 * inch), fitted_image(RENDER / "Print_Plate_02_Overview.png", 4.85 * inch, 2.35 * inch)],
        [fitted_image(RENDER / "Print_Plate_03_Overview.png", 4.85 * inch, 2.35 * inch), fitted_image(RENDER / "Print_Plate_04_Overview.png", 4.85 * inch, 2.35 * inch)],
    ], colWidths=[5.0 * inch, 5.0 * inch])]
    story.append(Paragraph("Ash Gray: structures. Charcoal: launcher/boat inserts. Ivory White: CIWS domes and life rafts. Silk Silver: CIWS barrels/details. Basic Black: navigation-light housings. No AMS slot is fixed.", styles["SmallM4"]))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_printing_guide(manifest, output):
    doc = SimpleDocTemplate(str(output), pagesize=letter, rightMargin=0.50 * inch, leftMargin=0.50 * inch, topMargin=0.45 * inch, bottomMargin=0.58 * inch, title="CVN-69 Weapons Deck-Edge Printing Guide", author="yh598")
    story = [
        Paragraph("CVN-69 Milestone 4 Printing Guide", styles["TitleM4"]),
        Paragraph("BAMBU P2S PRIMARY · X1C / P1S / A1 · A1 MINI WHERE PRACTICAL · 0.4 MM NOZZLE · PLA", styles["SubM4"]),
        fitted_image(RENDER / "CVN69_Hull_Deck_Island_Weapons_Bow_Isometric.png", 7.1 * inch, 3.25 * inch),
        Paragraph("Plate files", styles["HeadM4"]),
        table([
            ["3MF", "Named-object contents / layer height"],
            ["Print_Plate_01_Major_Weapons.3mf", "launcher/CIWS bodies, faces, domes, barrels · 0.12 mm"],
            ["Print_Plate_02_Sponsons_Foundations.3mf", "five weapon sponsons and six foundations · 0.16/0.12 mm"],
            ["Print_Plate_03_LifeRafts_Boats.3mf", "six life-raft groups, access platform, boat, insert, cradle, davit · 0.16 mm"],
            ["Print_Plate_04_DeckEdge_Details.3mf", "railings, ladders, lights, lockers · 0.12 mm"],
            ["Weapon_Mount_Interface_Test_Coupon.3mf", "actual male/female interface · print first"],
        ], widths=[2.65 * inch, 4.15 * inch]),
        PageBreak(), Paragraph("FDM requirements and orientation", styles["TitleM4"]),
        bullet("Do not auto-scale. Exports are millimetres at 1:700 and every production STL rests at z = 0 in its documented orientation."),
        bullet("Minimum structural wall 1.20 mm; fragile post 0.80 mm; preferred barrel 1.00 mm; raised feature 0.50 mm wide × 0.35 mm high; railing/ladder 0.60 mm."),
        bullet("Print sponsons and foundations with broad/keyed faces down. Keep launcher faces and fine inserts flat. Avoid supports inside open sockets."),
        bullet("No part exceeds 240 × 240 × 240 mm. Review/assembly 3MF files are not print plates."),
        fitted_image(RENDER / "Print_Plate_02_Overview.png", 7.0 * inch, 3.7 * inch),
        PageBreak(), Paragraph("No-paint object materials", styles["TitleM4"]),
        Paragraph("Assign filament by object name; no AMS slot is fixed. Separate inserts are preferred over layer-by-layer multicolor waste.", styles["SubM4"]),
    ]
    story.append(table([["Object", "Material"]] + [[name, material] for name, material in sorted(manifest["material_mapping"].items())], widths=[3.65 * inch, 3.15 * inch], font_size=6.1))
    story += [PageBreak(), Paragraph("Coupon and first-article acceptance", styles["TitleM4"]), fitted_image(RENDER / "Weapon_Interface_Family_Section.png", 7.1 * inch, 4.0 * inch), bullet("Print the coupon using the exact planned printer, material, layer height, and elephant-foot/XY compensation."), bullet("Pass: hand insertion, complete seating, no rocking, no cracked 1.20 mm skin, and the asymmetric key cannot reverse."), bullet("Fail: force fit, incomplete seating, more than 0.10 mm vertical error, visible lean over 0.30°, or glue trapped below the key."), bullet("Correct calibration and reprint. Never scale the production ship or sand the key into symmetry.")]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_project_plan(manifest, output):
    doc = SimpleDocTemplate(str(output), pagesize=letter, rightMargin=0.52 * inch, leftMargin=0.52 * inch, topMargin=0.47 * inch, bottomMargin=0.58 * inch, title="CVN-69 Weapons Deck-Edge Project Plan", author="yh598")
    story = [
        Paragraph("CVN-69 Milestone 4 Project Plan", styles["TitleM4"]),
        Paragraph("PUBLIC-REFERENCE AUDIT · PARAMETRIC RECONSTRUCTION · PRINTABILITY · FULL QA", styles["SubM4"]),
        fitted_image(RENDER / "CVN69_Hull_Deck_Island_Weapons_Top.png", 7.05 * inch, 2.65 * inch),
        Paragraph("Objective and frozen scope", styles["HeadM4"]),
        bullet("Create only publicly visible defensive systems and major deck-edge equipment compatible with immutable Milestones 1–3."),
        bullet("Freeze the 2023-10-14 through 2024-07-14 deployment fit, with June 2024 visible evidence preferred."),
        bullet("Build new parametric BReps; supplied STL triangles remain reference-only and never enter production geometry."),
        bullet("Exclude aircraft, vehicles, ammunition, internal/functional weapon mechanisms, ocean/display systems, electronics, and final release."),
        Paragraph("Accuracy policy", styles["HeadM4"]),
        bullet("Approved datums and interfaces are dimensionally verified; system identities use official public Navy/NAVSEA evidence."),
        bullet("Counts and placements are cross-image-derived and explicitly medium-confidence where a single view is obstructed."),
        bullet("Launcher grids, barrel, railings, ladders, and canisters are conservatively enlarged FDM-safe representations."),
        PageBreak(), Paragraph("Deterministic work breakdown", styles["TitleM4"]),
        table([
            ["Stage", "Outputs", "Release evidence"],
            ["Reference audit", "Configuration_Audit.md + JSON confidence report", "official URLs, dates, access date, counts, uncertainties"],
            ["Parameters", "weapons_deckedge_parameters.py", "imports approved integration/island modules"],
            ["CAD build", "FCStd, STEP, STL, OBJ, 3MF", "43 production objects; no STL import"],
            ["Physical fit", "STEP/STL/3MF coupon", "actual asymmetric 0.25 mm-per-side interface"],
            ["Visual review", "19 renders", "full ship, closeups, exploded, interface, plates"],
            ["Documentation", "4 PDFs + Markdown", "drawings, printing, plan, glue sequence"],
            ["Validation", "Markdown + JSON QA", "FreeCAD/BOP, STEP, STL, 3MF, interference, Bambu, SHA-256"],
        ], widths=[1.25 * inch, 2.55 * inch, 2.90 * inch]),
        Paragraph("Release gate", styles["HeadM4"]),
        Paragraph("Milestone 4 may be committed and pushed only after all required artifacts physically exist; all geometry, topology, interference, package, manifest, deterministic-rebuild, and Bambu Studio checks pass; and local main is clean and equal to origin/main. A physical coupon remains a separate real-world gate.", styles["BodyM4"]),
        PageBreak(), Paragraph("Change control and handoff", styles["TitleM4"]),
        fitted_image(RENDER / "CVN69_Hull_Deck_Island_Weapons_Stern_Isometric.png", 7.05 * inch, 3.45 * inch),
        bullet("All Milestone 4 work is isolated under Project/WeaponsDeckEdge/. Approved Milestone 1–3 hashes are captured and rechecked."),
        bullet("The integrated hull/deck/island/weapons STEP and 3MF are non-production review assemblies. Baseline production files are not duplicated."),
        bullet("No v1.0 tag is created and the complete ship is not marked production validated."),
        Paragraph(f"Configured production parts: {manifest['counts']['production_parts']}; weapon installations: {manifest['counts']['weapon_installations']}; frozen period: {manifest['configuration_period']}.", styles["BodyM4"]),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_coupon(output):
    doc = SimpleDocTemplate(str(output), pagesize=letter, rightMargin=0.50 * inch, leftMargin=0.50 * inch, topMargin=0.45 * inch, bottomMargin=0.56 * inch, title="CVN-69 Weapon Mount Coupon Instructions", author="yh598")
    story = [
        Paragraph("CVN-69 Weapon Mount Interface Coupon", styles["TitleM4"]),
        Paragraph("PRINT / FIT / GLUE TEST · RUN BEFORE PRODUCTION FOUNDATIONS", styles["SubM4"]),
        fitted_image(RENDER / "Weapon_Interface_Family_Section.png", 7.1 * inch, 3.8 * inch),
        table([
            ["Feature", "Actual production value"],
            ["Male feature", "4.00 × 5.00 mm asymmetric chamfered key"],
            ["Female clearance", "0.25 mm per side"],
            ["Seating depth", "1.20 mm"],
            ["Remaining skin", "1.20 mm"],
            ["Glue channel", "0.60 mm wide × 0.35 mm deep; open"],
            ["Coupon envelope", "48 × 24 × 4.20 mm per piece; under 60 × 60 × 25 mm"],
        ], widths=[2.35 * inch, 4.35 * inch]),
        Paragraph("Procedure", styles["HeadM4"]),
        bullet("Print both named objects at 100% with the exact planned production process."),
        bullet("Remove brim without filing the nominal mating walls. Dry-fit by hand; do not force or reverse."),
        bullet("Pass when broad faces seat completely, the fit does not rock, and no wall cracks or whitens."),
        bullet("Apply a small amount of medium CA through the open channel, seat fully, cure, and record the result."),
        bullet("If it fails, correct printer calibration or slicer compensation and repeat. Never scale production files."),
        PageBreak(), Paragraph("Acceptance record", styles["TitleM4"]),
        table([
            ["Item", "Record"],
            ["Printer / nozzle", "____________________________________________"],
            ["PLA / layer height", "____________________________________________"],
            ["XY / elephant-foot compensation", "____________________________________________"],
            ["Dry seating result", "PASS / FAIL    measured error: __________ mm"],
            ["Lean / rocking", "PASS / FAIL    observed: ___________________"],
            ["CA glue result", "PASS / FAIL    cure time: __________________"],
            ["Operator / date", "____________________________________________"],
        ], widths=[2.35 * inch, 4.35 * inch]),
        Spacer(1, 0.18 * inch), Paragraph("Automated geometry and slicer validation does not replace this physical first-article coupon.", styles["BodyM4"]),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def update_manifest(paths):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for path in paths:
        manifest["outputs"][str(path.relative_to(M4))] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    mapping = DOCS / "Weapons_DeckEdge_Material_Mapping.csv"
    with mapping.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["object_name", "material"])
        for name, material in sorted(manifest["material_mapping"].items()):
            writer.writerow([name, material])
    outputs = [
        DOCS / "Weapons_DeckEdge_Drawings.pdf",
        DOCS / "Weapons_DeckEdge_Printing_Guide.pdf",
        DOCS / "Weapons_DeckEdge_Project_Plan.pdf",
        DOCS / "Weapon_Mount_Coupon_Instructions.pdf",
    ]
    build_drawings(manifest, outputs[0])
    build_printing_guide(manifest, outputs[1])
    build_project_plan(manifest, outputs[2])
    build_coupon(outputs[3])
    source_files = [
        M4 / "README.md",
        M4 / "Assembly" / "Glue_Only_Weapons_Assembly.md",
        M4 / "References" / "Configuration_Audit.md",
        M4 / "QA" / "Reference_Confidence_Report.md",
        M4 / "QA" / "Material_Map.md",
        M4 / "CAD" / "Python" / "weapons_deckedge_parameters.py",
        *sorted((M4 / "Scripts").glob("*.py")),
    ]
    update_manifest([*outputs, mapping, *source_files])
    print(json.dumps({"status": "ok", "outputs": [str(path.relative_to(M4)) for path in outputs]}, indent=2))


if __name__ == "__main__":
    main()
