# Milestone 3 Validation Commands

Generated UTC: 2026-07-14T19:21:26.768683+00:00
FreeCAD: 1.1.1
Bambu Studio: 02.07.01.62

```sh
python3 Project/Island/Scripts/audit_island_reference.py
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "globals()['__file__']='Project/Island/Scripts/build_island.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
python3 Project/Island/Scripts/render_island.py
/Users/Yun.Hu@blueshieldca.com/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 Project/Island/Scripts/generate_island_documents.py
python3 Project/Island/Scripts/run_bambu_island_checks.py
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "globals()['__file__']='Project/Island/Scripts/validate_island.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
```
