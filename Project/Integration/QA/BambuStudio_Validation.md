# Milestone 2 Bambu Studio Validation

Overall status: **PASS**

Bambu Studio 02.07.01.62 imported and inspected 63 STL/3MF exports, then performed 4 actual slicing runs. This report does not rely on `--info` alone.

## Propeller object mapping and correction

The legacy hull plate stored one named 3MF mesh with 21 ordered disconnected components. The original build order and component bounds verify Bambu object IDs 5, 9, 13, and 17 as the four propellers:

| Reported object ID | 3MF/Bambu named object | Legacy print-oriented bounds (mm) |
|---:|---|---:|
| 5 | `Propeller_1` | 7.26227 × 7.12636 × 2.07500 |
| 9 | `Propeller_2` | 7.26227 × 7.12636 × 2.07500 |
| 13 | `Propeller_3` | 7.26227 × 7.12636 × 2.07500 |
| 17 | `Propeller_4` | 7.26227 × 7.12636 × 2.07500 |

The corrected `Print_Plate_01_Hull.3mf` contains 17 explicitly named non-propeller objects. `Print_Plate_04_Propellers.3mf` contains four explicitly named propeller objects, and Bambu's import log binds IDs 5/9/13/17 to `Propeller_1`/`Propeller_2`/`Propeller_3`/`Propeller_4` respectively.

The propellers are new parametric solids at 100% scale: 7.26 mm overall diameter, five retained 0.60 mm blade lobes per object, 0.60 mm hub wall, 0.60 mm blind-bore back wall, and a common flat bed-side face. No scale enlargement was applied. A removable sprue was not required; a 3 mm brim remains recommended.

## Actual slicing results

| Plate | Layer | Status | Named objects | G-code bytes | Floating | Empty layers | Faulty mesh |
|---|---:|---:|---:|---:|---:|---:|---:|
| `3MF/Print_Plate_01_Hull.3mf` | 0.12 mm | PASS | 17/17 | 17,318,473 | 0 | 0 | 0 |
| `3MF/Print_Plate_01_Hull.3mf` | 0.16 mm | PASS | 17/17 | 14,063,805 | 0 | 0 | 0 |
| `3MF/Print_Plate_04_Propellers.3mf` | 0.12 mm | PASS | 4/4 | 169,066 | 0 | 0 | 0 |
| `3MF/Print_Plate_04_Propellers.3mf` | 0.16 mm | PASS | 4/4 | 158,586 | 0 | 0 | 0 |

All four real slice runs used a Bambu Lab A1 0.4 mm machine profile, three walls, 0.15 mm elephant-foot compensation, and the named 0.12/0.16 mm validation profiles. Every run returned `Success`, emitted non-empty G-code, loaded every named object, and produced none of the targeted warnings.

## Import / manifold checks

| Export | Status | Manifold | Objects | Parts | Facets | Maximum object size x × y × z (mm) |
|---|---:|---:|---:|---:|---:|---:|
| `STL/Arresting_Wire_1.stl` | PASS | yes | 1 | 1 | 12 | 2.803 × 29.950 × 0.350 |
| `STL/Arresting_Wire_2.stl` | PASS | yes | 1 | 1 | 12 | 2.803 × 29.950 × 0.350 |
| `STL/Arresting_Wire_3.stl` | PASS | yes | 1 | 1 | 12 | 2.803 × 29.950 × 0.350 |
| `STL/Arresting_Wire_4.stl` | PASS | yes | 1 | 1 | 12 | 2.803 × 29.950 × 0.350 |
| `STL/Catapult_1_Bow_Port.stl` | PASS | yes | 1 | 1 | 12 | 129.003 × 1.300 × 0.400 |
| `STL/Catapult_2_Bow_Starboard.stl` | PASS | yes | 1 | 1 | 12 | 128.006 × 1.800 × 0.400 |
| `STL/Catapult_3_Waist_Inner.stl` | PASS | yes | 1 | 1 | 12 | 165.068 × 14.797 × 0.400 |
| `STL/Catapult_4_Waist_Outer.stl` | PASS | yes | 1 | 1 | 12 | 158.061 × 12.798 × 0.400 |
| `STL/Deck_Module_1_Bow.stl` | PASS | yes | 1 | 1 | 148 | 146.000 × 69.440 × 3.000 |
| `STL/Deck_Module_2_Midship.stl` | PASS | yes | 1 | 1 | 204 | 147.000 × 73.700 × 3.000 |
| `STL/Deck_Module_3_Stern.stl` | PASS | yes | 1 | 1 | 312 | 197.000 × 69.809 × 3.000 |
| `STL/Elevator_1_Port.stl` | PASS | yes | 1 | 1 | 28 | 26.000 × 12.800 × 1.800 |
| `STL/Elevator_2_Starboard.stl` | PASS | yes | 1 | 1 | 28 | 22.000 × 13.800 × 1.800 |
| `STL/Elevator_3_Starboard.stl` | PASS | yes | 1 | 1 | 28 | 26.000 × 13.700 × 1.800 |
| `STL/Elevator_4_Starboard.stl` | PASS | yes | 1 | 1 | 28 | 25.500 × 14.800 × 1.800 |
| `STL/Hull_Module_1_Bow.stl` | PASS | yes | 1 | 1 | 41,296 | 164.667 × 58.140 × 31.431 |
| `STL/Hull_Module_2_Midship.stl` | PASS | yes | 1 | 1 | 15,008 | 164.767 × 58.302 × 31.430 |
| `STL/Hull_Module_3_Stern.stl` | PASS | yes | 1 | 1 | 11,676 | 158.767 × 57.847 × 31.426 |
| `STL/Interface_Pad_01_Port.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Pad_01_Starboard.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Pad_02_Port.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Pad_02_Starboard.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Pad_03_Port.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Pad_03_Starboard.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Pad_04_Port.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Pad_04_Starboard.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Pad_05_Port.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Pad_05_Starboard.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Pad_06_Port.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Pad_06_Starboard.stl` | PASS | yes | 1 | 1 | 12 | 6.000 × 6.000 × 2.400 |
| `STL/Interface_Test_Coupon_Female.stl` | PASS | yes | 1 | 1 | 28 | 25.000 × 20.000 × 3.000 |
| `STL/Interface_Test_Coupon_Male.stl` | PASS | yes | 1 | 1 | 28 | 25.000 × 20.000 × 5.200 |
| `STL/Propeller_1.stl` | PASS | yes | 1 | 1 | 1,082 | 7.260 × 7.124 × 2.075 |
| `STL/Propeller_2.stl` | PASS | yes | 1 | 1 | 1,082 | 7.260 × 7.124 × 2.075 |
| `STL/Propeller_3.stl` | PASS | yes | 1 | 1 | 1,082 | 7.260 × 7.124 × 2.075 |
| `STL/Propeller_4.stl` | PASS | yes | 1 | 1 | 1,082 | 7.260 × 7.124 × 2.075 |
| `STL/Raised_Marking_Bow_Centerline.stl` | PASS | yes | 1 | 1 | 140 | 133.000 × 5.600 × 0.350 |
| `STL/Raised_Marking_Elevator_1_Port.stl` | PASS | yes | 1 | 1 | 64 | 24.800 × 11.600 × 0.350 |
| `STL/Raised_Marking_Elevator_2_Starboard.stl` | PASS | yes | 1 | 1 | 64 | 20.800 × 12.600 × 0.350 |
| `STL/Raised_Marking_Elevator_3_Starboard.stl` | PASS | yes | 1 | 1 | 64 | 24.800 × 12.500 × 0.350 |
| `STL/Raised_Marking_Elevator_4_Starboard.stl` | PASS | yes | 1 | 1 | 64 | 24.300 × 13.600 × 0.350 |
| `STL/Raised_Marking_Landing_Aft.stl` | PASS | yes | 1 | 1 | 196 | 180.159 × 35.290 × 0.350 |
| `STL/Raised_Marking_Landing_Forward.stl` | PASS | yes | 1 | 1 | 156 | 112.159 × 30.051 × 0.350 |
| `STL/Rudder_Port.stl` | PASS | yes | 1 | 1 | 32 | 16.000 × 12.100 × 1.200 |
| `STL/Rudder_Starboard.stl` | PASS | yes | 1 | 1 | 32 | 16.000 × 12.100 × 1.200 |
| `STL/Shaft_1.stl` | PASS | yes | 1 | 1 | 20 | 50.359 × 1.560 × 1.351 |
| `STL/Shaft_1_Strut_P.stl` | PASS | yes | 1 | 1 | 20 | 5.860 × 1.240 × 1.074 |
| `STL/Shaft_1_Strut_S.stl` | PASS | yes | 1 | 1 | 20 | 5.860 × 1.240 × 1.074 |
| `STL/Shaft_2.stl` | PASS | yes | 1 | 1 | 20 | 51.290 × 1.560 × 1.351 |
| `STL/Shaft_2_Strut_P.stl` | PASS | yes | 1 | 1 | 20 | 5.860 × 1.240 × 1.074 |
| `STL/Shaft_2_Strut_S.stl` | PASS | yes | 1 | 1 | 20 | 5.860 × 1.240 × 1.074 |
| `STL/Shaft_3.stl` | PASS | yes | 1 | 1 | 20 | 51.290 × 1.560 × 1.351 |
| `STL/Shaft_3_Strut_P.stl` | PASS | yes | 1 | 1 | 20 | 5.860 × 1.240 × 1.074 |
| `STL/Shaft_3_Strut_S.stl` | PASS | yes | 1 | 1 | 20 | 5.860 × 1.240 × 1.074 |
| `STL/Shaft_4.stl` | PASS | yes | 1 | 1 | 20 | 50.359 × 1.560 × 1.351 |
| `STL/Shaft_4_Strut_P.stl` | PASS | yes | 1 | 1 | 20 | 5.860 × 1.240 × 1.074 |
| `STL/Shaft_4_Strut_S.stl` | PASS | yes | 1 | 1 | 20 | 5.860 × 1.240 × 1.074 |
| `3MF/CVN69_Hull_Deck_Assembly.3mf` | PASS | yes | 1 | 55 | 74,498 | 476.000 × 73.700 × 41.265 |
| `3MF/Interface_Test_Coupon.3mf` | PASS | yes | 1 | 2 | 56 | 53.000 × 20.000 × 5.200 |
| `3MF/Print_Plate_01_Hull.3mf` | PASS | yes | 17 | 17 | 68,284 | 164.767 × 58.302 × 31.431 |
| `3MF/Print_Plate_02_Deck.3mf` | PASS | yes | 1 | 3 | 664 | 197.000 × 217.949 × 3.000 |
| `3MF/Print_Plate_03_Details.3mf` | PASS | yes | 1 | 31 | 1,100 | 216.800 × 171.588 × 2.400 |
| `3MF/Print_Plate_04_Propellers.3mf` | PASS | yes | 4 | 4 | 4,328 | 7.260 × 7.124 × 2.075 |
