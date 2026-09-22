# Limitations and considerations

What a careful reader should know before drawing conclusions from the NC Enrollment Shift
dashboard. Organized by the things that apply everywhere, then by data source, then by tab.
Each tab's page also carries the caveats most relevant to it in its "How to read this" card.

## 1. Conventions that apply everywhere

- **Year labels are the school year's ending year.** "2024-25" is NC DPI's `year = 2025`.
  Every series on every tab uses this convention.
- **Population estimates are dated July 1 and matched to the school year that ends that
  June.** The July 2024 estimate pairs with DPI year 2024, the 2023-24 school year. This is the
  pairing the CHCCS notebook uses, so the two agree number for number; it means the latest
  school year, 2024-25, has no population value yet (tab 3 opens on 2023-24 and the podcast's
  chapter 3 compares 2016-17 to 2023-24). The alternative pairing, with the school year that
  starts the following month, is equally defensible and shifts every population series by one
  column; on a 2019-2024 window it changes CHCCS's 5-17 change from −5.8% to −4.4%.
- **ADM is Average Daily Membership**, the state's funding count of students on the rolls,
  averaged over the year. It is not a headcount on a given day and not a count of resident
  children. DPI does not publish a methodology note for it in the researcher data set.
- **Students are counted where they attend; children are counted where they live.** Every
  comparison of enrollment to population inherits that mismatch. Districts that enroll
  transfers from outside their boundary, or counties whose private schools draw from
  neighbors, will look different from the resident picture.
- **Change metrics are sensitive to the base year.** The dashboards default to 2014-15 so
  that ten years are visible and the 2010 estimate seam (below) is avoided. Choosing 2018-19
  (the pre-pandemic peak for many districts) or 2019-20 will make almost every unit look worse.
- **Diverging color scales are clamped.** The legend shows the clamp (for example "≤ −25%" and
  "≥ +25%"); values beyond it are painted the deepest color. The tooltip and table always give
  the exact number. Spans are set from the 90th percentile of absolute values across all years
  so a year's map does not rescale while playing.

## 2. Source-by-source caveats

### NC DPI School Report Card data (tab 1 enrollment; tabs 2 and 3 as the public denominator)

- 115 traditional districts are those with a complete 20-year history. The two residential
  Schools for the Deaf (agency codes 296, 297) are excluded. Three federal and tribal districts
  (Fort Bragg, Camp Lejeune, Cherokee Central) are not NC LEAs and are absent from every count,
  which lowers county totals and county capture rates in Cumberland, Onslow, Swain and Jackson.
- Charter schools are assigned to the county of the school's address from DPI's location
  table. Two statewide virtual charters (NC Cyber Academy, NC Virtual Academy) are in the
  statewide charter total only, not in any county.
- City districts that straddle county lines (Kannapolis City in Cabarrus and Rowan; Nash-Rocky
  Mount in Nash and Edgecombe through 2023-24) are counted in the county of their central
  office, so a few county totals are approximate.
- **Nash-Rocky Mount demerger.** Senate Bill 248 (2023) split the district along the county
  line effective July 1, 2024. About 1,700 students on the Edgecombe side of Rocky Mount moved
  to Edgecombe County Public Schools, and the district was renamed Nash County Public Schools.
  The 2024-25 changes for both districts (Nash about −8%, Edgecombe about +20%) are that
  transfer, not families moving. The Census 2023 boundary file used for the maps still draws
  the pre-split shape.
- **2020-21** ADM was measured during remote and hybrid instruction and is the sharpest
  one-year drop in the series. One-year changes into and out of that year are a pandemic
  effect, not a trend.
- DPI's own agency-level state total row (`NC-SEA`) in the ADM table is not usable (it holds
  small, inconsistent values), so statewide totals are sums of the districts and charters.
- **Pre-K is not in ADM**, for any district or year. DPI's definition counts K-12 membership
  only (pre-K and visiting students are excluded), and the data agrees: DPI's separate pre-K
  enrollment table lists schools whose pre-K count exceeds their entire ADM (Sadie Saulter in
  Pitt County: ADM 32, pre-K 232; three others), which is impossible if pre-K were inside ADM.
  Two pre-K-plus-kindergarten centers carry ADM equal to a plausible kindergarten count. The
  rule is a state definition, so it applies uniformly to all 115 districts and all years; no
  district's ADM includes pre-K.
- **2024-25 may be over-counted.** DPI's table index notes that the transition to a new
  student information system "may have resulted in higher-than-expected student enrollment
  counts" in the 2024-25 final ADM. Treat 2024-25 one-year changes with that in mind; the
  statewide district total rose 0.06% that year after two years of decline.

### Elementary schools (tab 0)

- DPI reports ADM per school and per district, never per grade. "Elementary" on tab 0 is the
  sum of ADM at schools DPI classifies as span **E** (elementary, typically K-5 or PK-5) in
  that year's location table, with a second measure adding span **I** (K-8) schools.
  Elementary-grade students inside K-12 schools (span A), early colleges and special schools
  are not captured. Charter schools are mostly K-8 (span I), which is why the county measures
  that add charters change much more under E + I than under E alone.
- The district-level rows with category E, M or H in DPI's ADM table are the **average school
  size** in that category, not totals (CHCCS 2024-25: E = 411 = 4,522 students in 11 schools).
  They are not used anywhere in the dashboard. School rows sum exactly to the district total
  in every year, which is the check that makes the school-level sums trustworthy.
- Alleghany and Watauga have no E schools in any year (all K-8); Hyde, Jackson and Yadkin lack
  E schools in a few years. Under the E-only measure those units show "no value"; the E + K-8
  measure covers them.
- Between one and four school ADM rows a year statewide have no matching row in that year's
  location table and so no span; they are carried as "unclassified" so that school rows still
  sum exactly to district totals, and they never enter an elementary measure.
- A school that changes classification (for example a K-5 school that adds grades 6 to 8)
  moves between the E and I sums in the year it changes. Reclassifications are rare but can
  produce a one-year step in a small district.

### U.S. Census cartographic boundaries (maps)

- 2023 boundaries are applied to all 20 years. District boundaries do change; the Nash-Rocky
  Mount split is the only one large enough to matter in this period.
- The 1:500,000 files are generalized and then simplified further for file size (about 200 m).
  Shapes are fine for a state map, not for parcel-level work.
- One district polygon in the source is wound the wrong way for D3; it is rewound at load.

### NC DNPE private school and home school reports (tab 2)

- Private school enrollment is self-reported to DNPE and described by DNPE as the best available
  estimate. Only 757 of 930 schools completed the 2024-25 annual report. Reporting became a
  condition of receiving Opportunity Scholarship funds under the 2023 budget, so part of the
  2023-25 rise may be better reporting rather than more students.
- Home school student counts are **estimates**: DNPE counts registered home schools (a
  household, not a student) and estimates students from the schools that report. Single-year
  swings (the 2020-21 spike to 179,900 and the fall after) are partly estimation noise.
- The county tables are parsed from PDF and Word reports whose layouts changed several times.
  Every parsed year was checked: 100 counties present and county sums reconciled to each
  report's statewide total. Three discrepancies remain and are handled as follows:
  - 2013-14 home schools, Alexander County printed as "3" (304 and 337 in adjacent years):
    treated as a dropped-digit typo and interpolated (320).
  - 2022-23 home school students, Alamance County printed as 3,610, identical to Iredell's entry
    on the same line, with the report's own grand total 1,828 below the sum of its county rows:
    treated as a duplicated value and interpolated (2,344).
  - 2005-06 private school grand total (92,867) is 200 above the sum of the report's county
    rows (92,667). County rows are used as printed.
- The 2015-16 home school report is not published on DNPE's site; both home school series are
  interpolated for that year.
- Private school counts by county are available from 2007-08; the 2005-06 and 2006-07 reports
  do not tabulate them.
- 2025-26 figures come from the current-year reports (Word files published in 2026) and may be
  revised by DNPE.
- Students are counted where the school (or home) is located. Wake, Mecklenburg and Durham
  private schools draw from neighboring counties, so county non-public shares over-state
  Wake and under-state Orange, Franklin and Johnston to some degree.

### NCSEAA Opportunity Scholarship data (tab 2)

- County-of-residence counts exist for **one year only**, 2024-25, from a legislative staff
  table dated Feb. 3, 2025 (79,775 recipients across 99 counties). The annual report's June 30,
  2025 total is 80,472. Graham County's row could not be read from the table and is shown as
  missing.
- Statewide totals come from the annual reports for 2020-21, 2022-23, 2023-24 and 2024-25. The
  2021-22 report was not located, and reports before 2020-21 are not on the legislature's site
  in the same form, so the voucher bar chart has gaps.
- "New voucher students who left a district" uses the prior public school reported by the
  parent for new recipients, published for 2020-21 and 2022-23. Universal eligibility (2024-25)
  removed the prior-public-school requirement, so that table cannot continue. Rates per 1,000
  ADM are small everywhere and should be read as a floor on public-to-private movement, since
  students leaving without a voucher are not counted.

### U.S. Census population estimates (tab 3 counties)

- Three vintages are stitched: 2000-2010 intercensal (used for 2006-2009), Vintage 2019
  (2010-2019) and Vintage 2024 (2020-2024). Each vintage is benchmarked to a different census,
  so there are seams at 2010 and 2020. The 2020 seam moves some small counties' 5-17 counts by
  10% or more in one year (Duplin −17%, Hyde −13%, Gates −11%). Treat 2018-19 to 2019-20
  population changes with care.
- The intercensal file has only 5-year age groups. Ages 5-17 for 2006-2009 are estimated by
  scaling ages 5-19 with each county's own July 2010 ratio of (5-17)/(5-19). A flat 3/5 share
  of the 15-19 group was rejected because college towns (Orange, Watauga, Pitt, Jackson) have
  many 18- and 19-year-olds.
- Ages 5-17 is not exactly K-12. Some 5-year-olds are not yet in kindergarten and some
  18-year-olds are still enrolled, so "public students per 100 school-age children" can exceed
  100 and its level should not be over-interpreted; its change over time is the useful part.

### U.S. Census SAIPE school district estimates (tab 3 districts)

- SAIPE estimates before the 2010 release were built on 2000 Census geography and
  under-estimate fast-growing districts. Chapel Hill-Carrboro's 5-17 population steps from
  about 9,600 (2008-09) to about 11,000 (2009-10) to about 12,400 (2010-11) for that reason.
  Thomasville City, Onslow, Union and Camden show similar steps. **Use a base year of 2010-11
  or later for district-level population comparisons.**
- SAIPE 2024 adopted the post-demerger Nash and Edgecombe boundaries. Under the notebook's
  pairing that estimate lands on 2023-24, one year before the students transferred in ADM, so
  the Nash and Edgecombe enrollment-versus-population comparisons for 2023-24 are not
  meaningful. Earlier years compare the old district to the old boundary.
- SAIPE estimates are controlled to county totals, so district sums within a county match the
  county estimate closely from 2010 on. Differences of 3% to 15% remain in counties with a
  federal or tribal district (Cumberland, Onslow, Swain, Jackson) or a district that crosses
  the county line (Nash/Edgecombe before 2024-25, Cabarrus/Rowan).
- SAIPE is designed for poverty estimation; the total and 5-17 population columns are
  model-based and carry sampling and modeling error that the Census does not publish for
  those columns.

## 3. Tab-specific interpretation notes

### Tab 0: Elementary schools

- Same metrics and caveats as tab 1, applied to elementary-school ADM. The "elementary share
  of district ADM" measure moves both when elementary enrollment changes and when middle and
  high school enrollment changes; a district whose elementary share is falling while its total
  is flat is losing young families or gaining older students, and the two cannot be separated
  here.
- The private, home school and population tabs cannot be cut to elementary grades, so tab 0
  has no non-public or population comparison.

### Tab 1: Where are students going?

- "Below own peak" is always zero or negative and cannot show growth beyond a prior peak.
- The "3-year average annual change" starts in 2008-09 (it needs three one-year changes).
- The charter share metrics count charter students by school location, so a county with a
  large charter that draws from neighbors will show a high share.

### Tab 2: Private and home schools

- The county level is the only level available. Chapel Hill-Carrboro City Schools and Orange
  County Schools share Orange County's numbers. An estimated district split was considered and
  rejected as modeled rather than observed.
- "Non-public share of all students" divides private plus home by district ADM plus charter
  ADM plus private plus home, all counted by location. It is a share of students counted in
  NC, not a share of resident children; use "per 100 school-age children" for the latter.
- The line chart is blank for the two single-year voucher measures by design.

### Tab 3: Population vs. enrollment

- The headline "gap" is cumulative enrollment change minus cumulative 5-17 population change
  since the base year, in percentage points. It is a comparison of two rates, not a count of
  students, and it inherits the population seams above. With a 2014-15 base it is unaffected
  by the 2010 seam; a base before 2010-11 makes district gaps unreliable. 2024-25 has no
  population value, so gap, quadrant and capture measures show "no value" for that year.
- The quadrant view classifies on the sign of each change. Units near zero on either axis flip
  class from year to year; the scatter chart shows how close to a boundary a unit sits.
- For districts, "public enrollment" is the district's own ADM, so a falling capture rate can
  mean growth in charters as much as private or home schooling. For counties it includes
  charters located in the county.

## 4. What the dashboard can and cannot support

It can support statements like: "CHCCS enrollment fell 8.4% since 2014-15 while its
school-age population fell 5.3%, so roughly a third of the decline is more than demographics";
"non-public enrollment in Orange County grew from about 2,100 to about 2,300 over the same
period while public ADM fell"; "statewide, one in four K-12 students is now outside a
traditional district school."

It cannot support statements about *individual students moving* between sectors (no student
level data), about *why* families chose one sector (no survey data), about the *effect of
vouchers* on enrollment (one year of county voucher data, no counterfactual), or about
sub-county non-public enrollment (not published).

## 5. Quality checks performed

- `tests/check_dashboard_data.py`: structural checks on both cleaned JSON files (115 districts,
  100 counties, complete series, county sums equal district sums, statewide totals equal sums,
  known figures from the source reports such as CHCCS 2024-25 ADM of 11,065 and Orange County's
  616 voucher recipients).
- Data audit during review: year-over-year anomaly scans of every DNPE, SAIPE and county
  population series; reconciliation of parsed county rows to each report's printed total;
  district-sum-versus-county comparisons for population; capture-rate and non-public-share
  outlier lists. Findings are the corrections and caveats listed above.
- `tests/smoke_headless.py`: drives every level, measure, view, base year, sort order, table
  view, map click and play button on all four tabs in headless Chrome and fails on any
  JavaScript error. It caught one bug in review (the tab-1 table view at county level), which
  is fixed.
- Visual review of light and dark mode screenshots of every tab.

## 5a. Reconciliation with CHCCS's own documents

The podcast page and the dashboards were checked against the district's Board of Education
retreat deck (Dec. 11, 2025) and the closure study (May 7, 2026), both saved in the parent
CHCCS project and transcribed into `data/raw/chccs_board/`.

| Figure | CHCCS document | This project | Result |
|---|---|---|---|
| District ADM, FY2025 (2024-25) | 11,065 (deck p9) | 11,065 | exact match |
| District ADM, FY2026 (2025-26) | 10,758 projected/actual (deck p9) | not in DPI data yet | one year past the data; implies −2.8%, in line with the trend |
| Number of elementary schools | "one of eleven" (study) | 11 span-E schools | match |
| K-5 ADM, 2025-26 | 4,294 (study p14, Carolina Demography) | 4,522 for 2024-25 | one year apart; −5.0% would be the steepest one-year drop since COVID |
| Per-school 2025-26 (study) vs 2024-25 (DPI) | e.g. Estes Hills 324 / 324, Glenwood 394 / 390, Rashkis 367 / 427, Northside 335 / 392 | | every school within one plausible year's move; Rashkis and Northside fall most |
| K-5 forecast 2029-30, 2030-31, 2035-36 | 4,191, 4,177, 4,183 (study p14, p36) | transcribed table sums 4,191, 4,177, 4,184 | match (one-student rounding in the transcription) |
| Five-year ADM projection | FY2027 10,502 … FY2031 9,535, "over 1,200" loss (deck p8) | reproduced on the podcast page as the district forecast | match |

Two things the reconciliation surfaced:

- The closure study's current-year figures are described as "based on the October 2025 20th-day
  enrollment", a point-in-time count, while DPI ADM is a full-year average. The two are close
  but not the same measure, so the 2024-25 to 2025-26 step should be read as approximate.
- The district's forecast is nearly flat after 2025-26 (4,294 to 4,184 over ten years, about
  −0.3% a year) while the last five years of actual elementary ADM averaged about −3% a year.
  The podcast page shows both so the contrast is visible; it does not resolve it.

### School options page: the alternatives (school inventory and map)

- **Universe.** Charter schools come from DPI's 2024-25 location table (with 2024-25 ADM);
  private schools come from the NCES Private School Universe Survey for 2021-22 (grade span,
  enrollment, religious/nonsectarian typology) plus the NC DNPE private school directory dated
  January 2026 for schools that opened or were missed since. Directory-only schools carry no
  grade span or enrollment and are shown with dotted markers and an asterisk. Preschools that
  appear in the directory are included only if they are listed as private schools there.
- **Coordinates.** NCES EDGE geocodes (2023-24 public, 2021-22 private). Directory-only
  schools were geocoded with the Census Bureau geocoder from their street address; ten
  addresses could not be matched (mostly suites, compound addresses or new streets) and are
  left off the map. A few charters statewide could not be matched to NCES by name; none of
  them is within 25 miles.
- **Distance** is straight-line from the geographic centroid of the CHCCS boundary
  (35.922 N, 79.074 W), not driving distance, and the 5-mile and 25-mile rings are circles on
  the ground, not commuting sheds. Charter schools have no attendance boundaries, so distance
  is a proxy for practicality, not eligibility.
- **"Serves K-5"** means the school's reported grade span overlaps kindergarten through
  grade 5. Private enrollment counts cover all grades the school offers, not K-5 only, and are
  from the 2021-22 survey. The 2024-25 voucher counts by school are from NCSEAA's 2023-24
  report and are matched by name.
- Home school and virtual charter figures are county- and state-level counts, not places on
  the map.

## 6. Open items

- Graham County's 2024-25 voucher count is missing (its row is absent from the PDF's text layer).
- NCSEAA's 2021-22 annual report and any county-level voucher data for years other than
  2024-25 were not located.
- DNPE's 2015-16 home school report is not online; the year is interpolated.
- The Census 2024 or later boundary file, once published, would draw the post-demerger Nash
  and Edgecombe districts correctly.
