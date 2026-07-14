# Milestone 4 Validation Commands

Executed from the repository root on **2026-07-14**.

- FreeCAD: **1.1.1**
- Bambu Studio: **02.07.01.62**
- Primary printer target: **Bambu Lab P2S**

```sh
python3 Project/WeaponsDeckEdge/Scripts/audit_weapons_references.py

/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \
  "globals()['__file__']='Project/WeaponsDeckEdge/Scripts/build_weapons_deckedge.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"

python3 Project/WeaponsDeckEdge/Scripts/render_weapons_deckedge.py

/Users/Yun.Hu@blueshieldca.com/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  Project/WeaponsDeckEdge/Scripts/generate_weapons_documents.py

python3 Project/WeaponsDeckEdge/Scripts/run_bambu_weapons_checks.py

/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \
  "globals()['__file__']='Project/WeaponsDeckEdge/Scripts/validate_weapons_deckedge.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
```

Final automated result: **PASS** — 204/204 checks, 45/45 STL, 7/7 3MF, 3/3 STEP, zero unintended interference, 54/54 deterministic byte matches, and 52/52 Bambu Studio imports.
