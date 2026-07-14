# CVN-69 Milestone 4 — Defensive Systems and Deck-Edge Equipment

This directory contains a clean parametric reconstruction of the publicly visible defensive systems and major deck-edge equipment for the 2023-10-14 through 2024-07-14 deployment fit. The supplied STL package is a reference only; no source triangle is imported by the production builder.

## Scope and status

- 43 named production objects: 6 additive platforms/sponsons, 6 defensive installations broken into printable subparts, 6 life-raft groups, one generic utility-boat set, and selected major railings, ladders, lights, and lockers.
- Frozen defensive fit: 2 Mk 15 Phalanx CIWS, 2 Mk 49 RAM, and 2 Mk 29 Sea Sparrow/ESSM installations.
- One common two-part physical interface coupon reproduces the actual 0.25 mm-per-side asymmetric key, 1.20 mm seating depth, 1.20 mm remaining platform skin, and open glue channel.
- All geometry is new parametric BRep construction. Approved Milestones 1–3 are immutable inputs.
- This is a review milestone, not a final full-ship release. Aircraft, vehicles, aircraft weapons, internal mechanisms, ocean base, display stand, electronics, and later milestones remain out of scope.

The public evidence and uncertainty labels are in `References/Configuration_Audit.md`. Photo-derived geometry is not described as shipyard-accurate; FDM-enlarged features are explicitly identified.

## Rebuild from the repository root

```sh
python3 Project/WeaponsDeckEdge/Scripts/audit_weapons_references.py
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "globals()['__file__']='Project/WeaponsDeckEdge/Scripts/build_weapons_deckedge.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
python3 Project/WeaponsDeckEdge/Scripts/render_weapons_deckedge.py
/Users/Yun.Hu@blueshieldca.com/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 Project/WeaponsDeckEdge/Scripts/generate_weapons_documents.py
python3 Project/WeaponsDeckEdge/Scripts/run_bambu_weapons_checks.py
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "globals()['__file__']='Project/WeaponsDeckEdge/Scripts/validate_weapons_deckedge.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
```

## Print assumptions

- Bambu Lab P2S primary; X1C, P1S, and A1 supported. Individual objects fit an A1 Mini where practical.
- PLA, 0.4 mm nozzle.
- 0.16 mm layers for platforms, boat, and larger structures; 0.12 mm for weapons and fine details.
- Minimum structural wall 1.20 mm; minimum fragile diameter 0.80 mm; preferred barrel 1.00 mm; raised detail 0.50 mm wide × 0.35 mm high; railing/ladder 0.60 mm minimum.
- CA glue only. No magnets, screws, threaded inserts, heat-set inserts, metal pins, purchased connectors, or electronics.
- Material names are object-level assignments and never fixed AMS slot numbers.

See `Assembly/Glue_Only_Weapons_Assembly.md`, `Docs/Weapons_DeckEdge_Printing_Guide.pdf`, and the QA reports before printing.

## Major deliverables

- Editable FreeCAD: `CAD/FreeCAD/CVN69_Weapons_DeckEdge.FCStd`
- Production assembly: STEP, OBJ, and named-object 3MF
- One print-oriented STL per production/coupon object
- Four named-object print plates and one coupon 3MF
- Integrated hull/deck/island/weapons STEP and 3MF review model
- Nineteen neutral renders, four PDFs, dimensional/topology/interference/reference/Bambu reports, and a SHA-256 manifest

The integrated review 3MF is not a print plate and may exceed a printer bed.
