"""
EXPLORATORY DATA ANALYSIS -- stage 3 of 4.

Prints a data quality report and writes the exploratory charts to figures/.

Run it with:
    python src/run_eda.py

Run src/build_lea_population_crosswalk.py and src/preprocess.py first.

This is the script version of Sections 3, 4 and 5 of
notebooks/chccs_enrollment_exploration.ipynb. The notebook is where the
thinking and the written interpretation live; this script is the
reproducible version -- run it and every number and chart in those
sections regenerates from the raw files.

It runs in five parts:

  Part 1  Structure of the raw ADM table -- shape, types, missing values
  Part 2  Data quality checks -- duplicates, zeros, and the category_code
          trap (proving the lettered rows are per-school AVERAGES, not a
          breakdown of the district total)
  Part 3  Distributions -- box plots, histograms, and descriptive
          statistics split by aggregation level
  Part 4  Quality check on the Census population crosswalk
  Part 5  Exploration -- where CHCCS ranks among all NC districts, how
          enrollment tracks school-age population, and how exposed each
          district is to the elementary-only undercount
"""

import matplotlib
matplotlib.use("Agg")  # write charts to files instead of opening windows

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import CHCCS, DATA_CLEANED, DATA_SOURCES, FIGURES, PROJECT_ROOT, pct_change_by_lea


def save(fig_name):
    """Save the current chart to figures/ and close it."""
    path = FIGURES / fig_name
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"    saved {path.relative_to(PROJECT_ROOT)}")


def header(text):
    print(f"\n{'=' * 72}\n{text}\n{'=' * 72}")


# ---------------------------------------------------------------------------
# Part 1: structure of the raw data
# ---------------------------------------------------------------------------
def report_structure(adm):
    header("PART 1: STRUCTURE OF THE RAW ADM TABLE")

    print("Shape (rows, columns):", adm.shape)
    print("\nColumn types:")
    print(adm.dtypes.to_string())

    # isnull() only catches real NaNs -- it will not catch a blank string or
    # a sentinel value, so we check both.
    print("\nTrue NaNs per column:")
    print(adm.isnull().sum().to_string())
    print("\nEmpty-string values per column:")
    print((adm == "").sum().to_string())

    print("\nDescriptive statistics (avg_student_num is the only numeric column):")
    print(adm.describe().to_string())


# ---------------------------------------------------------------------------
# Part 2: data quality checks
# ---------------------------------------------------------------------------
def report_quality(adm):
    header("PART 2: DATA QUALITY CHECKS")

    # A table like this should have exactly one row per
    # (year, agency_code, category_code). Duplicates would mean something
    # is double-counted.
    duplicates = adm.duplicated(subset=["year", "agency_code", "category_code"]).sum()
    print("Duplicate (year, agency_code, category_code) rows:", duplicates)

    # describe() above reports a minimum of 0, which is worth a look: a
    # school with zero students is either a real closure or a stand-in for
    # missing data, and the file does not say which.
    zero_rows = adm[adm["avg_student_num"] == 0]
    print(f"Rows with avg_student_num == 0: {len(zero_rows)} (out of {len(adm):,})")

    print("\n--- What category_code actually means ---")
    print("This is the trap. An earlier draft of this analysis read the")
    print("lettered rows as a grade-span breakdown of district enrollment.")
    print("They are not. Two checks, using CHCCS in 2025:\n")

    chccs_2025 = adm[adm["agency_code"].str.startswith("681") & (adm["year"] == 2025)]
    schools = chccs_2025[~chccs_2025["agency_code"].str.endswith("LEA")]
    district_total = chccs_2025[
        (chccs_2025["agency_code"] == CHCCS) & chccs_2025["category_code"].isna()
    ]["avg_student_num"].iloc[0]

    # Check 1: the blank-category district row equals the sum of its schools.
    print(f"  Check 1  Sum of CHCCS's individual schools: {schools['avg_student_num'].sum():,.0f}")
    print(f"           CHCCS's blank-category_code row:   {district_total:,.0f}")
    print("           -> blank category_code IS the district total.\n")

    # Check 2: the lettered rows are per-school averages. CHCCS's 11
    # elementary schools are listed explicitly so the average can be
    # computed independently and compared to what the "E" row claims.
    elementary_codes = ["681300", "681304", "681310", "681311", "681312",
                        "681316", "681320", "681326", "681330", "681332", "681334"]
    elementary = schools[schools["agency_code"].isin(elementary_codes)]["avg_student_num"]
    lettered_e = chccs_2025[
        (chccs_2025["agency_code"] == CHCCS) & (chccs_2025["category_code"] == "E")
    ]["avg_student_num"].iloc[0]
    lettered_sum = chccs_2025[
        (chccs_2025["agency_code"] == CHCCS) & chccs_2025["category_code"].notna()
    ]["avg_student_num"].sum()

    print(f"  Check 2  CHCCS has {len(elementary)} elementary schools, averaging "
          f"{elementary.mean():.1f} students each")
    print(f"           The 'E' row for {CHCCS} says: {lettered_e:,.0f}")
    print(f"           -> the lettered rows are per-school AVERAGES.")
    print(f"           Summing them gives {lettered_sum:,.0f}, nowhere near the real "
          f"total of {district_total:,.0f}.")

    return duplicates


# ---------------------------------------------------------------------------
# Part 3: distributions and descriptive statistics
# ---------------------------------------------------------------------------
def report_distributions(adm, duplicates):
    header("PART 3: DISTRIBUTIONS BY AGGREGATION LEVEL")

    # The raw table stacks schools, districts and the state in one column.
    # That is why describe() showed a maximum of 1.5 million -- that is the
    # whole state, sitting in the same column as individual schools.
    state_level = adm[adm["agency_code"] == "NC-SEA"]["avg_student_num"]
    district_level = adm[adm["agency_code"].str.endswith("LEA")]["avg_student_num"]
    school_level = adm[
        ~adm["agency_code"].str.endswith("LEA") & (adm["agency_code"] != "NC-SEA")
    ]["avg_student_num"]

    print("State-level rows:   ", len(state_level))
    print("District-level rows:", len(district_level))
    print("School-level rows:  ", len(school_level))

    # Box plot. State is left off -- with a single state total, a box plot
    # has nothing to show a spread of.
    plt.figure()
    plt.boxplot([district_level, school_level], tick_labels=["District (LEA)", "School"])
    plt.ylabel("avg_student_num")
    plt.title("Spread of ADM Values by Aggregation Level")
    save("01_adm_boxplot.png")

    # Same box plot on a log scale. A log transform compresses the long
    # right tail so the box and whiskers become visible again instead of
    # disappearing under a wall of outlier dots. Log scale cannot show 0,
    # so the handful of zero rows are dropped for this plot only.
    district_positive = district_level[district_level > 0]
    school_positive = school_level[school_level > 0]

    plt.figure()
    plt.boxplot([district_positive, school_positive], tick_labels=["District (LEA)", "School"])
    plt.yscale("log")
    plt.ylabel("avg_student_num (log scale)")
    plt.title("Spread of ADM Values by Aggregation Level (Log Scale)")
    save("02_adm_boxplot_log.png")

    # Histograms: the standard first tool for seeing a distribution's
    # shape -- skew, peaks and gaps are all visible at a glance.
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].hist(district_level, bins=30)
    axes[0].set_title("District (LEA) ADM")
    axes[0].set_xlabel("avg_student_num")
    axes[0].set_ylabel("count")
    axes[1].hist(school_level, bins=30)
    axes[1].set_title("School ADM")
    axes[1].set_xlabel("avg_student_num")
    save("03_adm_histograms.png")

    # Log-x version. A log-scaled histogram needs log-SPACED bins, not
    # evenly-spaced ones -- otherwise the bins near the low end are still
    # too wide to show any detail.
    log_bins = np.logspace(
        np.log10(district_positive.min()), np.log10(district_positive.max()), 30
    )
    plt.figure()
    plt.hist(district_positive, bins=log_bins)
    plt.xscale("log")
    plt.xlabel("avg_student_num (log scale)")
    plt.ylabel("count")
    plt.title("District (LEA) ADM (Log Scale)")
    save("04_adm_histogram_log.png")

    # Descriptive statistics, district vs school:
    #   mean / median / mode  -- central tendency
    #   IQR, std dev          -- how spread out the values are
    #   skew                  -- which way the tail runs (positive = long right tail)
    #   kurtosis              -- "tailedness": how much more extreme-value-prone
    #                            this is than a normal distribution
    # mode() can return more than one value if there is a tie, so we take
    # the first with .iloc[0].
    def describe(series):
        return {
            "mean": series.mean(),
            "median": series.median(),
            "mode": series.mode().iloc[0],
            "IQR": series.quantile(0.75) - series.quantile(0.25),
            "spread (std dev)": series.std(),
            "skew": series.skew(),
            "kurtosis": series.kurt(),
        }

    stats_by_level = pd.DataFrame({
        "District (LEA)": describe(district_level),
        "School": describe(school_level),
    })
    print("\nDescriptive statistics by level:")
    print(stats_by_level.round(2).to_string())

    # The 8-dimension Data Quality Assessment. One sentence each; the two
    # dimensions we cannot claim are marked "None" rather than skipped.
    dqa = pd.DataFrame({
        "Dimension": [
            "Profiling", "Completeness", "Accuracy", "Consistency",
            "Integrity", "Lineage and Provenance", "Automated Testing",
            "Continuous Monitoring",
        ],
        "Assessment": [
            f"{len(adm):,} rows, {adm.shape[1]} columns, one numeric column (avg_student_num).",
            "No true missing values. Blank category_code cells are structural, not missing -- "
            "a blank marks a total row. Some avg_student_num values are exactly 0, which may "
            "represent a different kind of missing.",
            "Spot-checked CHCCS's 2025 district total (11,065) against the board deck's own "
            "reported figure; exact match. Broader accuracy is unverified.",
            "Single official release in one consistent format; no cross-source consistency "
            "problems found within this table.",
            f"agency_code follows a documented format; duplicate (year, agency_code, "
            f"category_code) rows found: {duplicates}.",
            "Fully documented: NC DPI bulk ZIP -> rcd_adm.xlsx -> CSV, tracked in "
            "data_sources/INDEX.md.",
            "None -- this is a one-time exploration, not a pipeline with validation rules.",
            "None -- a static snapshot downloaded once, not a live or refreshed feed.",
        ],
    })
    print("\n8-Dimension Data Quality Assessment:")
    for _, row in dqa.iterrows():
        print(f"  {row['Dimension']:<24} {row['Assessment']}")


# ---------------------------------------------------------------------------
# Part 4: quality check on the population crosswalk
# ---------------------------------------------------------------------------
def report_population_quality():
    header("PART 4: QUALITY CHECK ON THE CENSUS POPULATION CROSSWALK")

    population = pd.read_csv(
        PROJECT_ROOT / "data" / "lea_population_crosswalk.csv", dtype={"dpi_agency_code": str}
    )

    print("Shape (rows, columns):", population.shape)
    print("Duplicate (district, year) rows:",
          population.duplicated(subset=["dpi_agency_code", "year"]).sum())
    print("\nMissing values per column:")
    print(population.isnull().sum().to_string())

    # Coverage: does every year have the same set of districts? A district
    # appearing in some years but not others would quietly distort any
    # start-year-to-end-year comparison.
    years_per_district = population.groupby("dpi_agency_code")["year"].nunique()
    n_years = population["year"].nunique()
    print(f"\nDistricts with all {n_years} years present: {(years_per_district == n_years).sum()}")

    incomplete = years_per_district[years_per_district < n_years]
    if len(incomplete) > 0:
        print("Districts with fewer than all years:")
        partial = population[population["dpi_agency_code"].isin(incomplete.index)]
        print(partial[["dpi_agency_code", "district_name", "year"]].to_string(index=False))
    else:
        print("No districts have partial coverage.")


# ---------------------------------------------------------------------------
# Part 5: exploration
# ---------------------------------------------------------------------------
def explore_enrollment_ranking(district_adm):
    header("PART 5A: WHERE DOES CHCCS RANK AMONG ALL NC DISTRICTS?")

    # Two windows, because the answer depends on which one you pick -- and
    # that dependence is itself one of the findings.
    for start, end, tag in [(2006, 2025, "full history"), (2019, 2025, "post-peak")]:
        change = pct_change_by_lea(district_adm, "total_adm", start, end)
        ranked = change.dropna().sort_values()
        rank = ranked.index.get_loc(CHCCS) + 1  # +1 so rank 1 = biggest decline

        print(f"\n--- {start}-{end} ({tag}) ---")
        print(f"Districts with data in both years: {len(ranked)}")
        print(f"CHCCS change: {ranked[CHCCS]:.1f}%")
        print(f"CHCCS rank:   {rank} of {len(ranked)} (1 = biggest decline)")
        print("Five-number summary across all districts:")
        print(ranked.describe().round(1).to_string())

        plt.figure(figsize=(10, 5))
        plt.hist(ranked, bins=30)
        plt.axvline(ranked[CHCCS], color="red", linestyle="--",
                    label=f"CHCCS ({ranked[CHCCS]:.1f}%)")
        plt.xlabel(f"Enrollment % change, {start}-{end}")
        plt.ylabel("Number of LEAs")
        plt.title(f"Enrollment Change Across All NC LEAs ({start}-{end}), CHCCS Highlighted")
        plt.legend()
        save(f"05_enrollment_change_hist_{start}_{end}.png")

        # A bar per district shows exactly where CHCCS sits relative to all
        # of them, not just which histogram bucket it falls in.
        plt.figure(figsize=(14, 5))
        colors = ["red" if lea == CHCCS else "steelblue" for lea in ranked.index]
        plt.bar(range(len(ranked)), ranked.values, color=colors)
        plt.xlabel("LEAs, sorted from biggest decline to biggest growth")
        plt.ylabel(f"Enrollment % change, {start}-{end}")
        plt.title(f"Every NC LEA's Enrollment Change {start}-{end}, CHCCS in Red")
        plt.xticks([])
        save(f"06_enrollment_change_bars_{start}_{end}.png")


def explore_enrollment_vs_population(district_adm):
    header("PART 5B: ENROLLMENT CHANGE VS. SCHOOL-AGE POPULATION CHANGE")

    # The crosswalk names its ID column dpi_agency_code; renaming it to
    # agency_code lets the same pct_change_by_lea() helper be reused.
    population = pd.read_csv(
        PROJECT_ROOT / "data" / "lea_population_crosswalk.csv", dtype={"dpi_agency_code": str}
    ).rename(columns={"dpi_agency_code": "agency_code"})

    # 2024 is the end year here, not 2025: SAIPE's latest release is 2024.
    comparison = pd.DataFrame({
        "pop_5_17_pct_change": pct_change_by_lea(population, "pop_5_17", 2019, 2024),
        "enrollment_pct_change": pct_change_by_lea(district_adm, "total_adm", 2019, 2024),
    }).dropna()

    r = comparison["pop_5_17_pct_change"].corr(comparison["enrollment_pct_change"])
    print(f"Districts with both a population and enrollment figure: {len(comparison)}")
    print(f"Correlation between the two: {r:.2f}")
    print("\nCHCCS:")
    print(comparison.loc[CHCCS].round(2).to_string())

    plt.figure(figsize=(8, 6))
    colors = ["red" if lea == CHCCS else "steelblue" for lea in comparison.index]
    plt.scatter(comparison["pop_5_17_pct_change"], comparison["enrollment_pct_change"],
                c=colors, alpha=0.6)
    plt.xlabel("School-age (5-17) population % change, 2019-2024")
    plt.ylabel("Enrollment % change, 2019-2024")
    plt.title("Enrollment Change vs. School-Age Population Change, All NC LEAs")
    plt.axhline(0, color="gray", linewidth=0.5)
    plt.axvline(0, color="gray", linewidth=0.5)
    save("07_enrollment_vs_population.png")


def explore_combined_grade_schools(school_adm):
    header("PART 5C: THE ELEMENTARY-ONLY UNDERCOUNT")

    print("'Elementary enrollment' is not published by DPI -- it has to be built")
    print("by summing schools marked 'E'. Any elementary-aged child in a K-8 (I)")
    print("or K-12 (A) school is invisible to that sum. How big is the problem?\n")

    year_2024 = school_adm[school_adm["year"] == 2024]
    print("NC schools by grade-span category (2024):")
    print(year_2024["span"].value_counts().to_string())

    district_totals = year_2024.groupby("lea_code")["avg_student_num"].sum()
    combined_totals = (
        year_2024[year_2024["span"].isin(["I", "A"])].groupby("lea_code")["avg_student_num"].sum()
    )
    combined_share = (combined_totals / district_totals * 100).reindex(district_totals.index).fillna(0)

    print(f"\nDistricts with at least one K-8 or K-12 school: "
          f"{(combined_share > 0).sum()} of {len(combined_share)}")
    print(f"Districts where those schools hold >10% of students: {(combined_share > 10).sum()}")
    print("\nMost affected districts (% of ADM in K-8/K-12 schools):")
    print(combined_share.sort_values(ascending=False).head(5).round(1).to_string())
    print(f"\nCHCCS: {combined_share[CHCCS]:.2f}%  -- its elementary sum is essentially exact.")

    # Buckets 5 percentage points wide, so the shape of the exposure across
    # all districts is visible rather than just the extremes.
    bucket_edges = np.arange(0, 105, 5)
    exactly_zero = (combined_share == 0).sum()
    first_bucket = ((combined_share >= 0) & (combined_share < 5)).sum()

    plt.figure(figsize=(11, 5))
    plt.hist(combined_share, bins=bucket_edges, edgecolor="white")
    plt.xlabel("% of a district's students in K-8 or K-12 schools")
    plt.ylabel("Number of districts")
    plt.title("How Exposed Is Each NC District to the Elementary-Only Undercount? (2024)")
    plt.xticks(bucket_edges, rotation=45)

    # The first bar is misleading on its own -- most of it is districts at
    # exactly 0%, which have no undercount at all. Say so on the chart.
    plt.annotate(
        f"{first_bucket} districts in this bar,\nbut {exactly_zero} of them are exactly 0%\n"
        f"(no undercount at all)",
        xy=(2.5, first_bucket), xytext=(22, first_bucket * 0.75),
        arrowprops=dict(arrowstyle="->", color="gray"), fontsize=9, color="gray",
    )
    save("08_combined_grade_exposure.png")

    print(f"\nExactly 0%:        {exactly_zero} districts -- elementary sum is exact")
    print(f"Between 0% and 5%: {first_bucket - exactly_zero} districts -- minor undercount")
    print(f"5% or more:        {(combined_share >= 5).sum()} districts -- meaningful undercount")
    print(f"20% or more:       {(combined_share >= 20).sum()} districts -- elementary sum is unreliable")


if __name__ == "__main__":
    FIGURES.mkdir(parents=True, exist_ok=True)

    # Parts 1-3 work on the RAW file on purpose. Data quality checks are
    # about what was published, not about what our preprocessing left behind.
    adm_raw = pd.read_csv(DATA_SOURCES / "nc_dpi_rcd_adm_2024-25.csv", dtype={"agency_code": str})

    report_structure(adm_raw)
    duplicates = report_quality(adm_raw)
    report_distributions(adm_raw, duplicates)
    report_population_quality()

    # Part 5 works on the cleaned tables from preprocess.py.
    district_adm = pd.read_csv(DATA_CLEANED / "district_adm.csv", dtype={"agency_code": str})
    school_adm = pd.read_csv(DATA_CLEANED / "school_adm_with_spans.csv",
                             dtype={"agency_code": str, "lea_code": str})

    explore_enrollment_ranking(district_adm)
    explore_enrollment_vs_population(district_adm)
    explore_combined_grade_schools(school_adm)

    print(f"\n{'=' * 72}")
    print(f"Charts written to {FIGURES.relative_to(PROJECT_ROOT)}/")
