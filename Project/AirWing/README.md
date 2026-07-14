# CVN-69 Milestone 5 — Frozen-period carrier air wing

Milestone 5 reconstructs the confirmed Carrier Air Wing Three configuration from USS *Dwight D. Eisenhower*’s 14 October 2023 through 14 July 2024 deployment as new parametric FreeCAD/OpenCascade geometry. No source mesh is opened or reused. Approved Milestones 1–4 and the physically qualified 0.25 mm-per-side hull/deck interface remain unchanged.

## Configuration

Nine official-source-confirmed unit/type combinations are included: VFA-105 F/A-18E, VFA-32 F/A-18F, VFA-83 F/A-18E, VFA-131 F/A-18E, VAQ-130 EA-18G, VAW-123 E-2C, VRC-40 C-2A, HSM-74 MH-60R, and HSC-7 MH-60S. The frozen-period audit establishes that VAW-123 still operated the E-2C; E-2D is explicitly excluded.

The 48 production objects contain 25 body variants plus separate canopy, rotodome, rotor, and neutral squadron-ID inserts. Fixed-wing families have spread, folded, and launch/taxi variants. Helicopters have deployed- and folded-rotor variants.

## Manufacturing design

- 1:700; 0.40 mm nozzle; 0.12 mm preferred and 0.16 mm validated.
- 0.70 mm wings/stabilizers; 0.80 mm landing/support features; 0.70 × 0.60 mm rotor blades; 0.60 mm fins/inserts; 0.50 × 0.30 mm raised identity details.
- Body STL/3MF print versions include documented removable 0.80 mm belly/engine rails. Clean assembly BReps and STEP geometry do not contain those sacrificial rails.
- Four production materials only: Basic Blue Grey exterior, Charcoal canopies, Ivory dome/identity inserts, and Silver rotors/details.
- CA glue only; no magnets, metal pins, screws, or purchased connectors.

## Principal deliverables

| Deliverable | File |
|---|---|
| Editable aircraft master | [`CAD/FreeCAD/CVN69_AirWing_Master.FCStd`](CAD/FreeCAD/CVN69_AirWing_Master.FCStd) |
| Editable integrated layout | [`CAD/FreeCAD/CVN69_AirWing_Layout.FCStd`](CAD/FreeCAD/CVN69_AirWing_Layout.FCStd) |
| Master STEP | [`STEP/CVN69_AirWing_Master.step`](STEP/CVN69_AirWing_Master.step) |
| Integrated review STEP | [`STEP/CVN69_Hull_Deck_Island_Weapons_AirWing_Review.step`](STEP/CVN69_Hull_Deck_Island_Weapons_AirWing_Review.step) |
| Master 3MF | [`3MF/CVN69_AirWing_Master.3mf`](3MF/CVN69_AirWing_Master.3mf) |
| First article | [`3MF/Print_Plate_00_First_Article.3mf`](3MF/Print_Plate_00_First_Article.3mf) |
| Default layout 3MF | [`3MF/CVN69_AirWing_Default_Layout.3mf`](3MF/CVN69_AirWing_Default_Layout.3mf) |
| Default layout OBJ | [`OBJ/CVN69_AirWing_Default_Layout.obj`](OBJ/CVN69_AirWing_Default_Layout.obj) |
| Configuration audit | [`References/Configuration_Audit.md`](References/Configuration_Audit.md) |
| Drawings | [`Docs/AirWing_Drawings.pdf`](Docs/AirWing_Drawings.pdf) |
| Printing guide | [`Docs/AirWing_Printing_Guide.pdf`](Docs/AirWing_Printing_Guide.pdf) |
| First-article instructions | [`Docs/AirWing_First_Article_Instructions.pdf`](Docs/AirWing_First_Article_Instructions.pdf) |
| Layout guide | [`Docs/AirWing_Layout_Guide.pdf`](Docs/AirWing_Layout_Guide.pdf) |
| QA summary | [`QA/Validation_Summary.json`](QA/Validation_Summary.json) |
| Bambu real-slice report | [`QA/BambuStudio_Validation.md`](QA/BambuStudio_Validation.md) |
| Build manifest | [`QA/build_manifest.json`](QA/build_manifest.json) |

Individual production STLs are under `STL/`; nine family STEP files and ten actual-slice-validated production 3MF plates are supplied. Twenty-two neutral renders include full-ship, layout, family, variant, no-paint, and first-article views.

## Configurable layouts

- `Layout/light_deck_layout.json`: 16 aircraft.
- `Layout/default_deployment_layout.json`: 32 aircraft and the integrated review export.
- `Layout/full_deck_layout.json`: 36 folded-wing aircraft, the valid lower bound of the requested full-deck range.

Every record contains type, variant, squadron, x/y/z, heading, material, evidence source, and confidence. Coordinates use x = 0 bow to x = 476 stern, port y negative, starboard y positive, and the approved z = 34.50 mm deck-top datum. Exact BRep validation checks the traced boundary, island, weapons, elevators, catapults, arresting wires, markings, and every other aircraft at a 0.10 mm³ threshold.

## Validation status

- 48/48 STL objects: watertight/manifold, positive volume, consistent normals, zero boundary/non-manifold edges, zero degenerate triangles, and z=0 print contact.
- 13/13 3MF packages: valid ZIP/OPC/XML, unique named objects, valid triangle indices, build items, and material assignments.
- 12/12 STEP exports: valid re-import with closed solids; strict assembly-compound cross-object messages are retained separately from child-solid validity.
- Light/default/full layouts: PASS at 16/32/36 aircraft with ≥0.40 mm conservative object spacing and no overlap above 0.10 mm³.
- Bambu Studio 02.07.01.62: 61 STL/3MF import checks and 20 real production-plate slices at 0.12/0.16 mm all PASS with zero floating-region, empty-layer, or faulty-mesh warnings and no missing rotor objects.
- Approved input hashes: unchanged.

This is an automated geometry and slicer PASS, not a claim of physical first-article validation. No release tag is created.

## Rebuild

From the repository root:

```sh
python3 Project/AirWing/Scripts/audit_airwing_references.py
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "globals()['__file__']='Project/AirWing/Scripts/build_airwing.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "globals()['__file__']='Project/AirWing/Scripts/build_airwing_layout.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "globals()['__file__']='Project/AirWing/Scripts/validate_airwing.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
python3 Project/AirWing/Scripts/run_bambu_airwing_checks.py
python3 Project/AirWing/Scripts/render_airwing.py
```
