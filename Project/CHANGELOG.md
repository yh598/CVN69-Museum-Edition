# Changelog

All released changes use semantic versioning. Release artifacts are never overwritten after tagging.

## Unreleased — Milestone 6 flight-deck vehicles and aviation support equipment

### Added

- Public-reference audit frozen to 14 October 2023 through 14 July 2024, supporting seven families and explicitly omitting uncertain equipment instead of inventing deck clutter.
- Sixteen new parametric FreeCAD/OpenCascade production solids for the A/S32A-49 tow tractor, P-25A firefighting vehicle, MSU-200NAV air-start cart, carrier tow bar, maintenance ladder, wheel-chock group, portable extinguisher group, color inserts, and family-only sprues. No source mesh is opened or reused.
- Documented 0.4 mm-nozzle enlargement for 1.00 × 0.70 mm wheels, 0.80 mm tow bars/axles/sprues, 0.70 mm handles, and 0.60 mm ladder/hose details; enlarged features are not described as dimensionally exact.
- Two editable FCStd sources; master/default/integrated STEP; 16 individual STLs; master/default/integrated OBJ/3MF; seven non-empty production/first-article plates; and light/default/full combined review 3MFs.
- Configurable light/default/full support layouts containing 14/24/32 instances with family, variant, x/y/z, heading, material, relationship, confidence/rationale, state, source, and linkage metadata.
- Forty-five family, exploded, plate, layout, integrated, close-up, and vignette renders; five PDFs; glue-only assembly instructions; material and confidence schedules; machine-readable dimensional/enlargement/layout/interference reports.

### Validation

- Bambu Studio 02.07.01.62 independently imports all 28 STL/3MF exports and completes 14 actual 0.12/0.16 mm production-plate slices with non-empty G-code, all named difficult objects retained, and zero floating-region, empty-layer, or faulty-mesh warnings.
- The first ladder orientation exposed real empty-layer failures during slicing and was redesigned as a flat-backed, support-free part before the passing validation run.
- Approved Milestone 1–5 input hashes remain governed and unchanged, including the physically qualified frozen 0.25 mm-per-side hull/deck interface.

### Scope

- Static external deck vehicles/support equipment only. No weapons/ammunition, crew, functional mechanisms, approved hull/deck/interface/island/weapon/AirWing redesign, ocean base, display stand, lighting/electronics, or final release work is included.
- Milestone 5 and Milestone 6 physical first articles remain NOT RUN. No v1.0 or other release tag is created.

## Unreleased — Milestone 5 carrier air wing

### Added

- Official-source frozen-period CVW-3 audit for 14 October 2023 through 14 July 2024, confirming nine unit/type combinations and establishing the deployed VAW-123 aircraft as E-2C rather than E-2D.
- Forty-eight new parametric FreeCAD/OpenCascade production objects: 25 major spread/folded/launch or rotor-state bodies plus no-paint canopy, rotodome, rotor, and neutral squadron identity inserts. No source mesh is opened or reused.
- Official-dimension 1:700 envelopes with documented 0.4 mm-nozzle enlargement: 0.70 mm flight surfaces, 0.80 mm landing/support features, 0.70 × 0.60 mm rotor blades, 0.60 mm fins/inserts, and 0.50 × 0.30 mm raised identity details.
- Removable 0.80 mm bed-connected belly/engine print rails in STL/3MF print geometry; clean assembly BReps and STEP geometry remain rail-free.
- Editable master/layout FreeCAD sources; 12 STEP exports; 48 individual STLs; 13 named/material 3MF packages; master/default-layout OBJ; integrated M2–M5 review STEP/3MF; and ten production plates including a ≤120 × 120 mm first article.
- Configurable light/default/full layouts containing 16/32/36 aircraft with type, variant, squadron, x/y/z, heading, material, evidence URL, and confidence metadata.
- Twenty-two full-ship, layout, type-family, variant, no-paint, and first-article renders; drawings, printing, plan, first-article, and layout PDFs; glue-only assembly and material schedules.

### Validation

- All 48 production BReps are single valid closed solids; all 12 STEP exports re-import as valid closed solids. Strict compound-level cross-object messages are retained but do not invalidate valid/closed child solids.
- 48/48 STLs pass watertight/manifold, normal, positive-volume, z=0, boundary-edge, non-manifold-edge, and degenerate-triangle checks; 13/13 3MF packages pass ZIP/OPC/XML/name/material/index/build validation.
- Light/default/full layouts pass traced deck-boundary, island, weapon, elevator, catapult, arresting-wire, raised-marking, neighbor-clearance, and exact ≤0.10 mm³ overlap checks at 16/32/36 aircraft.
- Bambu Studio 02.07.01.62 passes 61 independent STL/3MF imports and 20 actual 0.12/0.16 mm production-plate slices with non-empty G-code, all named objects/rotors present, and zero floating-region, empty-layer, or faulty-mesh warnings.
- Approved Milestone 1–4 input hashes remain unchanged, including the physically qualified frozen 0.25 mm-per-side hull/deck interface.

### Scope

- Aircraft geometry and deck placement only. No approved hull, deck, interface, island, weapon, vehicle, ocean base, electronics, or display-base geometry is changed.
- Physical first-article printing remains a separate real-world gate. No release tag is created.

## Approved baseline ledger

- `70fe661` records the completed Milestone 3 island reconstruction and integrated review package.
- `1afb7cf` records the physical PASS of the Milestone 2 interface coupon at 100% scale: 0.40 mm nozzle, 0.16 mm layers, three walls, zero XY compensation, and 0.15 mm elephant-foot compensation.
- The qualified 0.25 mm-per-side deck-to-hull production interface is frozen; later milestones may reference but must not revise its dimensions or approved child artifacts.
- Milestone 4 adds the frozen-period defensive systems and deck-edge package while preserving Milestones 1–3.
- `05805a6` removes the four propellers from the hull plate, supplies their dedicated continuously sliceable plate, and leaves the approved hull modules and frozen hull/deck interface unchanged.

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
- Assembly and coupon STEP, 57 individual production/coupon STLs, assembly/coupon 3MF, and four Bambu-ready print plates.
- Corrected `Print_Plate_01_Hull.3mf` with all four legacy propeller components removed and 17 remaining parts promoted to explicit named 3MF objects.
- Added `Print_Plate_04_Propellers.3mf` with four explicit named objects and clean parametric five-blade solids: 7.26 mm diameter, 0.60 mm blades, printable hub/bore walls, common bed face, no scale enlargement, and no required sprue.
- Top, port, starboard, bow/stern isometric, exploded, keyed-section, and direct-support renders.
- Integration drawings, printing guide, glue-only assembly guide, object-level material mapping, and one-page physical coupon procedure.

### Validation

- 73/73 mesh/package/BRep/STEP/document/propeller checks pass.
- Physical interface coupon PASS at 100% scale using a 0.40 mm nozzle, 0.16 mm layers, three walls, 0.00 mm XY compensation, and 0.15 mm elephant-foot compensation; the 0.25 mm-per-side parts assembled by hand and seated correctly.
- Production deck-to-hull interface dimensions frozen under `Integration/QA/Production_Interface_Freeze.json` with SHA-256-governed CAD, STEP, STL, and 3MF artifacts.
- 16/16 dimensional checks pass, including 476.000 mm length, zero centerline/datum error, 0.250 mm measured clearance per side, 0.000 mm nominal seating gap, the physical coupon gate, and the production-interface freeze gate.
- 5/5 interference checks pass: zero unintended hull/deck, pad, elevator, and island-opening overlap.
- Bambu Studio 02.07.01.62 independently reports all 63 STL/3MF exports manifold and completes four actual 0.12/0.16 mm slice runs for the corrected hull and propeller plates with zero floating-region, empty-layer, or faulty-mesh warnings.

### Scope

- Island, weapons, aircraft, radar, ocean base, and display stand remain excluded.
- No release tag is created pending reviewer approval.

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
