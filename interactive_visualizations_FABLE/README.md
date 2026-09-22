# Interactive visualizations: how far could Fable take this on its own?

This folder is a side experiment inside the CHCCS Enrollment Decline Deep Dive project. The
question it set out to answer was less about enrollment than about process: starting from the
data and analysis already in the parent project, how much could Claude Fable 5.1 build on its
own, given direction and review but not step-by-step instructions?

The answer is the set of self-contained HTML pages in `dashboard/`. Every one of them opens by
double-clicking, runs offline, and was built, checked and documented by Fable in a single
extended working session, with the project owner setting the questions, choosing between
options, reviewing the output and asking for changes.

## The deliverables

| Page | What it is |
|---|---|
| `dashboard/nc_enrollment_dashboard.html` | A four-tab exploratory dashboard of enrollment change across all 115 North Carolina districts and 100 counties, 2005-06 to 2024-25. Tab 0 is elementary schools, tab 1 is all grades, tab 2 is private schools, home schools and vouchers, tab 3 is enrollment against the school-age population. Animated choropleth maps with a Triangle inset, a year slider with policy and pandemic events marked, distribution strips, comparison line charts, unit-by-year heatmaps, statewide context charts, table views and notes. |
| `dashboard/nc_enrollment_podcast.html` | A three-chapter companion for talking through the CHCCS story with a guest: the district's elementary decline, how it compares across the state, and whether demographics explain it. Few controls, large type, every number computed from the data. Chapter 1 also carries the district's own forecast from the closure study. |
| `dashboard/nc_school_options.html` | A map and inventory of the charter and private schools a K-5 student could attend instead of CHCCS, within 5 and 25 miles of the district's center, with enrollment, grade spans, and 2023-24 voucher counts by school. |

The pages share the parent project's data and conventions: NC DPI's ADM table is the enrollment
measure, elementary enrollment is the sum of schools DPI classifies as elementary, Census SAIPE
supplies district population, and population is paired with the school year that ends in the
estimate year, exactly as the notebook does. On the notebook's 2019 to 2024 window the pages
reproduce its headline figures number for number.

## What Fable did on its own, and what it did not

Done autonomously, from a description of the goal: sourcing and downloading every additional
data set (DPI's location table, Census boundaries, twenty years of DNPE private and home school
reports in PDF and Word form, NCSEAA voucher reports, Census population estimates, SAIPE, NCES
school coordinates); parsing, joining and checking them; designing and coding the pages; writing
the tests; running a data audit and a headless-browser interaction test; reconciling the pages
against the CHCCS board's own documents; and writing the limitations document.

Decided by the project owner: the questions each page answers, the packaging (single files),
the county-only treatment of non-public data, the Triangle focus set, the timeline events, the
base year, the switch from index values to percent change, the population pairing convention,
and every visual correction along the way. Several defects were caught only because the owner
looked (a mislabeled talking point, an unreadable label, a chart that should not have been
indexed) and several only because Fable's own tests looked (a table view that crashed at county
level, a base-year cache bug, two typos in the state's own PDFs).

Findings that were not planned and came out of the work: DPI's district-level "E" rows are
average school sizes rather than elementary totals; pre-K is not in ADM; the Nash-Rocky Mount
demerger shows up as a boundary artifact in both enrollment and population; and the district's
own ten-year elementary forecast is nearly flat while the last five years averaged about −3% a
year.

Everything a careful reader should know before quoting a number is in [LIMITATIONS.md](LIMITATIONS.md).

## Data sources

1. **NC DPI School Report Card researcher data set, 2024-25 release.** Tables `rcd_adm`
   (Average Daily Membership by school and district, 2005-06 to 2024-25) and `rcd_location`
   (names, counties, grade spans, charter designation).
   https://www.dpi.nc.gov/data-reports/school-report-cards/school-report-card-resources-researchers
   Local: `data/raw/nc_dpi_rcd_adm_2024-25.csv` (the same file as the parent project's
   `data_sources/`), `data/raw/nc_dpi_rcd_location_2024-25.xlsx`.
2. **U.S. Census Bureau, 2023 Cartographic Boundary Files (1:500,000)**, unified school
   districts (NC) and counties. Local: `data/raw/cb_2023_37_unsd_500k.zip`, `data/raw/cb_2023_us_county_500k.zip`.
3. **NC Department of Administration, Division of Non-Public Education (DNPE).** Annual private
   school and home school statistical summaries, 2005-06 through 2025-26, and the January 2026
   private school directory. https://www.doa.nc.gov/divisions/non-public-education
   Local: `data/raw/dnpe_private/`, `data/raw/dnpe_home/`, `data/raw/dnpe_directory/`.
4. **NC State Education Assistance Authority (NCSEAA), Opportunity Scholarship Program.**
   Annual reports to the Joint Legislative Education Oversight Committee (2020-21, 2022-23,
   2023-24, 2024-25) and the legislative staff table of 2024-25 recipients by county and tier.
   Local: `data/raw/ncseaa/`.
5. **U.S. Census Bureau, Population Estimates Program.** County characteristics by age and sex:
   2000-2010 intercensal, Vintage 2019 and Vintage 2024. Local: `data/raw/census_popest/`.
6. **U.S. Census Bureau, Small Area Income and Poverty Estimates (SAIPE).** School district
   population and ages 5-17, 2005 through 2024. Local: `data/raw/saipe/`.
7. **CHCCS Board of Education documents.** The Dec. 11, 2025 retreat deck (district ADM
   projection) and the May 7, 2026 closure study (Carolina Demography K-5 forecast by school),
   as transcribed in the parent project. Local: `data/raw/chccs_board/`.
8. **NCES Private School Universe Survey 2021-22** (NC rows) and **NCES EDGE geocodes** for
   private (2021-22) and public (2023-24) schools. Local: `data/raw/nces/`.
9. **Timeline events** (verified Sept 2026): Session Law 2011-164 (charter cap removed);
   Session Law 2013-360 (Opportunity Scholarships created, first awards 2014-15); Session Law
   2023-134 (universal eligibility for 2024-25); House Bill 10 / Session Law 2024-57 (waitlist
   funded, veto override Nov. 20, 2024).

Vendored libraries, inlined into the HTML so it works offline: D3 v7.9.0 and topojson-client
v3.1.0 (copies in `dashboard/vendor/`).

## Conventions and limits, in brief

The full list is in [LIMITATIONS.md](LIMITATIONS.md), organized by source and by page.

- Year labels use the school year's ending year, as DPI does: "2024-25" is `year = 2025`.
  Population estimates are dated July 1 and paired with the school year that ends that June
  (July 2024 with 2023-24), the parent notebook's convention, so 2024-25 has no population value.
- Pre-K is not in ADM for any district or year. DPI notes its 2024-25 final ADM may be
  over-counted after a student information system transition.
- Elementary enrollment is the sum of ADM at schools DPI classifies as elementary (span E).
  DPI does not publish ADM by grade, and its district-level E rows are average school sizes.
- Non-public counts are county-level, self-reported to DNPE, and counted where the school or
  household is located. Two printed values in the state's reports were corrected as typos and
  one missing report year is interpolated; all are listed in the limitations file.
- SAIPE district estimates before 2010 understate fast-growing districts; use a base year of
  2010-11 or later for district population comparisons.

## Reproduce

```bash
cd interactive_visualizations_FABLE
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python src/fetch_raw_data.py                  # restores the large Census and NCES raw files that are not committed (about 90 MB)
python src/build_dashboard_data.py            # tab 0-1 data: ADM + geography -> dashboard_data.json
python src/build_choice_population_data.py    # tab 2-3 data: DNPE, NCSEAA, Census -> choice_population_data.json
python src/build_podcast_data.py              # CHCCS schools, Orange County ages, board forecast -> podcast_data.json
python src/build_school_options.py            # alternative schools within 25 miles, geocoded -> school_options.json (needs internet)
python tests/check_dashboard_data.py          # sanity checks on the cleaned data
python src/build_dashboard.py                 # -> dashboard/nc_enrollment_dashboard.html
python src/build_podcast.py                   # -> dashboard/nc_enrollment_podcast.html
python src/build_school_options_page.py       # -> dashboard/nc_school_options.html
python tests/smoke_headless.py                # drives every control in headless Chrome, fails on any JS error
```

The DPI, DNPE, NCSEAA and board files are committed in `data/raw/`. The Census boundary,
SAIPE, population-estimate and NCES files are not (they are large and freely re-downloadable);
`src/fetch_raw_data.py` restores them, skipping any that are already present. The cleaned data
and the HTML pages are committed, so nothing needs to be fetched or rebuilt just to open them.

## Layout

```text
README.md                           this file
LIMITATIONS.md                      caveats, corrections and QA performed
requirements.txt
.gitignore
src/
  build_dashboard_data.py           cleans and joins ADM, builds the TopoJSON, sums ADM by school grade span
  build_choice_population_data.py   parses DNPE reports and NCSEAA PDFs, stitches Census population files
  build_podcast_data.py             CHCCS schools, Orange County child ages, the board's forecast
  build_school_options.py           inventory and coordinates of alternative schools within 25 miles
  fetch_raw_data.py                 re-downloads the Census and NCES raw files that are not committed
  dashboard_template.html           tab 1 markup, CSS and JS, plus placeholders for the other pieces
  dashboard_pages23.html / .js      tabs 0, 2 and 3 (markup and the page engine that drives them)
  build_dashboard.py                inlines everything into dashboard/nc_enrollment_dashboard.html
  podcast_template.html             the three-chapter podcast companion
  build_podcast.py                  -> dashboard/nc_enrollment_podcast.html
  school_options_template.html      the school options map page
  build_school_options_page.py      -> dashboard/nc_school_options.html
data/
  raw/                              source files as downloaded; Census and NCES files are git-ignored, see fetch_raw_data.py
  cleaned/                          tidy CSVs and the JSON files the pages embed
dashboard/
  nc_enrollment_dashboard.html      the four-tab dashboard
  nc_enrollment_podcast.html        the podcast companion
  nc_school_options.html            the school options map
  vendor/                           d3.v7.min.js, topojson-client.min.js
tests/
  check_dashboard_data.py           plain-assert checks on the cleaned data
  smoke_headless.py                 headless-Chrome interaction test of the built pages
```
