# Changelog

All released changes use semantic versioning. Release artifacts are never overwritten after tagging.

## Unreleased — Milestone 4 defensive systems and deck-edge equipment

### Added

- New deterministic parametric FreeCAD BReps for the public 2023–2024 visible defensive fit; no source STL is opened by the production builder and no source triangles are reused.
- Public configuration audit fixing two Mk 15 Phalanx CIWS, two Mk 49 RAM, and two Mk 29 Sea Sparrow/ESSM installations, with exact modeled coordinates, evidence URLs/dates, confidence, and unresolved uncertainty.
- Forty-three named production objects: six additive platforms/sponsons, six weapons separated into foundations/bodies/faces/domes/barrels, six life-raft groups, a generic utility-boat/cradle/davit set, and selected major railings, ladders, lights, and lockers.
- One common asymmetric printed mount interface with 0.25 mm clearance per side, 1.20 mm seating depth, 1.20 mm remaining platform skin, hidden open glue channel, and a two-part physical coupon.
- Editable FreeCAD source; weapons/coupon/review STEP; 45 production/coupon STLs; assembly OBJ; seven named-object 3MF packages; and a non-production integrated hull–deck–island–weapons review model.
- Nineteen high-resolution full-ship, weapon-area, family, exploded, interface-section, and print-plate renders.
- Drawings, printing guide, project plan, coupon instructions, glue-only assembly guide, dimensional/topology/interference/reference/Bambu reports, material mapping, and SHA-256 build manifest.

### Accuracy boundary

- The approved coordinate system, deck datum, seams, and island bounds are dimensionally verified imports.
- System identities are supported by official public Navy/NAVSEA evidence; exact counts and placements are cross-image-derived and are not described as shipyard-accurate.
- Launcher grids, CIWS barrels, life-raft canisters, railings, ladders, lights, and selected fittings are deliberately simplified or enlarged for 0.4 mm-nozzle FDM and are labeled accordingly.
- The utility boat is intentionally generic; public evidence did not establish a reliable subtype.

### Validation

- 204/204 native BRep, dimensional, interface, STEP round-trip, output, document, topology, interference, deterministic-rebuild, and Bambu checks pass.
- 45/45 STL files are watertight/manifold with zero boundary or non-manifold edges, zero degenerate triangles, consistent normals, and documented z=0 print orientation.
- 7/7 3MF packages pass ZIP, CRC, XML, relationship, content-type, object-name, material, index, and build-item validation; 3/3 STEP exports re-import as closed valid solids with zero self-intersections.
- Full integrated checks report zero unintended overlap above 0.10 mm³ against approved hull/deck modules, elevators, catapults, arresting wires, markings, twelve landing pads, island structures, seams, and neighboring Milestone 4 objects.
- The second full FreeCAD rebuild byte-matches all 54 deterministic STL/OBJ/3MF outputs; Bambu Studio 02.07.01.62 independently imports all 52 STL/3MF exports and reports them manifold.

### Scope

- Aircraft, deck vehicles, ammunition, internal/functional weapon mechanisms, ocean base, display stand, electronics, and final full-ship release remain excluded.
- No v1.0 or other release tag is created; physical coupons remain separate real-world gates.

## Unreleased — Milestone 3 island reconstruction and integration

### Added

- New deterministic, parametric FreeCAD island BReps; no source STL triangles are reused.
- Public-reference configuration audit frozen to the 2023–2024 deployment, including the AN/SPS-48G and CVN-69 AN/SPN-50 fit.
- Seventeen major glue-assembled production parts: foundation/lower body, bridge, PriFly, uptake, masts, yardarm, radar faces, window inserts, ladder, antennas, signal housings, and separate `69` markings.
- Asymmetric concealed foundation plug derived from the approved island opening, with 0.25 mm clearance per side and hidden open glue channels.
- Full-geometry male/female interface coupon and one-page test instructions.
- Island/coupon/review STEP, individual print-oriented STL files, assembly/review OBJ/3MF, and three named-object print plates.
- Fourteen high-resolution island and integrated hull–deck–island renders.
- Drawings, printing guide, project plan, assembly guide, dimensional QA, mesh validation, interference report, Bambu Studio report, reference-confidence report, and SHA-256 build manifest.

### Accuracy boundary

- Approved deck datums and opening geometry are dimensionally verified.
- Island superstructure proportions are derived from official public photographs and the supplied mesh envelope and are not described as shipyard-accurate.
- Unverified small sensors, cabling, sub-scale safety netting, and ambiguous equipment are omitted.

### Validation

- 36/36 mesh, package, FreeCAD BRep, STEP round-trip, document, render, immutable-input, and manifest checks pass.
- 16/16 dimensional and interface checks pass, including 0.250 mm clearance per side, zero X/Y/seating error, and zero measured mast lean.
- 6/6 integrated interference checks pass with zero unintended island overlap against the approved deck, elevators, markings, catapults, arresting wires, or twelve landing pads.
- Bambu Studio 02.07.01.62 independently imports all 25 STL/3MF exports and reports them manifold.

### Scope

- Weapons, aircraft, deck vehicles, ocean base, display stand, lighting/electronics, and a full-ship production release remain excluded.
- No release tag is created.

## Unreleased — Milestone 2 hull–flight-deck integration

### Added

- One authoritative x = 0 bow to x = 476 mm stern coordinate system and a documented mirror transform for the approved flight deck.
- Deterministic FreeCAD integration assembly containing 55 production solids without rebuilding the approved hull or deck planform.
- Twelve concealed 6 × 6 × 2.4 mm printed landing pads with 0.25 mm-per-side sockets, direct zero-gap hull-top seating, and 1.55 mm minimum deck skin above sockets.
- Staggered deck seams at x = 146 and 286 mm against hull seams at x = 158.667 and 317.333 mm.
- Assembly and coupon STEP, 57 individual production/coupon STLs, assembly/coupon 3MF, and three Bambu-ready print plates.
- Top, port, starboard, bow/stern isometric, exploded, keyed-section, and direct-support renders.
- Integration drawings, printing guide, glue-only assembly guide, object-level material mapping, and one-page physical coupon procedure.

### Validation

- 71/71 mesh/package/BRep/STEP/document checks pass.
- 14/14 dimensional checks pass, including 476.000 mm length, zero centerline/datum error, 0.250 mm measured clearance per side, and 0.000 mm nominal seating gap.
- 5/5 interference checks pass: zero unintended hull/deck, pad, elevator, and island-opening overlap.
- Bambu Studio 02.07.01.62 independently reports all 62 STL/3MF exports manifold.

### Scope

- Island, weapons, aircraft, radar, ocean base, and display stand remain excluded.
- No release tag is created pending physical coupon and reviewer approval.

## Unreleased — Flight-deck reconstruction review

### Added

- Clean scripted FreeCAD/OpenCascade flight-deck BRep at the corrected 476 mm 1:700 length; no source mesh triangles are reused.
- Three glue-keyed deck modules, four elevator inserts, seven raised-marking parts, four catapult tracks, and four arresting wires.
- FreeCAD, STEP, individual STL/3MF, assembly 3MF, print-plate 3MF, OBJ, top-view, and isometric outputs.
- Visual/numerical inventory of all 33 available source STLs and explicit preservation of source topology defects in the report.
- Independent strict BRep/STEP checks, STL topology checks, 3MF package checks, dimensional QA, and Bambu Studio CLI inspection of 47 exports.

### Scope

- Island, weapons, aircraft, hull redesign, and ocean base remain excluded.

## 0.1.0 — 2026-07-13

### Added

- Parameterized 16-station Nimitz-class full-hull loft at the mandated 476 mm length.
- Bulbous bow, stern form, paired anchor recesses, and engraved waterline witness.
- Three A1 Mini-compatible hull modules with asymmetric concealed keys.
- Four hex-printable shafts, eight A-bracket struts, four socketed five-blade propellers, and twin keyed rudders.
- Concealed, clearance-controlled mounting sockets for all glue-on running gear.
- FreeCAD, STEP, STL, 3MF, and OBJ/MTL exports.
- Manifold/normal/dimension/fit validation, Bambu Studio compatibility check, renders, drawings, BOM, assembly guide, printing guide, project plan, and release notes.

### Validation

- 34/34 automated checks pass.
- `Hull.stl`: 74,446 facets, 21 watertight manifold components, zero non-manifold edges, zero degenerate facets, and consistent normals.
- STEP re-import: 21 closed solids; no self-intersection issues.

### Known limitations

- Public shipyard lines were unavailable; hull stations and appendage placement remain a public-data, photo-informed reconstruction.
- A physical first-article print and glue-fit coupon are still required before declaring production validation complete.
