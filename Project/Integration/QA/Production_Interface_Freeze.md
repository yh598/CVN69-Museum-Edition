# Milestone 2 Production Interface Freeze

Freeze ID: `M2-DECK-HULL-INTERFACE-2026-07-14`

Status: **FROZEN — PHYSICAL PASS**

Effective: 2026-07-14

The deck-to-hull interface is frozen to the production dimensions below. The basis is the physical PASS recorded in [`Physical_Coupon_Result.md`](Physical_Coupon_Result.md): the coupon printed at 100% scale with a 0.40 mm nozzle, 0.16 mm layers, three walls, 0.00 mm XY compensation, and 0.15 mm elephant-foot compensation assembled by hand and seated correctly.

## Frozen dimensions

| Dimension | Frozen value |
|---|---:|
| Male pad plan size | 6.00 × 6.00 mm |
| Male pad total height | 2.40 mm |
| Hull insertion | 1.20 mm |
| Deck insertion | 1.20 mm |
| Female socket opening | 6.50 × 6.50 mm |
| Clearance | 0.25 mm per side |
| Hull socket nominal depth | 1.20 mm |
| Deck socket nominal depth | 1.45 mm |
| Socket opening allowance | 0.05 mm |
| As-modeled hull/deck cut depths | 1.25 / 1.50 mm |
| Vertical pad-tip clearance | 0.25 mm |
| Deck top skin over socket | 1.55 mm |
| Nominal seating gap | 0.00 mm |
| Minimum structural thickness | 1.20 mm |

Pad stations remain x = 32, 105, 205, 270, 370, and 445 mm, paired at y = −8 and +8 mm in the 476 mm bow-to-stern coordinate system.

## Artifact lock

[`Production_Interface_Freeze.json`](Production_Interface_Freeze.json) records byte sizes and SHA-256 hashes for the governing parameter source, FreeCAD assembly, production STEP, hull/deck/pad STLs, production 3MF files, and coupon exports. Those hashes define the accepted production interface artifact set.

Any change to a frozen dimension or governed artifact invalidates this freeze. Such a change requires a new revision, regenerated artifacts, and another physical coupon PASS before production use.
