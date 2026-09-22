# Research Appendix: Data Sources Explored During Project Planning

**Purpose of this appendix:** to document the data sources — and the details, access methods, and limitations of each — that were identified and explored with the help of AI during the planning phase of this project. It's a record of what was investigated and verified, organized by theme, with a confidence/status tag on each source:

- **Confirmed** — actually downloaded/queried directly and verified working during research.
- **High-confidence, not re-verified** — a well-established, standard public dataset; not independently re-checked in this session, but not expected to be a problem.
- **Dead end** — checked directly and it does not deliver what we hoped. Documented so nobody re-investigates it.

---

## 1. CHCCS's Own Primary Sources

### Board of Education Retreat Deck — December 11, 2025
**Confirmed.** 37-page PDF, real extractable text. Contains the district-wide ADM projection table, funding-in-arrears model, and financial impact tables.
- URL: `https://d3n9y02raazwpg.cloudfront.net/chccs/7ab2f0ad-22eb-4a03-aa47-ff62c673341c-bf2c6f2f-6a5f-4aa7-a665-6efde7d73e84-1773414282.pdf`
- **Notable finding:** the "CHCCS Enrollment & Demographic Trends" section (presented by Carolina Demography's director) is literally just a title-card divider slide — no chart or data behind it. Confirmed by rendering the page to an image and looking at it directly, not just extracting text. This is the strongest evidence that CHCCS's public board materials don't show their causal analysis.

### Closure Study — "A Study of the Proposed Closure of Ephesus, Glenwood and Seawell Elementary Schools," May 7, 2026
**Confirmed.** 104-page PDF, drafted by CHCCS District Administration, hosted at chccstogether.org. Real extractable text. Contains per-school projections and a causal-framing quote on the drivers of enrollment decline.
- URL: `https://www.chccstogether.org/_files/ugd/32373e_aaf35080ab73494f97a8de0f6fce6c3c.pdf`
- Landing page with FAQ/timeline: `https://www.chccstogether.org/`
- Contains 15 mentions of "Demography," per-school enrollment tables through 2035-36, Pre-K/dual-language/LEAP zone-of-residence tables, After-School Program capacity data, and NC legal context for school closure/consolidation (N.C.G.S. § 115C-47(1), § 115C-72) — useful for understanding the decision *process*, not just the numbers.

### The actual Carolina Demography report — title confirmed, document itself not found
The report referenced throughout CHCCS materials has a specific, confirmed title:

> **"Student Membership Forecast: 2025-26 through 2035-36 for Orange County: Chapel Hill-Carrboro City Schools and Orange County Schools"**

Facts confirmed about it:
- Commissioned by **Orange County** (not CHCCS alone) under a contract with Carolina Demography — covers *both* CHCCS and Orange County Schools.
- Analyzes all CHCCS schools individually (the closure study quotes it school-by-school).
- Presented to the CHCCS board on **April 9, 2026** by Nathan Dollar (Director, Carolina Demography).
- A **separate, earlier** presentation happened at the Dec 11, 2025 retreat (the divider-slide one above) — so Carolina Demography presented to the board at least twice; the April 2026 one appears to be the fuller version.

**Not found as a standalone public document**, despite checking:
- CHCCS's Granicus board-meeting archive (`chccs.granicus.com`)
- Orange County's BOCC Agenda Center, including a full 266-page March 2026 work-session packet (only one unrelated "Carolina Demography" mention, about the county's aging population — not schools)
- General web search across multiple query variations

**Next step if this document is wanted directly:** email CHCCS's board clerk or Orange County directly, referencing the exact title above. Also worth checking CHCCS's board portal for the **April 9, 2026** meeting specifically (agenda item was titled "Student Membership Forecast") — the Granicus search for that exact date didn't surface a direct attachment link, but the meeting almost certainly has one once indexed/archived.

### Local reporting worth using as secondary sources / fact-checks
None of these are datasets, but they're useful for verifying claims, finding quotes, and tracking the story's timeline:
- WUNC: ["Chapel Hill-Carrboro City Schools cuts 19 staff due to falling enrollment"](https://www.wunc.org/education/2026-04-10/chapel-hill-carrboro-schools-cuts-staff) (Apr 10, 2026) — mentions Ephesus/Glenwood growth vs. other schools declining.
- WUNC: ["CHCCS names 3 schools for possible closure"](https://www.wunc.org/education/2026-03-06/chccs-names-3-schools-for-possible-closure) (Mar 6, 2026)
- Daily Tar Heel: "CHCCS Superintendent hosts talk, addresses enrollment declines and funding cuts" (Nov 20, 2025)
- Chapelboro: ["New Studies Suggest CHCCS Close 1 Elementary School, Address Capacity Issues Through Redistricting"](https://chapelboro.com/news/pre-k-12-education/new-studies-suggest-chccs-close-1-elementary-school-address-capacity-issues-through-redistricting) — links to chccstogether.org.
- Triangle Blog Blog: ["Seven charts to consider in the CHCCS School Closure debate"](https://triangleblogblog.com/2026/02/24/seven-charts-to-consider-in-the-chccs-school-closure-debate/) (Feb 24, 2026) — includes a screenshot chart from the Dec 2025 retreat.
- Triangle Blog Blog: ["Live blog blog: CHCCS in a Time of Change meeting"](https://triangleblogblog.com/2025/11/17/live-blog-blog-chccs-in-a-time-of-change-meeting/) (Nov 17, 2025) — this is where the county-commissioned joint report was first mentioned ("due in late Jan-Feb").
- George Griffin's Substack — recaps individual board meetings in detail (e.g., "April 9 and 16, 2026 School Board Meetings"), useful for finding exact agenda-item titles and dates.

---

## 2. NC DPI / State Education Data

### NC DPI School Report Card Data (County Business Patterns-style bulk data)
**Confirmed.** Real downloadable data — two ZIP files + a data dictionary, not just a landing page.
- Download page: `https://www.dpi.nc.gov/data-reports/school-report-cards/school-report-card-resources-researchers`
- Direct files (confirmed via content-type headers): `/src-data-set-2024-251-2/open`, `/src-data-set-2024-252-2/open` (both `application/zip`), `/srcdatadictionary202425xlsx/open` (real `.xlsx`)
- **~67 tables** (2009-present, actively maintained), every table keyed by `year` + `agency_code`.
- **CHCCS's LEA/agency code is 681** (confirmed via NC DPI's own published AIG plan document).
- The `rcd_adm` table (Average Daily Membership) provides real historical, non-projected enrollment by district and by individual school, back to 2006 — confirmed by direct download and cross-checked against CHCCS's own reported figures.
- The `rcd_location` table provides an agency_code-to-school-name crosswalk, confirmed against all current CHCCS schools.

### NC DPI Facility Needs Survey — DEAD END for per-school capacity
**Dead end, confirmed by direct download and parsing.** Downloaded the actual 2020-21 statewide report (`https://www.dpi.nc.gov/documents/schoolplanning/facility-needs-survey-2020-21/download?attachment`, real PDF, 21 pages). It does **not** give per-school or even clean per-LEA capacity data — the appendix tables aggregate by **county** only (e.g., "Orange"), which conflates CHCCS with Orange County Schools (a separate LEA). This confirms the original handoff doc's caution: **do not build a utilization-rate claim** — there's no clean public source for per-school building capacity.

---

## 3. Geographic / GIS Data

### CHCCS School Attendance Boundaries — real, live, queryable
**Confirmed.** The public-facing "school assignment map" page itself has no visible download link, but tracing the underlying ArcGIS Instant App (via its public item-config API) revealed live, unauthenticated ArcGIS REST feature services:
- Elementary School Districts: `https://gis.carrboronc.gov/server/rest/services/SP/CHCCSElemSP/MapServer` (layer 20 = districts, layer 10 = walk zones)
- Middle School Districts: `https://gis.carrboronc.gov/server/rest/services/SP/CHCCSMidSP/MapServer`
- High School Districts: `https://gis.carrboronc.gov/server/rest/services/SP/CHCCSHS_SP/MapServer`
- General school assignments layer: `https://gis.carrboronc.gov/server/rest/services/SP/CHCCSDistrictsSP/MapServer`
- Test-queried the elementary layer directly and got back real GeoJSON polygon boundary data. No auth needed — append `/query?where=1=1&outFields=*&f=geojson` to a specific layer URL.
- **Use case:** mapping attendance boundaries (e.g., overlaying housing growth or demographic data against them) — a real, free source for this exists.

### Chapel Hill "Current Development Activity" — real, geolocated, forward-looking
**Confirmed.** A live ArcGIS point layer with real project records: name, type (residential/mixed-use/institutional), street address, review/approval status, approval dates.
- Feature service: `https://gisweb.townofchapelhill.org/arcgis/rest/services/MapServices/CurrentDevelopmentActivity/FeatureServer/0`
- Direct downloads: CSV / GeoJSON / Shapefile / KML all available via Chapel Hill's open data hub (`opendata-townofchapelhill.hub.arcgis.com`).
- Sample records confirmed real (e.g., Carraway Village, South Creek).
- **Limitation:** no unit-count field — tells you *where* and *what kind* of development, not how many housing units.
- **Not yet checked:** Carrboro has an analogous "Active Projects" page (`https://townofcarrboro.org/830/Active-Projects`) — same technique (look for an underlying ArcGIS item/feature service) would likely work but wasn't tried.

### Orange County Parcels — DEAD END for year-built
**Dead end, confirmed.** The county's "Parcels With Attributes" layer (`https://ocgis.com/arcpub/rest/services/LegalLotsAttributeOpenData/FeatureServer/0`) is real and geolocated (polygons + site address), but its schema only has address/ownership fields — **no year-built or unit-count field**. That level of detail likely lives in the county tax assessor's CAMA (Computer-Assisted Mass Appraisal) records, which were not located as a public download in this research pass.

---

## 4. Demographic & Population Data

### NC OSBM State Demographer Population Projections — real, strong, independent
**Confirmed via description, download link identified.** Direct CSV/Excel download ("Sex, Race, Age Groups (2010-2060)") covering all NC counties, with 2010-2024 estimates and 2024-2060 projections, broken out by sex/race/age group.
- Landing page: `https://www.osbm.nc.gov/facts-figures/population-demographics/state-demographer/countystate-population-projections`
- **Why this matters:** it's an *independent* government source for whether Orange County's under-18 population is actually declining, separate from CHCCS's own enrollment model or even Carolina Demography's district-specific work. Useful for answering "is this bigger than CHCCS, or specific to CHCCS?"

### NC DNPE Homeschool Statistics — real, deep historical archive
**Confirmed by direct download and parsing.** Annual reports going back to **1988-89**, county-level counts.
- Landing page: `https://www.doa.nc.gov/divisions/non-public-education/home-school-statistics`
- Downloaded and parsed the 2022-23 report directly: **Orange County had 781 registered home schools** that year (confirmed in a clean county-by-county table alongside all 100 NC counties).
- Report URLs follow a predictable pattern, e.g. `https://www.doa.nc.gov/dnpe-home-school-2022-23-annual-report-pdf/open` — swap the year to get other years, all the way back to 1988-89.
- **Caveats:** county-level, not CHCCS-specific (Orange County contains both CHCCS and Orange County Schools) — describe as a county-level proxy, not a CHCCS number. Also counts registered *home schools* (households), not individual students.

### Census ACS — standard, not re-verified this session but high-confidence
- **Year Structure Built (table B25034)** — tract/block-group level, decade-built buckets, standard ACS table. Good for understanding housing-stock age.
- **Housing cost burden / median rent / median home value** — already surfaced real Orange County numbers via search: median gross rent $1,387, 45.4% of renters cost-burdened (2019-2023 ACS). Available at tract level with 5-year vintages for trending.

---

## 5. Housing & Economic Data

### Zillow Research Data (ZHVI / ZORI)
**High-confidence, not independently re-verified this session** (well-established public dataset). Free CSV downloads at `zillow.com/research/data/`, ZIP-code level, monthly history back to 2000. Chapel Hill/Carrboro ZIP codes (27514, 27516, 27517, 27510) map reasonably well onto CHCCS's attendance area.

### Census Building Permits Survey (BPS)
**High-confidence, not independently re-verified this session.** Place-level annual new-housing-unit permit counts, available specifically for Chapel Hill and Carrboro as named "permit-issuing places," historical back to the 1990s (`census.gov/construction/bps`). Not geolocated to individual sites, but a clean long time series for "was housing production actually slowing before/after enrollment did."

---

## 6. Thematic Groupings for Further Exploration (suggested, not decided)

Rough sense of how this research naturally clusters by topic, for whoever picks up further work on this — offered as a starting point, not a locked plan:

- **Housing & development:** Zillow, Census ACS housing-cost tables, Chapel Hill Development Activity layer, Census Building Permits Survey, ACS Year Structure Built.
- **Demographics / population trends:** NC OSBM age-group projections, the still-unfound full Carolina Demography county report (worth pursuing via records request), Census ACS age structure.
- **School choice / homeschooling:** NC DNPE homeschool statistics (multi-decade trend), the closure study's own homeschool zone-of-residence tables, possibly NC DPI charter/private school enrollment data (not yet researched — new idea, would need its own feasibility check).
- **The decision process / redistricting & equity:** the closure study's full legal-context section, school attendance boundary GIS layers (for an actual redistricting map), the bond/facilities construction data, and the throughline of what this data can and can't tell us about the decisions being made.

---

## Ruled Out Entirely (don't re-investigate)

- **NC DPI Facility Needs Survey** for per-school capacity — aggregates by county only, conflates the two Orange County LEAs. (Section 2 above.)
- **Orange County parcel data** for year-built — schema doesn't include it; would need county tax/CAMA records, not located. (Section 3 above.)
