# Milestone 5 validation commands

All commands were run from the repository root on 14 July 2026.

```sh
python3 Project/AirWing/Scripts/audit_airwing_references.py

/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \
  "globals()['__file__']='Project/AirWing/Scripts/build_airwing.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"

/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \
  "globals()['__file__']='Project/AirWing/Scripts/build_airwing_layout.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"

/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \
  "globals()['__file__']='Project/AirWing/Scripts/validate_airwing.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"

python3 Project/AirWing/Scripts/run_bambu_airwing_checks.py
python3 Project/AirWing/Scripts/render_airwing.py

/Users/Yun.Hu@blueshieldca.com/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  Project/AirWing/Scripts/generate_airwing_documents.py
```

Bambu Studio was run by `run_bambu_airwing_checks.py` with `--info` for all 61 STL/3MF exports and with real `--slice 0 --arrange 0 --ensure-on-bed` commands for every production plate at 0.12 and 0.16 mm. The machine was a 0.40 mm A1 validation profile with three walls; P2S is the primary intended printer.
