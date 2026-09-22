"""
SOLE PURPOSE OF THIS FILE: crosswalk three different ID systems for North
Carolina school districts, and attach Census population estimates to each
district using DPI's own agency_code.

The problem this solves: our enrollment data (NC DPI) identifies districts
by a DPI-specific code, like "681LEA" for CHCCS. Census population data
(SAIPE) identifies districts by a federal NCES ID, like "3700720" for
CHCCS. Those two IDs have no obvious relationship to each other -- you
can't derive one from the other by formula. A third source, the NCES
Common Core of Data (CCD) district directory, happens to list both IDs
side by side for every district, which is what makes the crosswalk
possible.

This file does the crosswalk ONCE and saves the result to
data/lea_population_crosswalk.csv. Nothing else in this project should
redo this logic -- the notebook just reads that output file. Rerun this
script (`python src/build_lea_population_crosswalk.py`) any time the raw
files in data_sources/ are updated.

Inputs (already saved in data_sources/, see INDEX.md):
- census_saipe_nc_school_districts_YYYY.txt, for YYYY 2019-2024
    Census SAIPE: total population, population ages 5-17, and children
    5-17 in poverty, one row per district per year. Fixed-width text.
- nces_ccd_lea_directory_nc_2022.json
    NCES Common Core of Data directory of NC districts. Contains both the
    NCES ID ("leaid") and DPI's own code ("state_leaid", e.g. "NC-681")
    for every district -- this is the crosswalk key.

Output:
- data/lea_population_crosswalk.csv, one row per (DPI agency_code, year):
    dpi_agency_code  DPI's district code, e.g. "681LEA" for CHCCS. Matches
                     the agency_code used throughout the rest of this project.
    year             Calendar year the estimate applies to (SAIPE calls
                     this the "school year ending" year).
    district_name    District name as SAIPE reports it.
    pop_total        SAIPE's estimated total population living in the
                     district's boundaries, all ages.
    pop_5_17         SAIPE's estimated population ages 5-17 living in the
                     district's boundaries -- this is the school-age
                     population figure used in Section 5.
    pov_5_17         SAIPE's estimated number of children ages 5-17 living
                     in families with income below the poverty line.
                     Not currently used elsewhere in this project.

Known limitation: NCES reassigned new district IDs to two entities partway
through this period -- Camp Lejeune Schools and Fort Bragg Schools each have
one NCES ID for 2019-2021 and a different one for 2022-2024. Our crosswalk
(built from a single 2022 CCD snapshot) only recognizes the newer ID, so
those two districts' 2019-2021 rows are silently dropped, not missing from
SAIPE itself. A third entity, Eastern Cherokee Reservation, has no DPI match
in any year and only appears in SAIPE for 2019-2021. None of these three are
part of DPI's 115 standard LEAs, so this doesn't affect the rest of the
project, but it would need fixing if either district were ever analyzed
directly.
"""

import json
import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_SOURCES = PROJECT_ROOT / "data_sources"
OUTPUT_FILE = PROJECT_ROOT / "data" / "lea_population_crosswalk.csv"

SAIPE_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

# SAIPE's school-district files are fixed-width text, not CSV. Each line is:
# state FIPS, 5-digit district code, district name, then three numbers
# (total population, population ages 5-17, children 5-17 in poverty), then
# a trailing filename/date stamp we don't need.
SAIPE_LINE_PATTERN = re.compile(
    r"^(\d{2}) (\d{5}) (.+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+sd\d\d-nc\.txt"
)


def load_saipe_population() -> pd.DataFrame:
    """Read all six years of SAIPE school-district files into one table."""
    rows = []
    for year in SAIPE_YEARS:
        file_path = DATA_SOURCES / f"census_saipe_nc_school_districts_{year}.txt"
        for line in open(file_path):
            match = SAIPE_LINE_PATTERN.match(line)
            if match:
                _, district_code, name, pop_total, pop_5_17, pov_5_17 = match.groups()
                rows.append(
                    {
                        "year": year,
                        "nces_leaid": "37" + district_code,  # "37" = North Carolina's state FIPS code
                        "district_name": name.strip(),
                        "pop_total": int(pop_total),
                        "pop_5_17": int(pop_5_17),
                        "pov_5_17": int(pov_5_17),
                    }
                )
    return pd.DataFrame(rows)


def load_nces_to_dpi_crosswalk() -> pd.DataFrame:
    """Build the NCES ID <-> DPI agency_code lookup from the CCD directory.

    CCD's "state_leaid" field looks like "NC-681" -- DPI's own LEA number
    with a state prefix. Our DPI tables use "681LEA" for the same district.
    """
    directory = json.load(open(DATA_SOURCES / "nces_ccd_lea_directory_nc_2022.json"))
    ccd = pd.DataFrame(directory["results"])
    ccd["dpi_agency_code"] = ccd["state_leaid"].str.replace("NC-", "", regex=False) + "LEA"
    return ccd[["leaid", "dpi_agency_code", "lea_name", "agency_type"]].rename(
        columns={"leaid": "nces_leaid"}
    )


if __name__ == "__main__":
    saipe = load_saipe_population()
    crosswalk = load_nces_to_dpi_crosswalk()

    merged = saipe.merge(crosswalk, on="nces_leaid", how="left")

    unmatched = merged[merged["dpi_agency_code"].isna()]["district_name"].unique()
    print(f"SAIPE district-years with no DPI match: {merged['dpi_agency_code'].isna().sum()}")
    for name in unmatched:
        print(f"  - {name}")
    print("These are federal/military/tribal schools, none of them part of DPI's")
    print("115 standard LEAs. Two of them (Camp Lejeune, Fort Bragg) DO have")
    print("2022-2024 data -- it shows up later in this file under a newer NCES ID")
    print("that the crosswalk does recognize. Only Eastern Cherokee Reservation is")
    print("limited to 2019-2021 in SAIPE. See the module docstring for detail.")

    matched = merged.dropna(subset=["dpi_agency_code"])
    print(f"\nMatched rows: {len(matched)} ({matched['dpi_agency_code'].nunique()} districts x up to {len(SAIPE_YEARS)} years)")

    output_columns = ["dpi_agency_code", "year", "district_name", "pop_total", "pop_5_17", "pov_5_17"]
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    matched[output_columns].to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved to {OUTPUT_FILE}")
