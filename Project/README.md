# USS Dwight D. Eisenhower (CVN-69) — Museum Edition

Milestone 1 (`v0.1.0`) is the complete 1:700 hull release. It contains the bulbous-bow/full-hull envelope, cruiser stern, engraved waterline witness, paired anchor recesses, three keyed hull modules, four shaft lines with A-brackets and five-blade propellers, and twin rudders. Flight-deck details, island, weapons, aircraft, radar, and display bases are intentionally out of scope.

![Milestone 1 hull](Render/Hull_Isometric.png)

## Release status

- Geometry QA: **PASS** — 34/34 automated checks.
- Bambu Studio 02.07.01.62: **manifold**, 21 parts, 74,446 facets.
- Primary plate: 220.1 × 177.3 × 31.5 mm; fits X1C, P1S, and A1.
- A1 Mini: use the individual oriented STLs; every hull module is under 165 mm long.
- Glue joints: asymmetric concealed module keys plus concealed sockets for shafts, A-brackets, propellers, and rudders; 0.25 mm clearance per side.

## Deliverables

| Deliverable | File |
|---|---|
| Editable FreeCAD source | [`CAD/FreeCAD/Hull.FCStd`](CAD/FreeCAD/Hull.FCStd) |
| Parameter source | [`CAD/Python/hull_parameters.py`](CAD/Python/hull_parameters.py) |
| STEP assembly | [`STEP/Hull.step`](STEP/Hull.step) |
| Print-oriented STL kit | [`STL/Hull.stl`](STL/Hull.stl) |
| Multi-material 3MF | [`3MF/Hull.3mf`](3MF/Hull.3mf) |
| Assembled OBJ/MTL | [`OBJ/Hull.obj`](OBJ/Hull.obj) |
| Dimensioned drawings | [`Docs/Hull_Drawings.pdf`](Docs/Hull_Drawings.pdf) |
| Assembly guide | [`Docs/Hull_Assembly.pdf`](Docs/Hull_Assembly.pdf) |
| Printing guide | [`Docs/Hull_Printing_Guide.pdf`](Docs/Hull_Printing_Guide.pdf) |
| Project plan | [`Docs/Hull_ProjectPlan.pdf`](Docs/Hull_ProjectPlan.pdf) |
| Machine-readable QA | [`QA/validation_report.json`](QA/validation_report.json) |

The `STL/` directory also contains one already-oriented file per printable part.

## Principal model dimensions

| Parameter | 1:700 release |
|---|---:|
| Overall hull length | 476.00 mm |
| Maximum molded hull beam | 58.30 mm |
| Molded depth datum | 31.50 mm |
| Engraved waterline datum | z = 15.90 mm |
| Hull modules | 3 |
| Printable parts | 21 |

The generator supports `CVN69_SCALE=1000`, `700`, or `350`; split count is calculated from the model length. Functional features are clamped for a 0.4 mm nozzle at 1:1000.

## Build and validate

FreeCAD 1.1.1 was used for this release. Run from the repository root (`3D/`):

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \
  "globals()['__file__']='Project/Scripts/build_milestone_1.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"

/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c \
  "globals()['__file__']='Project/Scripts/validate_milestone_1.py'; exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))"
```

Render images with `python3 Project/Scripts/render_hull.py` and regenerate PDFs with the bundled-document Python runtime described in `Scripts/generate_documents.py`.

## Accuracy boundary

The Navy's public Nimitz-class description gives a 1,092 ft length and four shafts; 1,092 ft converts to 475.49 mm at 1:700, while this project's mandated display length is 476 mm. Public shipyard body plans and appendage drawings for CVN-69 were not available. Consequently, the station loft and appendage placement are a photo-informed, print-oriented reconstruction—not a claim to reproduce controlled shipyard lines. This limitation is preserved in the FCStd metadata, drawings, and validation report.

Primary public references:

- [NAVSEA Cost Estimating Handbook — Nimitz-class overview](https://www.navsea.navy.mil/Portals/103/Documents/05C/2005_NAVSEA_CEH_Final.pdf)
- [NAVSEA Naval Nuclear Propulsion Program — Nimitz-class dimensions](https://www.navsea.navy.mil/Portals/103/Documents/PSNSY_IMF/News%20Releases/2013%20Naval%20Nuclear%20Propulsion%20Program.pdf?ver=2017-03-02-113143-683)
- [Naval History and Heritage Command — attack carriers](https://www.history.navy.mil/research/histories/naval-aviation-history/attack-carriers.html)
- [NHHC CVN-69 photographic record](https://www.history.navy.mil/our-collections/photography/numerical-list-of-images/nhhc-series/naval-subjects-collection/l45--us-navy-ships/61-80/l45-80-06-01-uss-dwight-d--eisenhower--cvn-69-.html)

## License

CAD, meshes, drawings, and documentation are offered under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Generator and validation scripts are offered under the [MIT License](https://opensource.org/license/mit). See [`LICENSE.md`](LICENSE.md).

