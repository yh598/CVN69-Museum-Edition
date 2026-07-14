# CVN-69 Milestone 2 — Glue-Only Assembly

## Before the full print

The first-article `3MF/Interface_Test_Coupon.3mf` has a recorded physical PASS at 100% scale with a 0.40 mm nozzle, 0.16 mm layers, three walls, 0.00 mm XY compensation, and 0.15 mm elephant-foot compensation. The 6.00 mm male feature entered the 6.50 mm female socket by hand and seated correctly. The qualified clearance is 0.25 mm per side, and the production interface dimensions are frozen.

If the printer, material, slicer behavior, or compensation differs materially from the qualified setup, print the coupon before committing the full print. Do not alter the frozen CAD interface to compensate for a new process without creating a new revision and repeating physical qualification.

## Print sequence

1. Print `Print_Plate_01_Hull.3mf` in Bambu PLA Matte Ash Gray, with optional Silk Silver for shafts. This corrected plate contains no propellers.
2. Print `Print_Plate_02_Deck.3mf` in Bambu PLA Matte Charcoal.
3. Print `Print_Plate_03_Details.3mf`; assign Ivory White to raised markings, Silk Silver to metallic details, Ash Gray to interface pads, and Charcoal to elevators.
4. Print `Print_Plate_04_Propellers.3mf` in Silk Silver at 100% scale. Use 0.12 or 0.16 mm layers, three walls, and a 3 mm brim; supports and a sprue are not required.
5. Confirm every object is at 100% scale and rests on z = 0. Do not auto-scale a plate to fit.

## Hull preparation

1. Assemble the three hull modules using the approved Milestone 1 concealed keys and 0.25 mm-per-side fit.
2. Keep the top seating face free of squeeze-out. Let the hull seams cure on a straight reference surface.
3. Dry-fit each numbered interface pad in its matching hull-top socket. Pads are paired port/starboard at x = 32, 105, 205, 270, 370, and 445 mm.

## Flight-deck preparation

1. Dry-fit the three deck modules. In the authoritative coordinate system, seams are at x = 146 and 286 mm.
2. Glue the deck module seams on a verified flat surface and allow them to cure fully.
3. Verify the island opening and four elevator recesses remain clear. Do not install elevators or raised details yet.

## Hull-to-deck bonding

1. Install all twelve pads into the hull sockets without glue and lower the cured deck assembly onto the hull.
2. Confirm bow and stern datums are flush, centerlines coincide, every pad enters its deck socket, and the deck underside seats directly on the hull top without rocking.
3. Remove the deck. Apply a thin film of medium or gel CA only to the hidden overlapping hull-top seating area and a very small amount inside the pad sockets.
4. Reinstall the pads and lower the deck vertically. Do not slide it longitudinally after the pads engage.
5. Hold the assembly straight until stable. Remove any squeeze-out before it reaches a visible deck edge.

## Deck details

After the hull/deck bond has cured, install the four removable elevator plates, raised marking parts, catapult tracks, and arresting wires using the integrated top render as the placement map.

## Prohibited hardware

This interface is designed for printed geometry and adhesive only. Do not add magnets, screws, metal pins, heat-set inserts, or purchased connectors.

## First-article note

Physical coupon PASS is recorded in `QA/Physical_Coupon_Result.md`. Keep the frozen dimensions in `QA/Production_Interface_Freeze.md` unchanged for production. A future interface revision must pass a new physical coupon before use.
