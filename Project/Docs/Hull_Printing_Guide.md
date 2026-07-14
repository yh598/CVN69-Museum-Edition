# Hull Printing Guide — v0.1.0

## Printer routing

- X1 Carbon, P1S, or A1: load `3MF/Hull.3mf` or `STL/Hull.stl`. Plate envelope is 220.1 × 177.3 mm.
- A1 Mini: load individual files from `STL/`. Each hull module is less than 165 mm long; print accessories as a separate plate.

All supplied STLs are already in their intended support-free orientation. Hull modules print with the future flight-deck interface on the bed. Shafts and struts use a flat hex facet; propellers and rudders lie flat.

## Required process

| Setting | Hull modules | Running gear |
|---|---:|---:|
| Nozzle | 0.4 mm | 0.4 mm |
| Layer height | 0.16 mm | 0.12 mm |
| Walls | 3 | 3 |
| Top / bottom layers | 5 / 5 | 5 / 5 |
| Infill | 15% gyroid | 15% gyroid |
| Supports | Off | Off |
| Brim | Optional 3 mm | 3 mm recommended for shafts/struts |

Use PLA only. Recommended colors encoded in the 3MF:

- Hull, struts, rudders: PLA Matte Ash Gray
- Shafts: PLA Silk Silver
- Propellers: PLA Basic Gold

All colors are from the approved palette. No painting is required.

## Fit controls

- Nominal glue clearance is 0.25 mm per side (0.50 mm total).
- Keep XY hole compensation at zero for the first fit coupon.
- If first-layer elephant foot is visible, apply 0.10–0.15 mm elephant-foot compensation rather than sanding exterior seams.
- Do not scale STLs independently. Regenerate at 1:1000 or 1:350 from the parameter source so clearances and split count remain controlled.

## Preflight

1. Confirm the slicer detects 21 parts in the complete kit.
2. Confirm supports are disabled and no auto-orientation has changed the supplied placement.
3. Assign 0.12 mm layer height to the 18 running-gear objects and 0.16 mm to the three hull modules.
4. Confirm minimum first-layer contact for shafts/struts; use a brim, not supports.
5. Print one bow/midship seam region first if the filament has unusual shrinkage.

## Post-print

Allow parts to cool before removal. Flex the plate rather than levering against the waterline groove. Deburr only concealed keys/sockets. Do not fill or sand the engraved waterline or anchor pockets.

