#!/usr/bin/env python3
"""Generate deterministic Milestone 5 PDFs and machine-readable schedules."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from reportlab import rl_config
rl_config.invariant = 1
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
M5 = SCRIPT.parents[1]
DOCS = M5 / "Docs"
DOCS.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(M5 / "CAD" / "Python"))
from airwing_parameters import make_parameters  # noqa: E402


P = make_parameters()
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="M5Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=21, textColor=colors.HexColor("#20272A"), spaceAfter=12))
styles.add(ParagraphStyle(name="M5H", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#39474E"), spaceBefore=8, spaceAfter=5))
styles.add(ParagraphStyle(name="M5Body", parent=styles["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#263238"), spaceAfter=5))
styles.add(ParagraphStyle(name="M5Small", parent=styles["BodyText"], fontSize=7.2, leading=9, textColor=colors.HexColor("#4B565B")))
styles.add(ParagraphStyle(name="M5Center", parent=styles["M5Small"], alignment=TA_CENTER))


def PText(text, style="M5Body"):
    return Paragraph(text, styles[style])


def bullet(text):
    return Paragraph("• " + text, styles["M5Body"])


def table(rows, widths=None):
    result = Table([[PText(str(cell), "M5Small") for cell in row] for row in rows], colWidths=widths, repeatRows=1)
    result.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#39474E")), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#A8AFB1")),
        ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return result


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#657177"))
    canvas.drawString(0.55*inch, 0.35*inch, "CVN-69 Museum Edition · Milestone 5 review · 1:700 · build 2026-07-14")
    canvas.drawRightString(doc.pagesize[0]-0.55*inch, 0.35*inch, f"page {doc.page}")
    canvas.restoreState()


def build_pdf(path, story, pagesize=letter):
    doc = SimpleDocTemplate(str(path), pagesize=pagesize, rightMargin=0.55*inch, leftMargin=0.55*inch, topMargin=0.52*inch, bottomMargin=0.52*inch, title=path.stem, author="CVN-69 Museum Edition")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def drawings():
    rows = [["Type / squadron", "Official full scale", "1:700 envelope", "Production variants"]]
    for item in P.aircraft_types:
        extra = f"; rotor {item.rotor_diameter:.3f} mm" if item.rotor_diameter else (f"; dome {item.dome_diameter:.3f} mm" if item.dome_diameter else "")
        rows.append([f"{item.name}<br/>{item.squadron}", f"L {item.full_length_m:.3f} m<br/>span {item.full_span_m:.3f} m", f"L {item.model_length:.3f} × span {item.model_span:.3f} mm{extra}", ", ".join(item.variants)])
    image = M5 / "Render" / "Fixed_Wing_Variant_Comparison.png"
    story = [PText("CVN-69 Milestone 5 — Air-Wing Drawings", "M5Title"), PText("Dimensioned production-envelope schedule", "M5H"), table(rows, [1.55*inch, 1.35*inch, 1.65*inch, 1.55*inch]), Spacer(1, 0.12*inch)]
    if image.exists(): story += [Image(str(image), width=6.7*inch, height=3.7*inch)]
    story += [PText("Manufacturing sections", "M5H"), table([
        ["Feature", "Released size", "Classification"], ["wing / stabilizer", "0.70 mm", "FDM-enlarged"],
        ["landing support", "0.80 mm minimum", "FDM-enlarged"], ["rotor blade", "0.70 × 0.60 mm", "FDM-enlarged"],
        ["fin / insert", "0.60 mm", "FDM minimum"], ["raised identity", "0.50 × 0.30 mm", "neutral unit tile; not insignia art"],
    ], [2.0*inch, 1.4*inch, 2.9*inch])]
    build_pdf(DOCS / "AirWing_Drawings.pdf", story, landscape(letter))


def printing_guide():
    plate_rows = [["Plate", "Objects", "Use"]]
    for path in sorted((M5 / "3MF").glob("Print_Plate_*.3mf")):
        plate_rows.append([path.name, "named/material objects", "first article" if "00_" in path.name else "type family"])
    story = [PText("CVN-69 Milestone 5 — Printing Guide", "M5Title"), PText("Validated process", "M5H"),
             bullet("Primary: Bambu P2S, 0.40 mm nozzle; compatible with X1C, P1S, A1, and these compact type plates are practical on A1 mini."),
             bullet("Preferred 0.12 mm layer; 0.16 mm independently sliced as the second validation gate; three walls."),
             bullet("Use Basic Blue Grey for bodies, Charcoal for canopy inserts, Ivory for rotodome/identity inserts, and Silver for rotors/details."),
             bullet("Body STLs and type plates include 0.80 mm removable belly/engine rails only in print geometry. Clip and sand these rails after cooling; the clean assembly BRep/STEP remains unchanged."),
             bullet("Do not scale. Do not reduce the 0.60–0.80 mm nozzle-safe features."), PText("Production plates", "M5H"), table(plate_rows, [3.6*inch, 1.4*inch, 1.2*inch]),
             PText("Quality checks", "M5H"), bullet("Reject any part with a missing blade, broken folded wing, incomplete tail, or canopy/rotodome seat damage."),
             bullet("Use a 3–5 mm brim only if local adhesion requires it; no support generation was needed in the validated command-line slices."),
             bullet("Bambu Studio produced 20 successful real slices with zero floating-region, empty-layer, and faulty-mesh warnings.")]
    build_pdf(DOCS / "AirWing_Printing_Guide.pdf", story)


def project_plan():
    story = [PText("CVN-69 Milestone 5 — Project Plan and Accuracy Boundary", "M5Title"), PText("Completed objective", "M5H"),
             PText("Reconstruct the confirmed 2023-10-14 through 2024-07-14 CVW-3 type set as new parametric FreeCAD/OpenCascade geometry, export print and review formats, and integrate layouts without changing approved Milestones 1–4."),
             PText("Work packages", "M5H"), table([
                 ["Package", "Result"], ["Configuration audit", "Nine confirmed units/types; E-2C modeled and E-2D explicitly excluded"],
                 ["CAD", "48 production objects; 25 major body variants"], ["Layouts", "light 16 / default 32 / full folded 36"],
                 ["QA", "BRep, STEP, STL, 3MF, dimensions, interference, hashes, deterministic rebuild, Bambu real slices"],
                 ["Documentation", "drawings, printing, project plan, first article, layout guide, assembly instructions"],
             ], [1.55*inch, 4.75*inch]), PText("Accuracy boundary", "M5H"),
             bullet("Official-source-derived: embarked units, aircraft types, overall length/span/rotor/dome dimensions."),
             bullet("Photo-informed: major family silhouettes, folding states, canopy count, Growler pod/E-2C dome/C-2 cargo/helicopter distinctions."),
             bullet("Engineering representation: folded envelopes, neutral identity tiles, print supports, exact deck parking coordinates, and nozzle-safe thickness."),
             bullet("No claim is made to controlled lofts, bureau numbers, exact insignia art, weapons loads, or shipyard parking plans."),
             PText("Scope stop", "M5H"), PText("No hull, deck, interface, island, weapon, vehicle, ocean-base, lighting/electronics, or release-tag work is included. Physical first-article printing remains the next real-world gate.")]
    build_pdf(DOCS / "AirWing_Project_Plan.pdf", story)


def first_article():
    image = M5 / "Render" / "Print_Plate_00_First_Article.png"
    story = [PText("Air-Wing First-Article Instructions", "M5Title"), PText("Plate: Print_Plate_00_First_Article.3mf · packed envelope ≤120 × 120 mm", "M5H")]
    if image.exists(): story += [Image(str(image), width=6.7*inch, height=6.7*inch), Spacer(1, 0.08*inch)]
    story += [PText("Print", "M5H"), bullet("Print at 100% with a 0.40 mm nozzle, 0.12 mm preferred layer, three walls, zero XY compensation unless your calibrated process requires otherwise."),
              bullet("Assign materials by object name; a single-material geometry test is acceptable before color production."),
              PText("Inspect and record", "M5H"), table([
                  ["Check", "Acceptance"], ["Spread/folded/launch bodies", "all wings, fins, nacelles and gear/support features complete"],
                  ["Hawkeye/COD", "propeller crosses complete; rotodome flat and round"], ["MH-60", "all deployed/folded rotor blades present"],
                  ["Support removal", "rails detach without tearing the 0.70 mm flight surfaces"], ["Glue fit", "canopies/dome/rotors seat by hand; no scaling"],
              ], [2.2*inch, 4.1*inch]), PText("Gate", "M5H"), PText("This PDF defines the physical review procedure; the repository records only automated geometry/slicer PASS until a dated physical result is supplied.")]
    build_pdf(DOCS / "AirWing_First_Article_Instructions.pdf", story)


def layout_guide():
    image = M5 / "Render" / "Layout_Default_32.png"
    story = [PText("CVN-69 Milestone 5 — Layout Guide", "M5Title"), PText("Coordinate system", "M5H"),
             PText("x = 0 bow to x = 476 stern; y is port negative and starboard positive; z uses the approved keel datum with the deck top at z = 34.50 mm; heading is clockwise from +x."),
             PText("Provided layouts", "M5H"), table([
                 ["JSON", "Count", "Purpose"], ["light_deck_layout.json", "16", "open-deck visual review"],
                 ["default_deployment_layout.json", "32", "integrated review and principal renders"],
                 ["full_deck_layout.json", "36", "dense folded-wing display at the valid lower target bound"],
             ], [3.0*inch, 0.7*inch, 2.6*inch])]
    if image.exists(): story += [Spacer(1, 0.10*inch), Image(str(image), width=6.7*inch, height=2.45*inch)]
    story += [PText("Editing rules", "M5H"), bullet("Keep every required field: type, variant, squadron, x/y/z, heading, material, source, confidence."),
              bullet("Maintain at least 0.20 mm clearance per aircraft side (0.40 mm object-to-object AABB clearance in the supplied layouts)."),
              bullet("Re-run the layout builder and validator after any coordinate change; the exact 0.10 mm³ common-volume gate includes deck boundary, island, weapons, elevators, catapults, arresting wires, markings, and neighboring aircraft."),
              bullet("The integrated 3MF/STEP are non-production geometry reviews; print aircraft from the type plates or individual STLs.")]
    build_pdf(DOCS / "AirWing_Layout_Guide.pdf", story)


def schedules():
    manifest = json.loads((M5 / "QA" / "build_manifest.json").read_text(encoding="utf-8"))
    assignments = {}
    for part in manifest["parts"]:
        assignments[part["name"]] = part["material"]
    (M5 / "QA" / "Part_Material_Assignments.json").write_text(json.dumps(assignments, indent=2) + "\n", encoding="utf-8")
    with (DOCS / "AirWing_Material_Mapping.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["object", "material"])
        writer.writerows(sorted(assignments.items()))
    lines = ["# Milestone 5 material map", "", "| Material | Use |", "|---|---|",
             "| Bambu PLA Basic Blue Grey | aircraft exterior bodies and removable support rails |",
             "| Bambu PLA Matte Charcoal | canopy inserts |", "| Bambu PLA Matte Ivory White | rotodome and neutral squadron identity inserts |",
             "| Bambu PLA Silk Silver | deployed/folded helicopter rotors |", "", "No additional production color is required."]
    (M5 / "QA" / "Material_Map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finalize_manifest():
    path = M5 / "QA" / "build_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    files = []
    for item in sorted(M5.rglob("*")):
        if not item.is_file() or item == path or "__pycache__" in item.parts or item.suffix in {".pyc", ".FCBak"}:
            continue
        files.append(item)
    manifest["validation_status"] = {
        "reference_audit": json.loads((M5 / "QA" / "Reference_Audit.json").read_text(encoding="utf-8"))["overall_status"],
        "geometry_mesh_layout": json.loads((M5 / "QA" / "Validation_Summary.json").read_text(encoding="utf-8"))["overall_status"],
        "deterministic_rebuild": json.loads((M5 / "QA" / "Deterministic_Rebuild.json").read_text(encoding="utf-8"))["overall_status"],
        "bambu_real_slice": json.loads((M5 / "QA" / "BambuStudio_Validation.json").read_text(encoding="utf-8"))["overall_status"],
        "physical_first_article": "NOT_RUN",
    }
    manifest["counts"].update({
        "stl_files": len(list((M5 / "STL").glob("*.stl"))),
        "three_mf_packages": len(list((M5 / "3MF").glob("*.3mf"))),
        "step_files": len(list((M5 / "STEP").glob("*.step"))),
        "renders": len(list((M5 / "Render").glob("*.png"))),
        "pdf_documents": len(list((M5 / "Docs").glob("*.pdf"))),
        "layout_counts": {name: len(json.loads((M5 / "Layout" / filename).read_text(encoding="utf-8"))["entries"]) for name, filename in {
            "light": "light_deck_layout.json", "default": "default_deployment_layout.json", "full": "full_deck_layout.json"}.items()},
    })
    manifest["outputs"] = {str(item.relative_to(M5)): {"bytes": item.stat().st_size, "sha256": sha256(item)} for item in files}
    manifest["output_file_count"] = len(files)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    drawings(); printing_guide(); project_plan(); first_article(); layout_guide(); schedules(); finalize_manifest()
    outputs = sorted(path.name for path in DOCS.glob("*"))
    print(json.dumps({"status": "ok", "documents": outputs}, indent=2))


if __name__ == "__main__":
    main()
