#!/usr/bin/env python3
"""Generate deterministic M6 PDFs, guides, schedules, and final manifest."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from reportlab import rl_config
rl_config.invariant=1
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter,landscape
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image


SCRIPT=Path(__file__).resolve();ROOT=SCRIPT.parents[3];M6=SCRIPT.parents[1];DOCS=M6/"Docs";QA=M6/"QA";DOCS.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(M6/"CAD/Python"));from deck_vehicle_parameters import make_parameters  # noqa:E402
P=make_parameters();styles=getSampleStyleSheet();styles.add(ParagraphStyle(name="M6Title",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=18,leading=21,textColor=colors.HexColor("#20272A"),spaceAfter=12));styles.add(ParagraphStyle(name="M6H",parent=styles["Heading2"],fontName="Helvetica-Bold",fontSize=11,textColor=colors.HexColor("#39474E"),spaceBefore=8,spaceAfter=5));styles.add(ParagraphStyle(name="M6Body",parent=styles["BodyText"],fontSize=8.5,leading=11,textColor=colors.HexColor("#263238"),spaceAfter=5));styles.add(ParagraphStyle(name="M6Small",parent=styles["BodyText"],fontSize=7.1,leading=8.8,textColor=colors.HexColor("#4B565B")))


def ptext(text,style="M6Body"):return Paragraph(str(text),styles[style])
def bullet(text):return Paragraph("• "+text,styles["M6Body"])
def table(rows,widths=None):
    result=Table([[ptext(cell,"M6Small") for cell in row] for row in rows],colWidths=widths,repeatRows=1);result.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#39474E")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#A8AFB1")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]));return result


def footer(canvas,doc):
    canvas.saveState();canvas.setFont("Helvetica",7);canvas.setFillColor(colors.HexColor("#657177"));canvas.drawString(.55*inch,.35*inch,"CVN-69 Museum Edition · Milestone 6 review · 1:700 · build 2026-07-14");canvas.drawRightString(doc.pagesize[0]-.55*inch,.35*inch,f"page {doc.page}");canvas.restoreState()


def build_pdf(path,story,pagesize=letter):
    doc=SimpleDocTemplate(str(path),pagesize=pagesize,rightMargin=.55*inch,leftMargin=.55*inch,topMargin=.52*inch,bottomMargin=.52*inch,title=path.stem,author="CVN-69 Museum Edition");doc.build(story,onFirstPage=footer,onLaterPages=footer)


def drawings():
    rows=[["Family","Public full-scale envelope","Released 1:700 FDM envelope","Accuracy boundary"]]
    for item in P.families:rows.append([f"{item.code}<br/>{item.name}",f"{item.full_length_mm:.0f} × {item.full_width_mm:.0f} × {item.full_height_mm:.0f} mm",f"{item.model_length:.3f} × {item.model_width:.3f} × {item.model_height:.3f} mm",item.classification])
    story=[ptext("CVN-69 Milestone 6 — Deck Vehicle Drawings","M6Title"),ptext("Equipment dimensions and released manufacturing envelopes","M6H"),table(rows,[1.35*inch,1.35*inch,1.35*inch,3.0*inch]),PageBreak(),ptext("Manufacturing sections and part breakdown","M6H"),table([["Feature","Released minimum","Use"],["structural wall / body section","0.80 / 1.00 mm","solid static bodies"],["wheel","1.00 mm diameter × 0.70 mm width","black glue-on insert"],["axle / tow bar","0.80 mm","bed-connected support / yellow gear"],["handle / post","0.70 mm","static FDM enlargement"],["ladder / hose","0.60 mm","flat-backed ladder / reel"],["raised detail","0.50 × 0.30 mm","minimum visible relief"],["color insert","0.60 mm","window, wheel, turret/reel modules"]],[2.1*inch,1.5*inch,3.25*inch]),Spacer(1,.12*inch),ptext("Print orientation and sprues","M6H"),bullet("Bodies and inserts use engineered z=0 faces. Wheel inserts use bed-connected underbody rails and four distinct end wheels."),bullet("The maintenance ladder prints flat on its back. The tow-bar and chock sprues use 0.80 mm family-only gates on non-visible surfaces."),bullet("All multi-part interfaces are glue-only; the first-article coupon releases 0.20 mm clearance per side, independent of the frozen ship interface."),Spacer(1,.12*inch)]
    image=M6/"Render/Exploded_STT49.png"
    if image.exists():story.append(Image(str(image),width=6.7*inch,height=3.75*inch))
    build_pdf(DOCS/"Deck_Vehicles_Drawings.pdf",story,landscape(letter))


def printing_guide():
    bambu=json.loads((QA/"BambuStudio_Validation.json").read_text(encoding="utf-8"));rows=[["Plate","Objects","0.12 / 0.16 mm"]]
    for path in sorted((M6/"3MF").glob("Print_Plate_*.3mf")):
        rec=[r for r in bambu["slice_records"] if r["plate"].endswith(path.name)];rows.append([path.name,str(len(rec[0]["expected_named_objects"])) if rec else "—"," / ".join(r["status"] for r in rec)])
    story=[ptext("CVN-69 Milestone 6 — Printing Guide","M6Title"),ptext("Validated process","M6H"),bullet("Primary printer: Bambu Lab P2S. Also suitable for X1C, P1S, A1, and individual compact plates on A1 Mini where practical."),bullet("PLA, 0.40 mm nozzle, three walls, 0.12 mm preferred layer; 0.16 mm is independently real-sliced."),bullet("Print at 100%. Do not reduce the released 0.60–1.10 mm FDM-safe features."),bullet("Assign materials by object name. No fixed AMS slot is required."),ptext("Production plates","M6H"),table(rows,[3.7*inch,1.0*inch,1.4*inch]),ptext("Acceptance","M6H"),bullet("Reject missing wheels, handles, ladder rungs, tow-bar forks, chocks, bottles, hose reel, turret/nozzle, or alignment-coupon edges."),bullet("The validated command-line runs produced zero floating-region, empty-layer, and faulty-mesh warnings at both layer heights."),bullet("Supports were not needed. Add only a local brim if the calibrated printer requires more adhesion.")]
    build_pdf(DOCS/"Deck_Vehicles_Printing_Guide.pdf",story)


def project_plan():
    story=[ptext("CVN-69 Milestone 6 — Project Plan and Accuracy Boundary","M6Title"),ptext("Completed objective","M6H"),ptext("Reconstruct audit-supported flight-deck vehicles and aviation support equipment as reusable parametric FreeCAD/OpenCascade families, provide glue-only/no-paint manufacturing outputs, and coordinate static layouts with approved Milestones 1–5."),ptext("Delivered work packages","M6H"),table([["Package","Result"],["Reference audit","Seven supported families; uncertain equipment explicitly omitted"],["CAD","16 production solids; two editable FCStd sources"],["Layouts","light 14 / default 24 / full 32 support instances"],["QA","BRep, STEP, STL, 3MF, dimensions, immutable hashes, exact interference, deterministic rebuild, Bambu real slices"],["Review","Approved ship + AirWing + vehicles in non-production STEP/3MF"]],[1.45*inch,4.95*inch]),ptext("Accuracy categories","M6H"),bullet("Manufacturer/official dimension-derived: STT49, P-25A and MSU module envelopes."),bullet("Official-photo-derived and visually approximated: tow bar, ladder, chocks, exterior silhouettes and support placement."),bullet("Deliberately enlarged: every sub-nozzle wheel, rail, rung, hose, handle, tow bar, bottle and sprue section listed in FDM_Enlargements.json."),bullet("No claim is made to controlled lofts, proprietary drawings, exact deployed parking coordinates, functional mechanisms, or a single photographed operational moment."),ptext("Scope stop","M6H"),ptext("No ocean base, display stand, final assembly release, lighting, electronics, crew, weapons/ammunition, hull/deck/interface redesign, or Milestone 5 physical-pass claim is included.")]
    build_pdf(DOCS/"Deck_Vehicles_Project_Plan.pdf",story)


def first_article():
    image=M6/"Render/Print_Plate_00_First_Article.png";story=[ptext("Deck Vehicles First-Article Instructions","M6Title"),ptext("Plate: Print_Plate_00_First_Article.3mf · envelope ≤120 × 120 mm","M6H")]
    if image.exists():story += [Image(str(image),width=6.55*inch,height=3.7*inch),Spacer(1,.08*inch)]
    story += [ptext("Print","M6H"),bullet("100% scale; 0.40 mm nozzle; PLA; three walls; 0.12 mm preferred layer. Record printer, filament, XY and elephant-foot compensation."),bullet("A single-material geometry test is acceptable before no-paint color production. No supports are expected."),ptext("Physical evaluation checklist","M6H"),table([["Check","Acceptance / recorded result"],["Tow tractor","four wheels visible; body and dark insert complete"],["Service cart","body, wheels and equipment envelope retained"],["Tow bar / sprue","forks present; 0.80 mm gates clip cleanly"],["Maintenance ladder","all five rungs retained; flat print releases without curl"],["Chocks / extinguishers","paired wedges, bottles, handle and wheels present"],["Alignment coupon","male/female assemble by hand at 0.20 mm per side; no force or cracking"],["Layers / warnings","continuous at 0.12 and 0.16 mm; no slicer warnings"],["Physical status","PASS / FAIL / NOT RUN; date, operator and notes"]],[2.15*inch,4.2*inch]),ptext("Repository gate","M6H"),ptext("Automated geometry and slicer validation does not equal a physical pass. The repository remains NOT RUN until the user reports the completed print and settings.")]
    build_pdf(DOCS/"Deck_Vehicles_First_Article_Instructions.pdf",story)


def layout_guide():
    image=M6/"Render/Layout_Default_Combined.png";story=[ptext("CVN-69 Milestone 6 — Deck Equipment Layout Guide","M6Title"),ptext("Coordinate system","M6H"),ptext("x = 0 bow to x = 476 stern; y port negative / starboard positive; z uses the approved hull datum with deck top at 34.50 mm; heading is clockwise from +x."),table([["JSON","Support count","Coordinated AirWing"],["light_support_layout.json","14","light_deck_layout.json (16 aircraft)"],["default_support_layout.json","24","default_deployment_layout.json (32 aircraft)"],["full_support_layout.json","32","full_deck_layout.json (36 aircraft)"]],[3.0*inch,1.0*inch,2.4*inch])]
    if image.exists():story += [Spacer(1,.1*inch),Image(str(image),width=6.65*inch,height=2.25*inch)]
    story += [ptext("Required entry fields","M6H"),ptext("equipment family, variant, instance ID, x/y/z, heading, material, intended aircraft relationship, confidence/display rationale, state, source, and intentional linkage metadata."),ptext("Editing rules","M6H"),bullet("Re-run the layout builder and validator after any change. The 0.10 mm³ gate covers deck boundary, island, defensive systems, elevators, catapults, wires, markings, seams, aircraft, and neighboring support equipment."),bullet("A towing or servicing state requires explicit aircraft linkage metadata. The released layouts declare only independent parked/staged/stored/firefighting objects."),bullet("Integrated STEP/3MF files are review assemblies, not print plates. Print from family plates or individual STLs.")]
    build_pdf(DOCS/"Deck_Equipment_Layout_Guide.pdf",story)


def markdown_and_schedules():
    manifest=json.loads((QA/"build_manifest.json").read_text(encoding="utf-8"));materials={part["name"]:part["material"] for part in manifest["parts"]}
    (QA/"Part_Material_Assignments.json").write_text(json.dumps(materials,indent=2)+"\n",encoding="utf-8")
    ref={item.code:{"name":item.name,"evidence_url":item.evidence_url,"dimension_url":item.dimension_url,"confidence":item.confidence,"classification":item.classification} for item in P.families};(QA/"Reference_Confidence_Report.json").write_text(json.dumps(ref,indent=2)+"\n",encoding="utf-8")
    placements={name:json.loads((M6/"Layout"/filename).read_text(encoding="utf-8")) for name,filename in {"light":"light_support_layout.json","default":"default_support_layout.json","full":"full_support_layout.json"}.items()};(QA/"Layout_Placement.json").write_text(json.dumps(placements,indent=2)+"\n",encoding="utf-8")
    (QA/"Physical_First_Article_Status.json").write_text(json.dumps({"milestone":6,"status":"NOT_RUN","physical_print_reported":False,"automated_geometry_status":"PASS","bambu_real_slice_status":"PASS","airwing_milestone_5_physical_status":"NOT_RUN"},indent=2)+"\n",encoding="utf-8")
    (M6/"README.md").write_text("""# Milestone 6 — Flight-deck vehicles and aviation support equipment

Seven audit-supported families are reconstructed as new parametric FreeCAD/OpenCascade geometry at 1:700. Source meshes are not imported. The approved 476 mm ship baseline and frozen 0.25 mm-per-side hull/deck interface are unchanged.

Released production: 16 named solids, 7 non-empty family/first-article plates, 14/24/32 configurable support layouts, two editable FCStd sources, STEP/STL/3MF/OBJ, 45 neutral renders, five PDFs, exact interference QA, and real Bambu Studio slices at 0.12 and 0.16 mm.

Primary process: Bambu P2S, PLA, 0.4 mm nozzle, 0.12 mm layers, three walls. X1C/P1S/A1 are supported; compact individual plates are practical on A1 Mini. Assign available filament by object name; no AMS slot is fixed.

Accuracy boundary: official public dimensions are used where available. Photo-derived silhouettes and every FDM enlargement are labeled; enlarged details are not dimensionally exact. The layout is representative, not a claim to reproduce one dated photograph.

Physical first article: **NOT RUN**. Milestone 5 AirWing first article also remains **NOT RUN**. See `Docs/Deck_Vehicles_First_Article_Instructions.pdf`.

Deterministic rebuild from repository root:

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c "globals()['__file__']='Project/DeckVehicles/Scripts/build_deck_vehicles.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c "globals()['__file__']='Project/DeckVehicles/Scripts/build_deck_equipment_layout.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
```

Scope stops here: no ocean base, final release, lighting/electronics, crew, weapons/ammunition, or approved M1–M5 redesign.
""",encoding="utf-8")
    (M6/"Assembly/Glue_Only_Deck_Vehicle_Assembly.md").write_text("""# Glue-only deck-vehicle assembly

Print at 100%. Dry-fit and identify objects by name before applying adhesive. Use a small amount of PLA-compatible adhesive on hidden mating faces.

- STT49: seat the black wheel/underbody insert beneath the gold body, then glue the charcoal window insert to the cabin.
- P-25A: seat the black wheel insert beneath the gold body; glue the silver turret/nozzle at the documented roof position.
- MSU-200NAV cart: seat the black wheel insert below; glue the silver reel to the cart side.
- Extinguisher group: seat the black wheel insert under the red cart.
- Ladder, tow bar and chocks: one-piece static parts. Clip family sprues at the 0.80 mm non-visible gates and dress the cut flush.

Nominal small-part clearance is 0.20 mm per side. Do not sand the frozen ship interface and do not scale parts to force a fit. The maintenance ladder is intentionally flat-backed and may be glued leaning against a display aircraft only after layout review; supplied layouts keep it independently stored.
""",encoding="utf-8")
    (QA/"Reference_Confidence_Report.md").write_text("# Milestone 6 reference confidence\n\n| Family | Confidence | Classification |\n|---|---|---|\n"+"\n".join(f"| {item.code} | {item.confidence} | {item.classification} |" for item in P.families)+"\n\nSee `References/Configuration_Audit.md` for dated URLs, omissions, inference boundaries and the deployment-period anchor.\n",encoding="utf-8")
    (QA/"Material_Map.md").write_text("""# Milestone 6 material map

| Material | Named-object use |
|---|---|
| Bambu PLA Basic Gold | tractors, P-25A exterior, tow bars, ladders, chocks |
| Bambu PLA Basic Black | wheel/underbody inserts |
| Bambu PLA Matte Charcoal | tractor window insert |
| Bambu PLA Translucent Red | portable extinguisher group |
| Bambu PLA Matte Ash Gray | MSU-200NAV service cart body |
| Bambu PLA Silk Silver | P-25A turret/nozzle and MSU hose reel |

Ivory White and Marine Blue remain allowed but are not required by released M6 production objects. No AMS slot numbers are assigned.
""",encoding="utf-8")
    (QA/"Physical_First_Article_Status.md").write_text("""# Deck-vehicle physical first-article status

Status: **NOT RUN**

Automated BRep, STEP, STL, 3MF, interference, deterministic-rebuild, and Bambu real-slice gates are tracked separately. No physical print result has been reported for `3MF/Print_Plate_00_First_Article.3mf`.

Milestone 5 AirWing first article: **NOT RUN**. The hull production physical status is not changed by Milestone 6.
""",encoding="utf-8")
    (M6/"Images/README.md").write_text("# Milestone 6 source imagery\n\nNo external photograph is redistributed. Public-domain/official source URLs and captions are recorded in `References/Configuration_Audit.md`; generated renders are in `Render/`.\n",encoding="utf-8")


def sha256(path):
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()


def finalize_manifest():
    path=QA/"build_manifest.json";manifest=json.loads(path.read_text(encoding="utf-8"));status_files={"reference_audit":"Reference_Audit.json","geometry_mesh_layout":"Validation_Summary.json","deterministic_rebuild":"Deterministic_Rebuild.json","bambu_real_slice":"BambuStudio_Validation.json"};validation={}
    for key,filename in status_files.items():
        item=QA/filename;validation[key]=json.loads(item.read_text(encoding="utf-8")).get("overall_status","NOT_RUN") if item.exists() else "NOT_RUN"
    validation["physical_first_article"]="NOT_RUN";validation["airwing_physical_first_article"]="NOT_RUN";manifest["validation_status"]=validation
    include_roots={"CAD","Scripts","STEP","STL","3MF","OBJ","Render","Images","Layout","Assembly","Docs","References"};files=[]
    for item in sorted(M6.rglob("*")):
        if not item.is_file() or item==path or "__pycache__" in item.parts or item.suffix in {".pyc",".FCBak"}:continue
        relative=item.relative_to(M6)
        if relative.parts[0] in include_roots or relative.name=="README.md":files.append(item)
    manifest["counts"].update({"stl_files":len(list((M6/"STL").glob("*.stl"))),"three_mf_packages":len(list((M6/"3MF").glob("*.3mf"))),"step_files":len(list((M6/"STEP").glob("*.step"))),"renders":len(list((M6/"Render").glob("*.png"))),"pdf_documents":len(list((M6/"Docs").glob("*.pdf"))),"layout_counts":{name:len(json.loads((M6/"Layout"/filename).read_text(encoding="utf-8"))["entries"]) for name,filename in {"light":"light_support_layout.json","default":"default_support_layout.json","full":"full_support_layout.json"}.items()}})
    manifest["outputs"]={str(item.relative_to(M6)):{"bytes":item.stat().st_size,"sha256":sha256(item)} for item in files};manifest["output_file_count"]=len(files);path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")


def main():
    drawings();printing_guide();project_plan();first_article();layout_guide();markdown_and_schedules();finalize_manifest();print(json.dumps({"status":"ok","pdf_documents":sorted(path.name for path in DOCS.glob("*.pdf")),"manifest_outputs":json.loads((QA/"build_manifest.json").read_text(encoding="utf-8"))["output_file_count"]},indent=2))


if __name__=="__main__":main()
