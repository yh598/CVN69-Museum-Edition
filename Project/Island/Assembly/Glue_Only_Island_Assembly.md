# CVN-69 Milestone 3 — Glue-Only Island Assembly

## First: print the interface coupon

Print `3MF/Island_Interface_Test_Coupon.3mf` at 100% scale with the same PLA, nozzle, layer height, and XY/elephant-foot compensation planned for the production foundation.

The coupon reproduces the actual asymmetric opening and male plug, 0.25 mm clearance per side, 2.40 mm insertion, wall thickness, and 0.60 × 0.35 mm open glue channels. The male must enter by hand and the broad faces must seat without rocking. Do not scale production files to correct a failed coupon; correct printer or slicer compensation and repeat the test.

## Materials

- structural bodies, masts, yardarm, railings, ladder: Bambu PLA Matte Ash Gray
- bridge and PriFly window inserts: Bambu PLA Matte Charcoal
- radar faces and major antennas: Bambu PLA Silk Silver
- port/starboard `69` markings: Bambu PLA Matte Ivory White
- signal-light housings: Bambu PLA Basic Black

AMS slot numbers are intentionally not assigned. Separate color objects are designed for glue-on assembly.

## Print sequence

1. Print `Print_Plate_01_Island_Body.3mf` and verify the foundation plug and glue channels are clean.
2. Print `Print_Plate_02_Mast_Radar.3mf`; fragile mast and radar objects use their documented flat orientations.
3. Print `Print_Plate_03_Antennas_Details.3mf`; inspect every 0.60–0.80 mm feature before removal.
4. Dry-fit the bridge/PriFly window inserts in their matching recesses.
5. Keep all radar faces and identification markings separated by object name.

## Island subassembly

1. Bond `Navigation_Bridge`, `Primary_Flight_Control`, and `Exhaust_Uptake` to the top of `Foundation_Lower_Island`. Use the isometric and exploded renders for orientation.
2. Install the two Charcoal window inserts into their matching recessed bands. They should sit flush without force.
3. Bond `Main_Mast` to its central pedestal and `Secondary_Mast` above PriFly. Verify both are square in front and side views before the adhesive sets.
4. Add `Main_Yardarm`, then the three named radar arrays. AN/SPN-50 is the smaller modern rectangular air-traffic-radar part; do not substitute legacy dish geometry.
5. Install the antenna detail set, signal-light housings, and aft access ladder.
6. Install `Marking_69_Port` and `Marking_69_Starboard` with the digits upright when viewed from each side.

## Deck installation

1. Leave elevators, deck seams, catapults, arresting wires, and nearby raised markings unobstructed.
2. Test the complete island dry in the approved deck opening. The asymmetric plug prevents backward installation.
3. Confirm the flange seats flat at z = 34.50 mm, the island does not rock, and no glue channel is visible.
4. Remove the island. Apply a minimal amount of medium or gel CA to the hidden flange and open glue channels; avoid the visible deck perimeter.
5. Lower the island vertically. Do not slide it longitudinally once the plug enters the opening.
6. Hold the island square until stable. Check lean from port/starboard and forward/aft views before full cure.

## Prohibited hardware

Do not add magnets, screws, threaded inserts, heat-set inserts, metal pins, or purchased connection hardware.

## Acceptance record

Record printer, nozzle, PLA, layer height, XY compensation, measured coupon seating gap, and pass/fail result. Automated CAD/mesh checks do not replace a physical first-article coupon and dry fit.
