# Milestone 6 validation commands

Commands were run from the repository root on 14 July 2026.

```sh
python3 Project/DeckVehicles/Scripts/audit_deck_vehicle_references.py

/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c \
  "globals()['__file__']='Project/DeckVehicles/Scripts/build_deck_vehicles.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"

/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c \
  "globals()['__file__']='Project/DeckVehicles/Scripts/build_deck_equipment_layout.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"

CVN69_DETERMINISTIC_REBUILD=1 /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c \
  "globals()['__file__']='Project/DeckVehicles/Scripts/validate_deck_vehicles.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"

python3 Project/DeckVehicles/Scripts/run_bambu_deck_vehicle_checks.py
python3 Project/DeckVehicles/Scripts/render_deck_vehicles.py

/Users/Yun.Hu@blueshieldca.com/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  Project/DeckVehicles/Scripts/generate_deck_vehicle_documents.py

/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c \
  "globals()['__file__']='Project/DeckVehicles/Scripts/validate_deck_vehicles.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
```

Bambu Studio 02.07.01.62 used `--info` on all 28 STL/3MF exports and real `--slice 0 --arrange 0 --ensure-on-bed` commands on all seven production plates at both 0.12 and 0.16 mm. The 0.40 mm validation machine profile used three walls. `QA/BambuStudio_Validation.json` retains all commands, object lists, G-code byte counts, warnings and raw slicer logs.
