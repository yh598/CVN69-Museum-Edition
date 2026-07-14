# Changelog

All released changes use semantic versioning. Release artifacts are never overwritten after tagging.

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
