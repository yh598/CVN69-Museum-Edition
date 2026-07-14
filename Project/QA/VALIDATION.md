# Milestone 1 Validation Report

Overall status: **PASS**

| Check | Status | Evidence |
|---|---:|---|
| STL topology — Hull.stl | PASS | 74446 facets; 21 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Hull_Module_1.stl | PASS | 41032 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Hull_Module_2.stl | PASS | 15704 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Hull_Module_3.stl | PASS | 11630 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Propeller_1.stl | PASS | 1444 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Propeller_2.stl | PASS | 1444 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Propeller_3.stl | PASS | 1444 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Propeller_4.stl | PASS | 1444 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Rudder_Port.stl | PASS | 32 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Rudder_Starboard.stl | PASS | 32 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_1.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_1_Strut_P.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_1_Strut_S.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_2.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_2_Strut_P.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_2_Strut_S.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_3.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_3_Strut_P.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_3_Strut_S.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_4.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_4_Strut_P.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| STL topology — Shaft_4_Strut_S.stl | PASS | 20 facets; 1 component(s); 0 non-manifold edges; 0 degenerate facets |
| Complete kit part count | PASS | detected 21 disconnected watertight parts |
| Preferred plate envelope | PASS | Hull.stl bounds [220.0562, 177.29082, 31.43096] mm |
| A1 Mini module envelope | PASS | module maximum axes [164.66667, 164.76666, 158.76666] mm |
| 3MF package and indices | PASS | 74446 triangles; 4 allowed materials; CRC=True |
| FreeCAD BRep validity / self-intersection | PASS | 23 leaf/reference BRep shapes passed OCC BOPCheck |
| FreeCAD closed solids | PASS | all exported production Part::Feature objects are closed solids |
| STEP round-trip | PASS | 21 closed solids after STEP re-import; 0 self-intersection issues (92 OCC p-curve diagnostics recorded) |
| Overall hull length | PASS | measured 476.000 mm; target 476.000 mm |
| Maximum molded hull beam | PASS | measured 58.304 mm; target 58.300 mm |
| Glue-joint fit allowance | PASS | 0.250 mm per side; 0.50 mm diametral |
| Minimum modeled feature | PASS | 0.48 mm minimum strut radius / blade gauge; hull bodies are solid slicer volumes |
| Support strategy | PASS | hull modules orient flight-deck interface down; sockets bridge less than 8 mm; accessories have supplied flat/hex orientations |

## Limitations

- No shipyard lines or classified appendage drawings were available; fidelity is a public-data, photo-informed Nimitz-class reconstruction.
- Automated geometry checks do not replace a physical fit coupon and first-article print.
