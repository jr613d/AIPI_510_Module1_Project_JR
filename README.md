# An analysis of enrollment decline in Chapel Hill-Carrboro City Schools

AIPI 510 — Module 1 Project: Data Storytelling

---

## Overview

In 2026, Chapel Hill-Carrboro City Schools (CHCCS) proposed closing three elementary schools. The stated reason was falling enrollment. This project takes a deeper look at the data behind enrollment decline to explore: **is enrollment falling because there are fewer children in Chapel Hill, or because the children who live there are going somewhere else?**

Those two explanations look identical in an enrollment table, and they point to opposite responses. A district shrinking because families aged out of the school system has a demographic problem no board can fix. A district shrinking because families are choosing charters, private schools, or other towns has a different problem entirely — one a board might be able to do something about.

To separate them, we stacked four measures of the same community on top of each other, 2019 to 2024:

| Layer | 2019 | 2024 | Change |
|---|---:|---:|---:|
| Total population living in the district | 93,239 | 93,897 | **+0.7%** |
| School-age population (ages 5–17) | 13,065 | 12,309 | **−5.8%** |
| K–12 enrollment (Average Daily Membership) | 12,335 | 11,266 | **−8.7%** |
| Elementary enrollment | 5,488 | 4,583 | **−16.5%** |

Each layer is a subset of the one above it, and each falls faster than the one above it. Chapel Hill is not emptying out. It is getting older, and its elementary schools are absorbing the sharpest end of that.

### The engineered feature: capture rate

The number that makes the decomposition possible is what we call **capture rate** — the share of a district's school-age residents that the district actually enrolls:

```
capture_rate = K-12 enrollment (ADM) / school-age population (5-17)
```

For CHCCS it fell from **0.9441 in 2019 to 0.9153 in 2024**. Holding the 2019 rate fixed and applying it to the 2024 population gives a counterfactual enrollment, and the gap between that and the real 2024 number splits the decline in two:

| Component | Students | Share |
|---|---:|---:|
| Fewer school-age children living in the district | −714 | **67%** |
| A falling capture rate (kids who live here, enroll elsewhere) | −355 | **33%** |
| **Total decline, 2019–2024** | **−1,069** | 100% |

Two-thirds demographics, one-third something else. We can size that one-third. We cannot open it — charter, private, homeschool, and priced-out all look identical in this data: an absence.

### Other findings

- **CHCCS's elementary decline is steep but not unique.** At −16.5%, it ranks **17th of 113** NC districts with elementary schools. The median district lost 7.3%. **100 of 113 districts declined.** Sixteen declined more steeply than CHCCS. This is a statewide pattern with a sharp local edge, not a CHCCS-specific crisis.
- **The window you choose changes the story.** Measured from 2006, CHCCS enrollment is up 0.8% and ranks 90th of 115. Measured from 2019, it is down 10.3% and ranks 35th. Same district, same data.
- **A null result worth keeping.** Four candidate explanations — economically disadvantaged share (r = −0.16), chronic absenteeism (r = −0.02), Pre-K enrollment (r = 0.04), per-pupil expenditure (r = −0.62) — explain nothing. The one strong correlation is circular: enrollment is the denominator of per-pupil spending, so a district losing students mechanically shows higher spending per pupil.
- **A data quality trap.** "Elementary enrollment" is not a number anyone publishes. NC DPI has no grade-level enrollment table, so it has to be built by summing schools labeled elementary — which quietly assumes every elementary-aged child attends a school labeled elementary. That holds for CHCCS (0.00% of its students are in K–8 or K–12 schools). It breaks badly elsewhere: 8 NC districts have more than 20% of their students in combined-grade schools, one of them 93.3%.

### Who this is for

Parents, teachers, and board members in Chapel Hill-Carrboro weighing a school closure decision — and, more broadly, anyone in a district facing the same conversation. Every NC district can be swapped into these scripts by changing one constant.

---

## Repository structure

```
.
├── README.md                     <- you are here
├── requirements.txt              <- pinned Python dependencies
├── COLLABORATION.md              <- how this project was built, section by section
├── RESEARCH_APPENDIX.md          <- every source explored, including dead ends
│
├── data_sources/                 <- RAW data, exactly as downloaded (nothing modified)
│   └── INDEX.md                  <- what each raw file is and where it came from
│
├── data/
│   ├── lea_population_crosswalk.csv   <- generated: Census population by DPI district code
│   └── cleaned/                       <- generated: all analysis-ready tables
│
├── figures/                      <- generated: all charts
│
├── notebooks/
│   └── chccs_enrollment_exploration.ipynb   <- the narrative analysis
│
└── src/                          <- the pipeline (see below)
```

---

## Datasets

### 1. NC DPI School Report Card data (primary source)

North Carolina Department of Public Instruction publishes its School Report Card data as a bulk download for researchers: two ZIP files containing roughly 67 separate tables — enrollment, accountability, spending, attendance — each keyed by `year` and an `agency_code` identifying a school, a district (LEA), or the state. It is less a dataset than a warehouse of them released together.

Five of those tables are used here:

| Table | What it provides | Years |
|---|---|---|
| `rcd_adm` | Average Daily Membership — the state's official enrollment count, by school and by district. **The anchor of the whole analysis.** | 2006–2025 |
| `rcd_location` | One row per school per year with its grade span (`PK:05`, `09:12`) and grade-span category. This is what makes elementary-only enrollment possible at all. | 2006–2025 |
| `rcd_acc_eds` | % economically disadvantaged students, by district | 2017–2025 |
| `rcd_chronic_absent` | Chronic absenteeism rate, by district and subgroup | 2018–2025 |
| `rcd_funds2` | Per-pupil expenditure, by district and spending category | 2019–2025 |
| `rcd_pk_enroll` | Pre-Kindergarten enrollment, by district and subgroup | 2018–2025 |

**Citation:** North Carolina Department of Public Instruction. *School Report Card Resources for Researchers*, 2024–25 release. https://www.dpi.nc.gov/data-reports/school-report-cards/school-report-card-resources-researchers

**Two things to know before using it:**

- **Masking.** Any count under 10, or any percentage below 5% or above 95%, is suppressed. District-wide totals are unaffected; small schools and small subgroups are not.
- **Excluded LEAs.** Nine agency codes (209, 269, 298, 299, 679, 996–999) are left out of the ADM release entirely. Three were confirmed against the NCES directory as federal or tribal schools: 209 is Cherokee Central (Bureau of Indian Education), 269 is Fort Bragg and 679 is Camp Lejeune (both Department of Defense).
- **No published methodology.** DPI does not document how ADM itself is measured — whether it is a first-week count, a full-year average, or something else. The public-facing pages explain the school letter-grade formula, not the underlying enrollment numbers. This is the single largest unknown in the analysis.

### 2. Census SAIPE school-district population estimates

The Census Bureau's Small Area Income and Poverty Estimates program publishes total population, population ages 5–17, and children 5–17 in poverty for every school district in the country, annually. This is the denominator of the capture rate.

**Citation:** U.S. Census Bureau. *Small Area Income and Poverty Estimates (SAIPE): School District Estimates*, 2019–2024. https://www.census.gov/programs-surveys/saipe.html

**Caveats:** these are **modeled estimates**, not counts, and they carry margins of error. They use a July 1 reference date, so they do not line up perfectly with a school year. The latest available release is 2024, which is why the capture-rate analysis ends in 2024 while the enrollment analysis runs to 2025.

### 3. NCES Common Core of Data district directory (crosswalk only)

SAIPE identifies districts by a federal NCES ID (`3700720` for CHCCS). DPI identifies them by its own code (`681LEA`). There is no formula converting one to the other. The NCES CCD district directory lists both side by side, which is what makes the join possible. It is used for nothing else.

**Citation:** U.S. Department of Education, National Center for Education Statistics. *Common Core of Data, Local Education Agency Directory*, 2022. Accessed via the Urban Institute Education Data API, https://educationdata.urban.org/

### 4. CHCCS board documents (context, not analysis)

Two PDFs from the district itself — the December 2025 board retreat deck and the May 2026 closure study — are included in `data_sources/` as the origin of the claim this project examines. They were used to verify one number (CHCCS's 2025 district total of 11,065, which matches DPI's `rcd_adm` exactly) and to establish what the district said and when. No figure in the analysis is extracted from them.

---

## Reproducing the analysis

### Prerequisites

Python 3.10 or newer. Everything else installs from `requirements.txt`.

### Step 1 — Set up the environment

```bash
git clone <this-repo>
cd "CHCCS Enrollment Decline Deep Dive"

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2 — Run the pipeline

Four scripts, in this order. Each one is independently runnable and prints what it produced.

```bash
python src/build_lea_population_crosswalk.py   # 1. join Census IDs to DPI IDs
python src/preprocess.py                       # 2. raw DPI tables -> clean tables
python src/run_eda.py                          # 3. data quality report + EDA charts
python src/build_features.py                   # 4. capture rate + final charts
```

**What each stage does:**

| Script | Reads | Writes | Purpose |
|---|---|---|---|
| `build_lea_population_crosswalk.py` | 6 SAIPE text files, NCES CCD JSON | `data/lea_population_crosswalk.csv` | Matches federal NCES district IDs to DPI agency codes so Census population can be joined to DPI enrollment. Runs once; nothing else redoes this logic. |
| `preprocess.py` | 6 raw DPI CSVs, the crosswalk | 4 files in `data/cleaned/` | Splits the three aggregation levels stacked in `rcd_adm`, builds elementary enrollment from school-level rows, and merges five district-level variables into one trend table. |
| `run_eda.py` | raw `rcd_adm`, `data/cleaned/` | 10 charts in `figures/` | Prints a structure report, an 8-dimension data quality assessment, and the exploratory comparisons. Deliberately reads the **raw** file for the quality checks — those are about what was published, not about what our preprocessing left behind. |
| `build_features.py` | `data/cleaned/` | 3 files in `data/cleaned/`, 3 charts | Builds the capture rate and the four nested layers, decomposes the decline, and benchmarks CHCCS against all 113 districts with a three-way sensitivity check. |

Total runtime is well under a minute. `src/common.py` holds the folder paths and the one shared percent-change function; it is not run directly.

### Step 3 — Read the narrative

```bash
jupyter lab notebooks/chccs_enrollment_exploration.ipynb
```

The notebook is where the reasoning, the interpretation, and the written discussion of limitations and ethics live. The scripts are the reproducible version of the same analysis: every number and chart in the notebook regenerates from them.

### Changing the district

Everything is parameterized on one constant. To run this for any other NC district, change `CHCCS` in `src/common.py` to that district's DPI agency code (e.g. `"680LEA"` for Orange County Schools) and rerun steps 2–4.

### Two legacy scripts

`src/fetch_dpi_adm.py` and `src/extract_pdf_tables.py` are from an earlier pass at this project and are **not part of the pipeline above**. They are kept because `extract_pdf_tables.py` documents how the board deck's tables were pulled, including which numbers were machine-parsed and which were transcribed by hand from a chart image — methodological provenance worth preserving even though those tables are not used here.

Note that `fetch_dpi_adm.py` reads `nc_dpi_rcd_adm_2024-25.xlsx`, which is not committed (see the data section below), so it will not run on a fresh clone without re-downloading that file. Nothing in the main pipeline has this problem.

---

## Data included in this repository

**Raw data** is in `data_sources/` (~41 MB), committed exactly as downloaded. Nothing in that folder has been modified.

Several DPI tables originally arrived as `.xlsx` and were converted to `.csv` with no other change. Only the `.csv` versions are committed — the originals are gitignored, because carrying both would have doubled the repo to hold a second copy of the same numbers. `data_sources/INDEX.md` records which files were converted and where to re-download the originals if you want to verify a conversion yourself. Every script in the pipeline reads the `.csv` versions, so nothing in the analysis depends on the missing files.

Two indexes cover the folder: `data_sources/INDEX.md` describes every file the analysis uses directly, and `RESEARCH_APPENDIX.md` covers everything else that was explored, including the dead ends and how each was ruled out. Sources that turned out not to work are documented there by conclusion and URL rather than carried as files — the finding is what's useful, not eleven megabytes of PDF. One unused source is kept in the folder: NC DNPE homeschool statistics, a live lead for future work, held back here only because its counts are county-level households rather than CHCCS students.

**Cleaned data** is in `data/cleaned/` and is fully regenerated by the pipeline above — it is committed so results can be inspected without running anything, but nothing in it is hand-edited.

| File | Grain | Contents |
|---|---|---|
| `district_adm.csv` | district × year | Total ADM, 119 districts, 2006–2025 |
| `school_adm_with_spans.csv` | school × year | ADM plus grade-span category, 51,466 rows |
| `elementary_adm_by_district.csv` | district × year | Elementary ADM and elementary school count |
| `lea_trend_table.csv` | district | % change 2019–2025 in five variables, 115 districts |
| `chccs_layers.csv` | year | The four nested layers and the capture rate, 2019–2024 |
| `elementary_change_by_district.csv` | district | Elementary ADM 2019 and 2024 plus % change, 113 districts |
| `enrollment_correlations.csv` | variable | Each candidate variable's correlation with enrollment change |
| `../data/lea_population_crosswalk.csv` | district × year | Census population by DPI agency code, 699 rows, 118 districts |

**Nothing here is restricted.** Every source is a public download requiring no key or account. A note on one gap: elementary-*aged* population (ages 5–9, which would let the capture rate be computed for elementary specifically, rather than K–12) requires a free Census API key for the ACS age-structure tables. That is the main unfinished piece of this analysis, and it is why the elementary layer is reported as enrollment change rather than as an elementary capture rate.

---

## Limitations and ethics

Both are treated at length in Sections 9 and 10 of the notebook. In brief:

- **We answered two-thirds of the question.** The 33% of the decline attributable to a falling capture rate is a number we can size but not explain. Charter, private, homeschool, and priced-out are indistinguishable here.
- **"Elementary enrollment" is constructed, not given**, and the construction is only safe for districts without combined-grade schools. The sensitivity check reruns the key comparison three ways to show CHCCS's position holds (14th–17th percentile under every treatment).
- **Privacy protection creates a representation blind spot.** Suppressing counts under 10 is the right call for children's privacy, and its side effect is that small districts and small subgroups systematically drop out of statewide comparisons. Ten of 115 districts fell out of one analysis for exactly this reason.
- **Enrollment is a measurable proxy for something unmeasurable.** ADM counts how many students a district serves. It says nothing about whether a school is good, or what it means to a neighborhood.
- **The data confirms the district's premise and justifies none of its specific decisions.** Enrollment is really falling; elementary really is falling more than twice as fast as the median NC district. But no enrollment table can say *which* school should close, or whether closing one beats redistricting. Those are questions about who absorbs a loss.
- **Nothing here touches student-level data.** Every figure is a district or school aggregate from a public release, well clear of FERPA.

---

## A note on how this was built

This analysis was developed collaboratively with an AI assistant, one section at a time. [COLLABORATION.md](COLLABORATION.md) describes how that worked, and [RESEARCH_APPENDIX.md](RESEARCH_APPENDIX.md) records every source explored along the way. Several findings in this repository exist because a first pass got something wrong and the error was caught: the `category_code` field was initially read as a grade-span breakdown of district enrollment when it is a per-school average, and an early version of the elementary benchmark filtered out districts that opened or closed a school, which discarded 26 districts to solve a problem that did not exist. Both corrections are documented in place rather than quietly fixed.
