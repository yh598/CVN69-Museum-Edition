# Milestone 2 Validation Commands

Generated UTC: 2026-07-14T17:43:05.697205+00:00
FreeCAD: 1.1.1
Bambu Studio: 02.07.01.62

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "globals()['__file__']='Project/Integration/Scripts/build_hull_deck_integration.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
python3 Project/Integration/Scripts/render_hull_deck_integration.py
python3 Project/Integration/Scripts/run_bambu_integration_checks.py
/Users/Yun.Hu@blueshieldca.com/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 Project/Integration/Scripts/generate_integration_documents.py
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "globals()['__file__']='Project/Integration/Scripts/validate_hull_deck_integration.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
```
