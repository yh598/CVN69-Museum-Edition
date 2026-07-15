# Milestone 6 — Flight-deck vehicles and aviation support equipment

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
