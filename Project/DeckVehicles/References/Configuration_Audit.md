# Milestone 6 configuration and public-reference audit

Configuration freeze: **14 October 2023 through 14 July 2024**. This is a representative deployment-era display layout, not a reconstruction of one photograph. Public evidence supports each included family; no source triangle or controlled drawing is used.

| Code | Included family | Public evidence and dimensional basis | Confidence / accuracy boundary |
|---|---|---|---|
| STT49 | A/S32A-49 Shipboard Tow Tractor | [NAVAIR role and photograph](https://www.navair.navy.mil/product/Shipboard-Tow-Tractor-STT); [Department of the Navy SAM notice](https://sam.gov/opp/e2c470306bf64dc28a7a1df13b696f26/view) gives 138.9 × 73.2 × 40.16 in | High for official envelope; photo-informed silhouette; wheels/body enlarged for FDM. |
| P25A | A/S32P-25A Shipboard Firefighting Vehicle | [NAVAIR upgrade report and official image](https://www.navair.navy.mil/node/21206); [public Navy training-plan copy](https://www.globalsecurity.org/military/library/policy/navy/ntsp/p25-a.htm) gives 190 × 70 × 64 in | High for envelope, medium for simplified exterior. The source says two operating trucks are required during flight operations. |
| MSU200 | MSU-200NAV air-start service cart | [NAVAIR systems description](https://www.navair.navy.mil/systems); [public Navy training-plan copy](https://www.globalsecurity.org/military/library/policy/navy/ntsp/msu_200-p_2002.pdf) gives module dimensions 68.31 × 36.61 × 27.35 in | Medium-high for module envelope; towable chassis and hose are photo-informed/FDM-enlarged. |
| TOWBAR | Carrier aircraft tow bar | [Official Navy DVIDS photograph, 9 October 2023](https://www.dvidshub.net/image/8063718/aircraft-handling) | Medium; photo-derived, not an engineering drawing. Fork and bar sections are deliberately enlarged. |
| LADDER | Portable aircraft maintenance ladder | [Official CVN-69 deployment-era maintenance image, 6 February 2024](https://www.dvidshub.net/image/8278538/uss-dwight-d-eisenhower-conducts-routine-maintenance-in-the-red-sea) | Medium; visually approximated envelope. Rails/rungs are enlarged to 0.60 mm and the production part prints flat. |
| CHOCK | Aircraft wheel-chock group | [Official shipboard handling account](https://www.dvidshub.net/news/153407/1-228th-aviation-regiment-joins-navy-for-qualification); [official explanatory image](https://www.dvidshub.net/image/6811000/night-flying-operations) | Medium; generic wedge form. Chocks and connecting rope/bar are deliberately enlarged. |
| EXT | Twin portable extinguisher cart | [NAVAIR P-25 equipment report](https://www.navair.navy.mil/node/21206) documents three 20-lb portable extinguishers carried on the vehicle | Medium; the static grouped cart is a display-rationale arrangement, not a claim that the exact cart was photographed on CVN-69. Bottles/rails/wheels are enlarged. |

## Deployment-era visual anchor

[Official DVIDS imagery from 29 January 2024](https://www.dvidshub.net/image/8253033/uss-dwight-d-eisenhower-conducts-routine-operations-red-sea) explicitly shows a tractor aboard CVN-69 during the frozen period. The layout uses this as a type-presence anchor, not as a coordinate survey.

## Deliberate FDM enlargements

Every enlargement is machine-readable in `deck_vehicle_parameters.py` and `QA/FDM_Enlargements.json`. At 1:700 the literal wheel, rail, hose, tow-bar, and bottle sections would be below a reliable 0.4 mm-nozzle feature. Released dimensions therefore preserve recognizable envelopes where possible but use 0.60–1.10 mm printable sections. These details are not dimensionally exact.

## Omitted after audit

- Carrier crash crane, forklift, bomb cart, hydraulic/oxygen/nitrogen carts, deck scrubber, aircraft jacks, hose reels, rotor storage stands, and large maintenance platforms: public evidence confirms many as Navy equipment, but the frozen-period CVN-69 type/configuration or safe uncluttered placement was not strong enough for this release.
- Weapons, ammunition, crew, moving aircraft/vehicles, functional steering/lifts, ocean base, electronics, and lighting: outside Milestone 6 scope.

Public DVIDS imagery is used under the public-domain status shown on each image page. No photograph is redistributed in the repository; URLs, dates, captions, and modeling inferences are recorded only.
