# Milestone 5 Bambu Studio validation

Overall status: **PASS**

Bambu Studio 02.07.01.62 imported 61 STL/3MF exports and completed 20 real slice runs across 10 production plates. This is not an `--info`-only check.

| Plate | Layer | Status | Objects | G-code bytes | Floating | Empty layers | Faulty mesh |
|---|---:|---:|---:|---:|---:|---:|---:|
| `3MF/Print_Plate_00_First_Article.3mf` | 0.12 mm | PASS | 12/12 | 906,662 | 0 | 0 | 0 |
| `3MF/Print_Plate_00_First_Article.3mf` | 0.16 mm | PASS | 12/12 | 780,483 | 0 | 0 | 0 |
| `3MF/Print_Plate_C2A_VRC40.3mf` | 0.12 mm | PASS | 5/5 | 528,789 | 0 | 0 | 0 |
| `3MF/Print_Plate_C2A_VRC40.3mf` | 0.16 mm | PASS | 5/5 | 455,602 | 0 | 0 | 0 |
| `3MF/Print_Plate_E2C_VAW123.3mf` | 0.12 mm | PASS | 6/6 | 634,272 | 0 | 0 | 0 |
| `3MF/Print_Plate_E2C_VAW123.3mf` | 0.16 mm | PASS | 6/6 | 550,267 | 0 | 0 | 0 |
| `3MF/Print_Plate_EA18G_VAQ130.3mf` | 0.12 mm | PASS | 5/5 | 373,445 | 0 | 0 | 0 |
| `3MF/Print_Plate_EA18G_VAQ130.3mf` | 0.16 mm | PASS | 5/5 | 326,062 | 0 | 0 | 0 |
| `3MF/Print_Plate_FA18E_VFA105.3mf` | 0.12 mm | PASS | 5/5 | 341,510 | 0 | 0 | 0 |
| `3MF/Print_Plate_FA18E_VFA105.3mf` | 0.16 mm | PASS | 5/5 | 296,738 | 0 | 0 | 0 |
| `3MF/Print_Plate_FA18E_VFA131.3mf` | 0.12 mm | PASS | 5/5 | 341,510 | 0 | 0 | 0 |
| `3MF/Print_Plate_FA18E_VFA131.3mf` | 0.16 mm | PASS | 5/5 | 296,738 | 0 | 0 | 0 |
| `3MF/Print_Plate_FA18E_VFA83.3mf` | 0.12 mm | PASS | 5/5 | 341,834 | 0 | 0 | 0 |
| `3MF/Print_Plate_FA18E_VFA83.3mf` | 0.16 mm | PASS | 5/5 | 297,110 | 0 | 0 | 0 |
| `3MF/Print_Plate_FA18F_VFA32.3mf` | 0.12 mm | PASS | 5/5 | 341,508 | 0 | 0 | 0 |
| `3MF/Print_Plate_FA18F_VFA32.3mf` | 0.16 mm | PASS | 5/5 | 296,761 | 0 | 0 | 0 |
| `3MF/Print_Plate_MH60R_HSM74.3mf` | 0.12 mm | PASS | 6/6 | 246,602 | 0 | 0 | 0 |
| `3MF/Print_Plate_MH60R_HSM74.3mf` | 0.16 mm | PASS | 6/6 | 205,813 | 0 | 0 | 0 |
| `3MF/Print_Plate_MH60S_HSC7.3mf` | 0.12 mm | PASS | 6/6 | 255,621 | 0 | 0 | 0 |
| `3MF/Print_Plate_MH60S_HSC7.3mf` | 0.16 mm | PASS | 6/6 | 216,995 | 0 | 0 | 0 |

All cases use a 0.4 mm nozzle validation machine, three walls, and the requested 0.12/0.16 mm layers. Named rotor objects must load one-for-one, guarding against missing blades or omitted rotor meshes.

## Import/manifold summary

Every record is retained in `BambuStudio_Validation.json`, including dimensions, facets, parts, per-object manifold results, and raw slice logs.
