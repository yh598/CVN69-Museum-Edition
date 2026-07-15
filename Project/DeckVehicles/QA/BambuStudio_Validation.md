# Milestone 6 Bambu Studio validation

Overall status: **PASS**

Bambu Studio 02.07.01.62 imported 28 STL/3MF exports and completed 14 real slice runs across 7 production plates. This is not an `--info`-only check.

| Plate | Layer | Status | Objects | G-code bytes | Floating | Empty layers | Faulty mesh |
|---|---:|---:|---:|---:|---:|---:|---:|
| `3MF/Print_Plate_00_First_Article.3mf` | 0.12 mm | PASS | 11/11 | 154,165 | 0 | 0 | 0 |
| `3MF/Print_Plate_00_First_Article.3mf` | 0.16 mm | PASS | 11/11 | 129,362 | 0 | 0 | 0 |
| `3MF/Print_Plate_01_Tow_Tractors.3mf` | 0.12 mm | PASS | 3/3 | 46,526 | 0 | 0 | 0 |
| `3MF/Print_Plate_01_Tow_Tractors.3mf` | 0.16 mm | PASS | 3/3 | 39,730 | 0 | 0 | 0 |
| `3MF/Print_Plate_02_Service_Carts.3mf` | 0.12 mm | PASS | 3/3 | 42,120 | 0 | 0 | 0 |
| `3MF/Print_Plate_02_Service_Carts.3mf` | 0.16 mm | PASS | 3/3 | 36,442 | 0 | 0 | 0 |
| `3MF/Print_Plate_03_Firefighting_Equipment.3mf` | 0.12 mm | PASS | 5/5 | 67,778 | 0 | 0 | 0 |
| `3MF/Print_Plate_03_Firefighting_Equipment.3mf` | 0.16 mm | PASS | 5/5 | 55,051 | 0 | 0 | 0 |
| `3MF/Print_Plate_04_Tow_Bars_Chocks.3mf` | 0.12 mm | PASS | 4/4 | 94,163 | 0 | 0 | 0 |
| `3MF/Print_Plate_04_Tow_Bars_Chocks.3mf` | 0.16 mm | PASS | 4/4 | 82,162 | 0 | 0 | 0 |
| `3MF/Print_Plate_05_Ladders_Maintenance.3mf` | 0.12 mm | PASS | 1/1 | 34,936 | 0 | 0 | 0 |
| `3MF/Print_Plate_05_Ladders_Maintenance.3mf` | 0.16 mm | PASS | 1/1 | 34,939 | 0 | 0 | 0 |
| `3MF/Print_Plate_06_Wheels_Inserts_Details.3mf` | 0.12 mm | PASS | 7/7 | 79,417 | 0 | 0 | 0 |
| `3MF/Print_Plate_06_Wheels_Inserts_Details.3mf` | 0.16 mm | PASS | 7/7 | 63,908 | 0 | 0 | 0 |

All cases use the 0.4 mm nozzle validation machine, three walls, and requested 0.12/0.16 mm layers. Named wheels, handles/tow bars, ladders, chocks, extinguishers, sprues, inserts, reels, turret and coupon objects must load one-for-one.

Raw commands and slicer logs are retained in `BambuStudio_Validation.json`.
