"""
PREPROCESSING -- stage 2 of 4.

Turns the raw NC DPI files in data_sources/ into a handful of small, clean
tables in data/cleaned/ that the EDA and feature-engineering scripts read.

Run it with:
    python src/preprocess.py

Run src/build_lea_population_crosswalk.py first -- this script reads its
output (data/lea_population_crosswalk.csv).

What "preprocessing" means here, concretely:

1. The raw rcd_adm table mixes THREE levels of aggregation in one column:
   individual schools, district (LEA) totals, and one statewide total. Any
   analysis has to pick a level first. We split them apart.

2. Within the district rows, category_code decides what a row means. A
   BLANK category_code is the district's true total ADM -- it equals the
   sum of that district's individual schools exactly. The rows tagged
   E/M/H/A/I/T are NOT a breakdown of that total; they are the AVERAGE ADM
   per school of that grade span. Summing them would be meaningless. (This
   is verified in run_eda.py, and was a real trap we fell into first time.)

3. DPI publishes no grade-level enrollment table, so "elementary
   enrollment" does not exist as a number anywhere. It has to be BUILT by
   summing school-level ADM for the schools that rcd_location marks as
   elementary. That reshaping happens here.

4. The four comparison tables (economically disadvantaged, chronic
   absenteeism, per-pupil expenditure, Pre-K) each carry subgroup or
   category breakdowns. We filter each to its one overall total row, then
   merge all five variables into a single district-level trend table.

Outputs written to data/cleaned/:
    district_adm.csv               one row per (district, year): total ADM
    school_adm_with_spans.csv      one row per (school, year): ADM + grade span
    elementary_adm_by_district.csv one row per (district, year): elementary ADM
    lea_trend_table.csv            one row per district: 5 variables' % change
"""

import pandas as pd

from common import DATA_CLEANED, DATA_SOURCES, PROJECT_ROOT, pct_change_by_lea

# 2019 is the common start year for the five-variable comparison. It is not
# an arbitrary choice: rcd_funds2 (per-pupil expenditure) does not start
# until 2019, which is the latest starting point of the five tables. Using
# any earlier year would mean comparing variables over different windows.
START_YEAR = 2019
END_YEAR = 2025


def load_district_adm():
    """District-level total ADM, one row per (district, year)."""
    adm = pd.read_csv(DATA_SOURCES / "nc_dpi_rcd_adm_2024-25.csv", dtype={"agency_code": str})

    # Keep district rows only, and only the blank-category_code rows -- see
    # points 1 and 2 in the module docstring for why.
    district = adm[adm["agency_code"].str.endswith("LEA") & adm["category_code"].isna()]

    return district[["year", "agency_code", "avg_student_num"]].rename(
        columns={"avg_student_num": "total_adm"}
    )


def load_school_adm_with_spans():
    """School-level ADM joined to each school's grade span, per year.

    rcd_location gives one row per school per year with a grade-span
    category:
        E = elementary only          I = elementary + middle (K-8)
        M = middle only              A = elementary + middle + high (K-12)
        H = high school only         T = middle + high
    It also gives lea_code, which is how a school gets tied back to its
    district.
    """
    adm = pd.read_csv(DATA_SOURCES / "nc_dpi_rcd_adm_2024-25.csv", dtype={"agency_code": str})

    # School rows: not a district total, not the state total, and (as with
    # districts) the blank-category_code row is the school's real total.
    schools = adm[
        ~adm["agency_code"].str.endswith("LEA")
        & (adm["agency_code"] != "NC-SEA")
        & adm["category_code"].isna()
    ]

    location = pd.read_csv(
        DATA_SOURCES / "nc_dpi_rcd_location_2024-25.csv",
        dtype={"agency_code": str, "lea_code": str},
        low_memory=False,
    )
    spans = location[["year", "agency_code", "category_code", "lea_code"]].rename(
        columns={"category_code": "span"}
    )

    merged = schools.merge(spans, on=["year", "agency_code"], how="left")
    return merged[["year", "agency_code", "lea_code", "span", "avg_student_num"]]


def build_elementary_adm(school_adm):
    """Sum elementary-school ADM up to the district level, per year.

    This is the number DPI does not publish. We also carry the count of
    elementary schools, because it is the first thing to check before
    believing a decline: if a district closed two schools, a falling total
    means something different than if the school count held steady.

    IMPORTANT CAVEAT, carried through the whole project: this counts only
    schools marked "E". Elementary-aged children attending a K-8 or K-12
    school are invisible to it. That is harmless for CHCCS (0.00% of its
    students are in such schools) but wrong for districts built around
    combined-grade schools. run_eda.py quantifies the exposure for every
    district; build_features.py reruns the key comparison three ways to
    show the conclusion does not depend on it.
    """
    return (
        school_adm[school_adm["span"] == "E"]
        .groupby(["year", "lea_code"])
        .agg(elem_adm=("avg_student_num", "sum"), n_elem_schools=("agency_code", "nunique"))
        .reset_index()
    )


def build_trend_table(district_adm):
    """Merge five district-level variables into one table of % changes.

    Each of the four comparison tables has its own idea of a "total" row,
    so each needs its own filter before the percent change is computed:
      - acc_eds   : district rows only (no subgroup column)
      - chronic   : subgroup == "ALL"
      - funds2    : expenditure_category == "TOTAL"
      - pk_enroll : subgroup == "ALL"
    """
    eds = pd.read_csv(DATA_SOURCES / "nc_dpi_rcd_acc_eds_2024-25.csv", dtype={"agency_code": str})
    chronic = pd.read_csv(DATA_SOURCES / "nc_dpi_rcd_chronic_absent_2024-25.csv", dtype={"agency_code": str})
    funds = pd.read_csv(DATA_SOURCES / "nc_dpi_rcd_funds2_2024-25.csv", dtype={"agency_code": str})
    pk = pd.read_csv(DATA_SOURCES / "nc_dpi_rcd_pk_enroll_2024-25.csv", dtype={"agency_code": str})

    eds_lea = eds[eds["agency_code"].str.endswith("LEA")]
    chronic_lea = chronic[chronic["agency_code"].str.endswith("LEA") & (chronic["subgroup"] == "ALL")]
    funds_lea = funds[funds["agency_code"].str.endswith("LEA") & (funds["expenditure_category"] == "TOTAL")]
    pk_lea = pk[pk["agency_code"].str.endswith("LEA") & (pk["subgroup"] == "ALL")]

    trend_table = pd.DataFrame({
        "enrollment_pct_change": pct_change_by_lea(district_adm, "total_adm", START_YEAR, END_YEAR),
        "eds_pct_change": pct_change_by_lea(eds_lea, "pct_eds", START_YEAR, END_YEAR),
        "chronic_absent_pct_change": pct_change_by_lea(chronic_lea, "pct", START_YEAR, END_YEAR),
        "ppe_pct_change": pct_change_by_lea(funds_lea, "total_ppe", START_YEAR, END_YEAR),
        "pk_enroll_pct_change": pct_change_by_lea(pk_lea, "count_masked", START_YEAR, END_YEAR),
    })

    # Some agency_codes ending in "LEA" are special-purpose codes, not real
    # school districts. Enrollment is every table's anchor variable, so
    # requiring a valid enrollment change is what narrows this to the 115
    # real districts.
    return trend_table.dropna(subset=["enrollment_pct_change"])


if __name__ == "__main__":
    DATA_CLEANED.mkdir(parents=True, exist_ok=True)

    print("Loading district-level ADM...")
    district_adm = load_district_adm()
    district_adm.to_csv(DATA_CLEANED / "district_adm.csv", index=False)
    print(f"  {len(district_adm):,} district-years, {district_adm['agency_code'].nunique()} districts, "
          f"{district_adm['year'].min()}-{district_adm['year'].max()}")

    print("Loading school-level ADM and joining grade spans...")
    school_adm = load_school_adm_with_spans()
    school_adm.to_csv(DATA_CLEANED / "school_adm_with_spans.csv", index=False)
    missing_span = school_adm["span"].isna().sum()
    print(f"  {len(school_adm):,} school-years, {missing_span:,} with no grade span in rcd_location")

    print("Building elementary enrollment per district-year...")
    elementary = build_elementary_adm(school_adm)
    elementary.to_csv(DATA_CLEANED / "elementary_adm_by_district.csv", index=False)
    print(f"  {len(elementary):,} district-years with at least one elementary school")

    print(f"Building the five-variable trend table ({START_YEAR}-{END_YEAR})...")
    trend_table = build_trend_table(district_adm)
    trend_table.to_csv(DATA_CLEANED / "lea_trend_table.csv")
    print(f"  {len(trend_table)} districts; {trend_table.dropna().shape[0]} have all five variables")

    print(f"\nWrote 4 files to {DATA_CLEANED.relative_to(PROJECT_ROOT)}/")
