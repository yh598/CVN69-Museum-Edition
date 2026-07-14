# Milestone 3 Bambu Studio Validation

Overall status: **PASS**

Bambu Studio 02.07.01.62 independently loaded and inspected 25 STL/3MF exports.

| Export | Status | Manifold | Parts | Facets | Size x × y × z (mm) |
|---|---:|---:|---:|---:|---:|
| `STL/Aft_Access_Ladder.stl` | PASS | yes | 1 | 92 | 5.000 × 3.800 × 0.600 |
| `STL/Antenna_Detail_Set.stl` | PASS | yes | 4 | 4,016 | 11.000 × 1.400 × 3.950 |
| `STL/Bridge_Window_Insert.stl` | PASS | yes | 1 | 36 | 11.950 × 14.450 × 1.850 |
| `STL/Exhaust_Uptake.stl` | PASS | yes | 1 | 1,050 | 10.300 × 9.900 × 11.900 |
| `STL/Foundation_Lower_Island.stl` | PASS | yes | 1 | 1,352 | 31.806 × 15.600 × 11.900 |
| `STL/Island_Interface_Coupon_Female.stl` | PASS | yes | 1 | 48 | 40.000 × 24.000 × 3.000 |
| `STL/Island_Interface_Coupon_Male.stl` | PASS | yes | 1 | 120 | 40.000 × 24.000 × 5.400 |
| `STL/Main_Mast.stl` | PASS | yes | 1 | 660 | 9.000 × 27.000 × 8.000 |
| `STL/Main_Yardarm.stl` | PASS | yes | 1 | 68 | 8.000 × 14.000 × 2.600 |
| `STL/Marking_69_Port.stl` | PASS | yes | 2 | 96 | 5.400 × 0.350 × 3.600 |
| `STL/Marking_69_Starboard.stl` | PASS | yes | 2 | 96 | 5.400 × 0.350 × 3.600 |
| `STL/Navigation_Bridge.stl` | PASS | yes | 1 | 200 | 14.500 × 17.100 × 7.000 |
| `STL/PriFly_Window_Insert.stl` | PASS | yes | 1 | 36 | 8.851 × 11.867 × 1.550 |
| `STL/Primary_Flight_Control.stl` | PASS | yes | 1 | 210 | 12.500 × 12.800 × 5.700 |
| `STL/Radar_AN_SPN50_Array.stl` | PASS | yes | 1 | 582 | 3.400 × 7.000 × 1.650 |
| `STL/Radar_AN_SPS48G_Array.stl` | PASS | yes | 1 | 76 | 6.000 × 7.000 × 1.150 |
| `STL/Radar_AN_SPS49_Array.stl` | PASS | yes | 1 | 76 | 7.000 × 4.200 × 1.150 |
| `STL/Secondary_Mast.stl` | PASS | yes | 1 | 28 | 1.200 × 9.800 × 7.000 |
| `STL/Signal_Light_Housings.stl` | PASS | yes | 4 | 4,016 | 1.440 × 12.240 × 1.150 |
| `3MF/CVN69_Hull_Deck_Island_Review.3mf` | PASS review/reference | yes | 1 | 18,302 | 164.767 × 58.304 × 31.430 |
| `3MF/CVN69_Island_Assembly.3mf` | PASS review/reference | yes | 1 | 660 | 9.000 × 8.000 × 27.000 |
| `3MF/Island_Interface_Test_Coupon.3mf` | PASS | yes | 1 | 120 | 40.000 × 24.000 × 5.400 |
| `3MF/Print_Plate_01_Island_Body.3mf` | PASS | yes | 1 | 1,352 | 31.806 × 15.600 × 11.900 |
| `3MF/Print_Plate_02_Mast_Radar.3mf` | PASS | yes | 1 | 660 | 9.000 × 27.000 × 8.000 |
| `3MF/Print_Plate_03_Antennas_Details.3mf` | PASS | yes | 1 | 36 | 11.950 × 14.450 × 1.850 |

Assembly and integrated-review 3MF files are non-production references and are exempt only from the 240 mm plate envelope. All objects must still import and report manifold. Raw mesh z=0, topology, and 3MF ZIP/XML/CRC checks are performed by the deterministic validator.
