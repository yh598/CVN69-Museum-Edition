# Milestone 3 Mesh / Geometry Validation

Overall status: **PASS**

| Check | Status | Evidence |
|---|---:|---|
| STL — Aft_Access_Ladder.stl | PASS | 92 facets; 1 component(s); 0 bad edges; [5.0, 3.8, 0.6] mm; min z 0.00000 |
| STL — Antenna_Detail_Set.stl | PASS | 4016 facets; 4 component(s); 0 bad edges; [11.0, 1.39956, 3.95] mm; min z 0.00000 |
| STL — Bridge_Window_Insert.stl | PASS | 36 facets; 1 component(s); 0 bad edges; [11.95, 14.45, 1.85] mm; min z 0.00000 |
| STL — Exhaust_Uptake.stl | PASS | 1050 facets; 1 component(s); 0 bad edges; [10.3, 9.9, 11.9] mm; min z 0.00000 |
| STL — Foundation_Lower_Island.stl | PASS | 1352 facets; 1 component(s); 0 bad edges; [31.80622, 15.6, 11.9] mm; min z 0.00000 |
| STL — Island_Interface_Coupon_Female.stl | PASS | 48 facets; 1 component(s); 0 bad edges; [40.0, 24.0, 3.0] mm; min z 0.00000 |
| STL — Island_Interface_Coupon_Male.stl | PASS | 120 facets; 1 component(s); 0 bad edges; [40.0, 24.0, 5.4] mm; min z 0.00000 |
| STL — Main_Mast.stl | PASS | 660 facets; 1 component(s); 0 bad edges; [9.0, 27.0, 8.0] mm; min z 0.00000 |
| STL — Main_Yardarm.stl | PASS | 68 facets; 1 component(s); 0 bad edges; [8.0, 14.0, 2.6] mm; min z 0.00000 |
| STL — Marking_69_Port.stl | PASS | 96 facets; 2 component(s); 0 bad edges; [5.4, 0.35, 3.6] mm; min z 0.00000 |
| STL — Marking_69_Starboard.stl | PASS | 96 facets; 2 component(s); 0 bad edges; [5.4, 0.35, 3.6] mm; min z 0.00000 |
| STL — Navigation_Bridge.stl | PASS | 200 facets; 1 component(s); 0 bad edges; [14.5, 17.1, 7.0] mm; min z 0.00000 |
| STL — PriFly_Window_Insert.stl | PASS | 36 facets; 1 component(s); 0 bad edges; [8.85102, 11.86735, 1.55] mm; min z 0.00000 |
| STL — Primary_Flight_Control.stl | PASS | 210 facets; 1 component(s); 0 bad edges; [12.5, 12.8, 5.7] mm; min z 0.00000 |
| STL — Radar_AN_SPN50_Array.stl | PASS | 582 facets; 1 component(s); 0 bad edges; [3.4, 7.0, 1.64989] mm; min z 0.00000 |
| STL — Radar_AN_SPS48G_Array.stl | PASS | 76 facets; 1 component(s); 0 bad edges; [6.0, 7.0, 1.15] mm; min z 0.00000 |
| STL — Radar_AN_SPS49_Array.stl | PASS | 76 facets; 1 component(s); 0 bad edges; [7.0, 4.2, 1.15] mm; min z 0.00000 |
| STL — Secondary_Mast.stl | PASS | 28 facets; 1 component(s); 0 bad edges; [1.2, 9.8, 7.0] mm; min z 0.00000 |
| STL — Signal_Light_Housings.stl | PASS | 4016 facets; 4 component(s); 0 bad edges; [1.44, 12.23955, 1.15] mm; min z 0.00000 |
| 3MF — CVN69_Hull_Deck_Island_Review.3mf | PASS | CRC=True; named objects=72/72; triangles=95738; bounds=[476.0, 73.7, 84.36572]; review/reference |
| 3MF — CVN69_Island_Assembly.3mf | PASS | CRC=True; named objects=17/17; triangles=12690; bounds=[39.40622, 17.9, 45.9]; review/reference |
| 3MF — Island_Interface_Test_Coupon.3mf | PASS | CRC=True; named objects=2/2; triangles=168; bounds=[40.0, 51.0, 5.4]; print envelope |
| 3MF — Print_Plate_01_Island_Body.3mf | PASS | CRC=True; named objects=4/4; triangles=2812; bounds=[78.10622, 17.1, 11.9]; print envelope |
| 3MF — Print_Plate_02_Mast_Radar.3mf | PASS | CRC=True; named objects=6/6; triangles=1490; bounds=[49.6, 27.0, 8.0]; print envelope |
| 3MF — Print_Plate_03_Antennas_Details.3mf | PASS | CRC=True; named objects=7/7; triangles=8388; bounds=[67.04102, 14.45, 3.95]; print envelope |
| FreeCAD Shape.check(True) / strict BOPCheck | PASS | 19 production/coupon objects; zero invalid/open solids or self-intersections |
| Island STEP round-trip | PASS | 25/25 closed solids; self-intersections=0; diagnostics=0 |
| Coupon STEP round-trip | PASS | 2/2 closed solids; self-intersections=0; diagnostics=0 |
| Review STEP round-trip | PASS | 80/80 closed solids; self-intersections=0; diagnostics=107 |
| Bambu Studio independent import/manifold check | PASS | Bambu Studio 02.07.01.62 loaded 25/25 STL/3MF exports; all manifold |
| Required source and production outputs exist | PASS | 67 required files; missing=[] |
| Build-manifest production hashes | PASS | 63 SHA-256/byte-size records match |
| Approved Milestone 1–2 inputs unchanged | PASS | 18 immutable hashes match |
| Production build excludes source mesh import | PASS | build_island.py creates Part BReps and does not import the reference archive/STL |
| PDF documentation structure | PASS | {'Island_Drawings.pdf': {'bytes': 879509, 'header_ok': True, 'eof_ok': True, 'pages': 6}, 'Island_Printing_Guide.pdf': {'bytes': 393390, 'header_ok': True, 'eof_ok': True, 'pages': 4}, 'Island_Project_Plan.pdf': {'bytes': 364884, 'header_ok': True, 'eof_ok': True, 'pages': 3}, 'Island_Interface_Coupon_Instructions.pdf': {'bytes': 136599, 'header_ok': True, 'eof_ok': True, 'pages': 1}} |
| All 14 high-resolution renders | PASS | {'Island_Port.png': (2750, 1826), 'Island_Starboard.png': (2750, 1826), 'Island_Forward.png': (2750, 1826), 'Island_Aft.png': (2750, 1826), 'Island_Top.png': (2750, 1826), 'Island_Bow_Isometric.png': (2750, 2023), 'Island_Stern_Isometric.png': (2750, 2023), 'Island_Exploded.png': (2750, 2023), 'Island_Interface_Section.png': (2640, 1760), 'CVN69_Hull_Deck_Island_Port.png': (3740, 1364), 'CVN69_Hull_Deck_Island_Starboard.png': (3740, 1364), 'CVN69_Hull_Deck_Island_Top.png': (3740, 1364), 'CVN69_Hull_Deck_Island_Bow_Isometric.png': (3740, 1803), 'CVN69_Hull_Deck_Island_Stern_Isometric.png': (3740, 1803)} |

## Checks run

Binary STL edge incidence, normals, degenerates, signed volume, z=0, print envelope; named-object 3MF ZIP/XML/CRC/index/material checks; FreeCAD Shape.check(True), strict BOPCheck, STEP round-trip, PDF/PNG structure, immutable-input hashes, production-output hashes, source-mesh exclusion, and Bambu Studio manifold checks.
