# Changelog

All released changes use semantic versioning. Release artifacts are never overwritten after tagging.

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
