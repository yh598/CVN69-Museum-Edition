# CVN-69 Island Configuration Audit

Access date for all web references: **2026-07-14**.

## Frozen configuration

The reconstruction is frozen to USS *Dwight D. Eisenhower*'s deployment from **14 October 2023 through 14 July 2024**, with the visible fit anchored to official imagery dated **30 June 2024**. The deployment dates are confirmed by the U.S. Navy/DVIDS return report and Commander, U.S. 2nd Fleet. This period is recent, extensively photographed in public, and predates the 2025 planned incremental availability, avoiding undocumented maintenance-era mixing.

This is a public-reference, photo-informed reconstruction. It is not a shipyard-accurate or controlled-technical-data model.

## Reference hierarchy

1. Approved Milestone 2 deck opening, transform, and deck elevation: dimensionally authoritative for this project.
2. Official U.S. Navy, NAVAIR, NAVSEA, Fleet Forces, and DVIDS public releases: authoritative for dates, visible configuration, and named radar installations.
3. The supplied v0.4 STL: dimensional/visual reference only for placement envelope and proportions; its triangles are not reused.
4. Visual inference across multiple photographs: used only where public dimensions are unavailable and explicitly labeled approximate.

## Feature audit

| Feature | Frozen-period interpretation | Evidence class | Confidence | Known uncertainty |
|---|---|---|---:|---|
| Island foundation | Asymmetric plug follows the approved opening at x = 325.0–355.0 mm, y = 19.2–33.0 mm; 0.25 mm clearance per side | approved CAD | verified | Physical printer compensation remains first-article dependent |
| Lower island body | Faceted, tapered block covering the opening and supporting bridge, uptake, mast, and aft cantilever | approved opening + source/photo proportion | high | Exact plating breaks and door locations are omitted |
| Navigation bridge | Forward block with projecting bridge wing and dark wraparound window insert | 2024 official photos | high | Window count and mullion spacing are simplified for 0.4 mm FDM |
| Primary flight control | Separate aft tower/cantilever with wraparound dark window insert | 2024 official photos + source silhouette | high | Interior layout and exact glazing divisions are unavailable |
| Bridge wings/platforms | Projecting platforms with 0.60 mm printable railings | 2024 official photos | medium-high | Small stanchions and safety netting are simplified |
| Exhaust/uptake | Central tapered uptake with two visible cap forms | 2024 photo silhouette + source reference | medium | Public photographs do not provide exact duct cross-sections |
| Main mast | Tapered main mast, tiered platforms, transverse yardarm, and upper whip | 2024 official photos + source height | high silhouette / medium dimensions | Platform spacing is photo-derived |
| Secondary mast | Smaller aft mast above primary flight control | 2024 official photos | medium-high | Minor crossarms are omitted where evidence is ambiguous |
| AN/SPS-48G | Major 3-D air-search array represented as a separate ribbed panel | official Navy equipment documentation + 2024 silhouette | high identity / medium placement detail | Exact rotation angle at the photographed instant is not meaningful |
| AN/SPN-50(V)1 | Modern rectangular shipboard air-traffic radar; legacy SPN-43 dish is excluded | NAVAIR installation record and fielding report | high | Fine panel lattice and cabling are below reliable print scale |
| AN/SPS-49-family array | Upper rectangular air-search-array silhouette retained as a separate panel | public CVN-69 historical record + 2024 silhouette comparison | medium | Exact 2024 variant and fine feed geometry are not asserted |
| Communications antennas | Four major visible whip/pedestal forms on main and secondary mast platforms | 2024 official photos | medium | Numerous smaller aerials are intentionally omitted |
| Yardarms/support frames | One major transverse yardarm with diagonal supports | 2024 official photos | high | Small secondary bars are simplified |
| Railings/ladders | FDM-safe bridge/PriFly railings and one representative aft access ladder | visible public features + print rule | medium | Not every real railing or ladder is modeled |
| Identification 69 | Separate Ivory White port/starboard objects | official imagery | high | Block-digit geometry is optimized for 0.50–0.60 mm strokes |
| Signal lights | Four separate black housings on the main yardarm | public photo silhouette | medium | Lens colors and exact sequence are not asserted |

## Major arrangement

- The navigation bridge occupies the forward end of the island; primary flight control projects aft.
- The uptake and main mast form the central vertical mass. The main mast uses tiered platforms and a broad transverse yardarm.
- The secondary mast rises from the aft/PriFly structure.
- The AN/SPS-48G, AN/SPN-50, and upper SPS-49-family faces are separate printable objects so their silver material and fragile geometry do not force multicolor changes through the structural bodies.
- Dark bridge/PriFly window bands are separate recessed inserts; no painting is required.

## Changes from earlier configurations

- NAVAIR identifies AN/SPN-50(V)1 as the replacement for AN/SPN-43C and specifically scheduled the first operational-test installation on CVN-69. A later NAVAIR leadership summary states that the replacement was fielded aboard *Dwight D. Eisenhower*. Therefore, the large legacy SPN-43 dish seen in older carrier references is deliberately excluded.
- Navy documentation describes AN/SPS-48G as the progressive CVN backfit replacing AN/SPS-48E; the frozen model uses the G-era panel identity while simplifying its face.
- Older CVN-69 photographs show different mast details and radar fits. They are used only to understand persistent island massing, not to add equipment absent from the 2023–2024 imagery.
- The 2025 planned incremental availability and 2026 post-maintenance sea-trial fit are outside the freeze. No feature visible only after that maintenance period is included.

## Public sources

- [U.S. Navy photo 240630-N-UQ924-1763 — 30 June 2024 configuration anchor](https://www.navy.mil/Resources/Photo-Gallery/igphoto/2003496438/)
- [U.S. Navy photo 240502-N-MW930-1109 — Mediterranean photo exercise](https://www.navy.mil/Resources/Photo-Gallery/igphoto/2003457556/)
- [U.S. Navy photo 240505-N-FM895-1237 — Suez Canal transit](https://www.navy.mil/Resources/Photo-Gallery/igphoto/2003460881/)
- [U.S. Navy photo 240428-N-EM691-1117 — Souda Bay arrival](https://www.navy.mil/Resources/Photo-Gallery/igphoto/2003456688/)
- [DVIDS image 8332038 — March 2024 flight operations](https://www.dvidshub.net/image/8332038/uss-dwight-d-eisenhower-conducts-flight-operations-red-sea)
- [Commander, U.S. 2nd Fleet — return from the 2023–2024 deployment](https://www.c2f.usff.navy.mil/Press-Room/News-Stories/Article/3838635/unprecedented-dwight-d-eisenhower-carrier-strike-group-returns-from-combat-depl/)
- [NAVAIR — AN/SPN-50 contract and CVN-69 installation plan](https://www.navair.navy.mil/news/Navy-awards-contract-new-shipboard-air-traffic-radar/Thu-10012020-1020)
- [NAVAIR — first AN/SPN-50 fielding aboard USS Dwight D. Eisenhower](https://www.navair.navy.mil/news/PMA-213-welcomes-new-leadership/Wed-08092023-0647)
- [U.S. Navy — AN/SPS-48G public fact file](https://www.navy.mil/DesktopModules/ArticleCS/Print.aspx?Article=2167957&ModuleId=724&PortalId=1)
- [NAVSEA/NSWC Dahlgren — AN/SPS-48G modernization overview](https://www.navsea.navy.mil/Portals/103/Documents/NSWC_Dahlgren/LeadingEdge/Sensors/Sensors03.pdf)
- [DVIDS — 2025 planned incremental availability boundary](https://www.dvidshub.net/news/489050/uss-dwight-d-eisenhower-transits-norfolk-naval-shipyard-nnsy-planned-incremental-availability-pia-following-historic-deployment)

## Omitted because evidence or print scale is insufficient

- Unverified small electronic-warfare boxes, cable runs, horn clusters, and minor satellite terminals.
- Exact interior bridge/PriFly subdivision.
- Thin safety netting, sub-0.60 mm stanchions, and decorative surface plating.
- Any weapon, weapon director treated primarily as weapon-system geometry, CIWS, RAM, or Sea Sparrow equipment.

No private, restricted, classified, leaked, controlled, or non-public technical information was used.
