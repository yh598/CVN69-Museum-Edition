# Milestone 1 Project Plan and Completion Record

## Objective

Deliver the complete, parameterized, consumer-FDM-printable hull for the USS Dwight D. Eisenhower (CVN-69) Museum Edition at 1:700, without advancing into flight-deck details, island, weapons, aircraft, radar, or display bases.

## Completed work packages

1. Requirements and reference boundary — complete
2. Parameter table and scale logic — complete
3. Sixteen-station full-hull loft — complete
4. Bulbous bow, stern, anchor recesses, and waterline witness — complete
5. Automatic module splitting and concealed alignment keys — complete
6. Four-shaft running gear, five-blade propellers, A-brackets, and twin rudders — complete
7. Concealed accessory locator sockets and print orientations — complete
8. FCStd, STEP, STL, 3MF, and OBJ export — complete
9. Mesh/BRep/STEP/dimension/fit validation — complete
10. Renders, drawings, assembly/printing documents, BOM, and release record — complete

## Acceptance record

- Overall length: 476.000 mm
- Maximum molded hull beam: 58.304 mm (58.300 mm target)
- Preferred plate: 220.056 × 177.291 × 31.431 mm
- Complete STL: 21 watertight manifold parts
- Non-manifold edges: 0
- Degenerate triangles: 0
- Normal mismatches: 0
- FreeCAD production leaf solids: OCC BOPCheck pass
- STEP: 21 closed solids on round-trip, with no self-intersection issue
- Bambu Studio: manifold yes

Automated status is PASS. Physical first-article printing remains a release caveat; dimensional QA cannot substitute for real filament shrinkage and adhesive behavior.

## Configuration and scaling

The 1:700 dimensions are the master. `CVN69_SCALE` accepts 1000, 700, or 350. Length, beam, depth, and appendages scale proportionally; functional print gauges and clearances are clamped where needed for a 0.4 mm nozzle. Module count derives from a 160 mm body-length target, preserving A1 Mini compatibility.

## Reference and fidelity policy

Authoritative public Navy material supports the Nimitz-class 1,092 ft length and four-shaft arrangement. Public CVN-69 shipyard body plans were not found. The geometry therefore uses public dimensions, official imagery, and a documented print-oriented station reconstruction. It must not be marketed as reverse-engineered shipyard geometry.

## Risks retained for v0.1.0

- First-article glue fit may require ±0.05 mm clearance tuning for a specific printer/filament pair.
- STEP re-import produces OpenCascade p-curve diagnostics on analytic loft faces; all 21 solids remain valid and closed, and no self-intersection diagnostic is present.
- Propeller/shaft gauges prioritize 0.4 mm-nozzle survival over exact scale thinness.

## Later milestones — blocked pending approval

The following remain untouched in this release: v0.2 flight deck, v0.3 island, v0.4 weapons, v0.5 aircraft, v0.6 base, v0.7 assembly integration, v0.8 QA expansion, v0.9 optimization, and v1.0 release. Work must not begin until Milestone 1 is approved.

