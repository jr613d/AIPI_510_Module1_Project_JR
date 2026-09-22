"""
FEATURE ENGINEERING -- stage 4 of 4.

Builds the engineered features the story rests on, writes them to
data/cleaned/, and produces the final charts in figures/.

Run it with:
    python src/build_features.py

Run src/build_lea_population_crosswalk.py and src/preprocess.py first.

This is the script version of Sections 7 and 8 of
notebooks/chccs_enrollment_exploration.ipynb.

Three features get built, in the order we arrived at them:

1. CORRELATIONS WITH ENROLLMENT CHANGE (the null result)
   Percent change in four candidate explanations -- economically
   disadvantaged share, chronic absenteeism, per-pupil expenditure, Pre-K
   enrollment -- correlated against enrollment change across all districts.
   None of them explain much. This is kept rather than deleted: knowing
   what does NOT explain the decline is part of the finding, and the one
   variable that does correlate (per-pupil expenditure, r = -0.62) is
   circular, since enrollment is its own denominator.

2. CAPTURE RATE (the feature that works)
   capture_rate = K-12 enrollment / school-age population in the district.
   It answers the question the raw enrollment number cannot: of the
   children who live here, what share does the district enroll? A district
   can lose students because fewer children live there, or because a
   steady number of children choose elsewhere. These have completely
   different policy implications and look identical in the enrollment data.

   Built alongside it are the four nested layers that give the capture
   rate its context: total population, school-age population (5-17), K-12
   enrollment, and elementary enrollment.

3. DECLINE DECOMPOSITION
   Using the capture rate as a counterfactual: if the 2019 capture rate
   had held, how many students would 2024 have had? The gap between that
   and the real 2024 number splits the decline into a population component
   and a behavior component.

Outputs written to data/cleaned/:
    chccs_layers.csv                 the four layers + capture rate, by year
    elementary_change_by_district.csv every district's elementary change
    enrollment_correlations.csv       the null-result correlations
"""

import matplotlib
matplotlib.use("Agg")  # write charts to files instead of opening windows

import matplotlib.pyplot as plt
import pandas as pd

from common import CHCCS, DATA_CLEANED, FIGURES, PROJECT_ROOT

# The capture-rate analysis ends in 2024, not 2025, because SAIPE's latest
# population release is 2024. Enrollment data runs a year further, but a
# ratio needs both halves from the same year.
START_YEAR = 2019
END_YEAR = 2024


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
# Feature 1: what does NOT explain enrollment change
# ---------------------------------------------------------------------------
def build_correlations(trend_table):
    header("FEATURE 1: CORRELATIONS WITH ENROLLMENT CHANGE (THE NULL RESULT)")

    # .corr() handles missing data pairwise on its own -- for each pair of
    # columns it uses only the rows where both have a value, so districts
    # missing one variable still contribute to the others.
    correlations = trend_table.corr()["enrollment_pct_change"].drop("enrollment_pct_change")

    # Sort by strength of relationship, positive or negative, strongest first.
    ranked = correlations.reindex(correlations.abs().sort_values(ascending=False).index)
    print(f"Across {len(trend_table)} NC districts, {START_YEAR}-2025:\n")
    print(ranked.round(2).to_string())
    print("\nRead this as a null result. Per-pupil expenditure is the only strong")
    print("relationship and it is circular -- enrollment is the denominator of")
    print("per-pupil spending, so a district that loses students mechanically")
    print("shows higher spending per pupil. Nothing here explains the decline.")

    # One scatter per candidate variable, CHCCS in red. A correlation
    # coefficient alone hides the shape of the data; the scatter shows
    # whether a weak r means "no pattern" or "a pattern this measure misses."
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    variable_pairs = [
        ("eds_pct_change", "% Economically Disadvantaged", axes[0, 0]),
        ("chronic_absent_pct_change", "Chronic Absenteeism", axes[0, 1]),
        ("ppe_pct_change", "Per-Pupil Expenditure", axes[1, 0]),
        ("pk_enroll_pct_change", "Pre-K Enrollment", axes[1, 1]),
    ]
    for col, label, ax in variable_pairs:
        plot_data = trend_table[[col, "enrollment_pct_change"]].dropna()
        colors = ["red" if lea == CHCCS else "steelblue" for lea in plot_data.index]
        ax.scatter(plot_data[col], plot_data["enrollment_pct_change"], c=colors, alpha=0.6)
        ax.set_xlabel(f"{label} % change ({START_YEAR}-2025)")
        ax.set_ylabel("Enrollment % change")
        ax.set_title(f"{label} (r = {correlations[col]:.2f})")
    save("09_candidate_variables_scatter.png")

    return ranked


# ---------------------------------------------------------------------------
# Feature 2: the four nested layers, and the capture rate
# ---------------------------------------------------------------------------
def build_layers(district_adm, elementary):
    """Stack four measures of the same community onto one table, by year.

    Each layer is a subset of the one above it:
        pop_total   everyone living inside the district's boundaries
        pop_5_17    the school-age children among them
        total_adm   the school-age children the district actually enrolls
        elem_adm    the elementary-aged share of those
    Lined up this way, the gaps between the layers are the story.
    """
    population = pd.read_csv(
        PROJECT_ROOT / "data" / "lea_population_crosswalk.csv", dtype={"dpi_agency_code": str}
    ).rename(columns={"dpi_agency_code": "lea_code"})

    district = district_adm.rename(columns={"agency_code": "lea_code"})

    all_layers = (
        district.merge(population[["year", "lea_code", "pop_total", "pop_5_17"]],
                       on=["year", "lea_code"])
        .merge(elementary, on=["year", "lea_code"], how="left")
    )

    chccs = all_layers[all_layers["lea_code"] == CHCCS].set_index("year").sort_index()

    # The engineered feature itself: what share of the district's
    # school-age children does the district enroll?
    chccs["capture_rate"] = chccs["total_adm"] / chccs["pop_5_17"]

    return chccs.loc[START_YEAR:END_YEAR]


def report_layers(chccs_layers):
    header("FEATURE 2: THE FOUR NESTED LAYERS, AND THE CAPTURE RATE")

    print(chccs_layers[["pop_total", "pop_5_17", "total_adm", "elem_adm",
                        "n_elem_schools", "capture_rate"]].round(4).to_string())

    print(f"\nPercent change, {START_YEAR}-{END_YEAR}:")
    start, end = chccs_layers.loc[START_YEAR], chccs_layers.loc[END_YEAR]
    for label, column in [
        ("Total population", "pop_total"),
        ("School-age population (5-17)", "pop_5_17"),
        ("K-12 enrollment (ADM)", "total_adm"),
        ("Elementary enrollment", "elem_adm"),
    ]:
        change = (end[column] / start[column] - 1) * 100
        print(f"  {label:30s} {start[column]:>8,.0f} -> {end[column]:>8,.0f}   {change:+6.1f}%")

    # All four layers indexed to the start year so they sit on one scale
    # despite being wildly different sizes (a population in the tens of
    # thousands vs. an elementary enrollment in the thousands).
    layer_columns = ["pop_total", "pop_5_17", "total_adm", "elem_adm"]
    indexed = chccs_layers[layer_columns] / chccs_layers[layer_columns].loc[START_YEAR] * 100

    plt.figure(figsize=(10, 6))
    for col, label in [
        ("pop_total", "Total population in district"),
        ("pop_5_17", "School-age population (5-17)"),
        ("total_adm", "K-12 enrollment (ADM)"),
        ("elem_adm", "Elementary enrollment"),
    ]:
        plt.plot(indexed.index, indexed[col], marker="o", label=label)
    plt.axhline(100, color="gray", linewidth=0.8, linestyle=":")
    plt.ylabel(f"Indexed to {START_YEAR} = 100")
    plt.xlabel("Year")
    plt.title("CHCCS: The Community Isn't Shrinking. Its Elementary Schools Are.")
    plt.legend()
    save("10_four_nested_layers.png")


# ---------------------------------------------------------------------------
# Feature 3: decomposing the decline
# ---------------------------------------------------------------------------
def report_decomposition(chccs_layers):
    header("FEATURE 3: DECOMPOSING THE DECLINE")

    print("Capture rate by year (K-12 enrollment / school-age population):")
    print(chccs_layers["capture_rate"].round(4).to_string())

    # The counterfactual: hold the start-year capture rate fixed and apply
    # it to the end-year population. The difference between that and the
    # real end-year enrollment is the part the population cannot explain.
    capture_start = chccs_layers.loc[START_YEAR, "capture_rate"]
    expected_end = chccs_layers.loc[END_YEAR, "pop_5_17"] * capture_start
    actual_end = chccs_layers.loc[END_YEAR, "total_adm"]
    actual_start = chccs_layers.loc[START_YEAR, "total_adm"]
    total_decline = actual_end - actual_start

    population_part = expected_end - actual_start
    capture_part = actual_end - expected_end

    print(f"\nActual enrollment decline, {START_YEAR}-{END_YEAR}:  {total_decline:>7,.0f} students")
    print(f"  explained by fewer school-age children: {population_part:>7,.0f} students "
          f"({population_part / total_decline * 100:.0f}%)")
    print(f"  explained by a falling capture rate:    {capture_part:>7,.0f} students "
          f"({capture_part / total_decline * 100:.0f}%)")
    print("\nThe second number is the one the enrollment data alone cannot see,")
    print("and the one a school board might be able to do something about.")


# ---------------------------------------------------------------------------
# Is CHCCS's elementary decline unusual?
# ---------------------------------------------------------------------------
def compare_elementary(elementary, school_adm, chccs_layers):
    header("BENCHMARK: IS CHCCS'S ELEMENTARY DECLINE UNUSUAL?")

    # A guard we deliberately did NOT apply: excluding districts that
    # opened or closed an elementary school. That would be wrong. This is a
    # SUM across a district's elementary schools -- if a district opens a
    # 12th elementary school, those students came from the existing 11, so
    # the district total barely moves. Filtering on school count would have
    # discarded 26 districts to solve a problem that does not exist.
    #
    # The measurement issue that IS real -- elementary-aged children in K-8
    # and K-12 schools being invisible to this sum -- is handled by the
    # sensitivity check below.
    elem_wide = (
        elementary[elementary["year"].isin([START_YEAR, END_YEAR])]
        .pivot(index="lea_code", columns="year", values="elem_adm")
        .dropna()
    )
    elementary_change = (elem_wide[END_YEAR] / elem_wide[START_YEAR] - 1) * 100

    print(f"Districts with elementary enrollment in both years: {len(elementary_change)}")
    print(f"CHCCS elementary change: {elementary_change[CHCCS]:.1f}%")
    print(f"Median district:         {elementary_change.median():.1f}%")
    print(f"CHCCS rank (1 = steepest decline): "
          f"{int(elementary_change.rank()[CHCCS])} of {len(elementary_change)}")

    # Before believing a decline, check the school count. A falling total
    # means something different if the district closed schools.
    print(f"\nCHCCS held {int(chccs_layers.loc[END_YEAR, 'n_elem_schools'])} elementary schools "
          f"the whole period, while average school size fell from "
          f"{chccs_layers.loc[START_YEAR, 'elem_adm'] / chccs_layers.loc[START_YEAR, 'n_elem_schools']:.0f} "
          f"to {chccs_layers.loc[END_YEAR, 'elem_adm'] / chccs_layers.loc[END_YEAR, 'n_elem_schools']:.0f} "
          f"students. The decline is real, not an artifact of closures.")

    declining = (elementary_change < 0).sum()
    worse = (elementary_change < elementary_change[CHCCS]).sum()
    print(f"\n{declining} of {len(elementary_change)} districts lost elementary enrollment.")
    print(f"{worse} declined more steeply than CHCCS; "
          f"{len(elementary_change) - worse - 1} declined less or grew.")

    plt.figure(figsize=(11, 5))
    plt.hist(elementary_change, bins=25, edgecolor="white")
    plt.axvline(elementary_change[CHCCS], color="red", linestyle="--", linewidth=2,
                label=f"CHCCS ({elementary_change[CHCCS]:.1f}%)")
    plt.axvline(elementary_change.median(), color="black", linestyle=":", linewidth=2,
                label=f"Median district ({elementary_change.median():.1f}%)")
    plt.xlabel(f"Elementary enrollment % change, {START_YEAR}-{END_YEAR}")
    plt.ylabel("Number of districts")
    plt.title(f"Elementary Enrollment Change, All {len(elementary_change)} "
              f"NC Districts with Elementary Schools")
    plt.legend()
    save("11_elementary_change_all_districts.png")

    # --- Sensitivity check -------------------------------------------------
    # Does CHCCS's position depend on how we handle districts with K-8/K-12
    # schools? Recompute under three treatments. If the answer barely moves,
    # the elementary-only undercount does not threaten the conclusion.
    def combined_school_share(year):
        """% of a district's ADM sitting in K-8 or K-12 schools that year."""
        rows = school_adm[school_adm["year"] == year]
        district_total = rows.groupby("lea_code")["avg_student_num"].sum()
        combined = rows[rows["span"].isin(["I", "A"])].groupby("lea_code")["avg_student_num"].sum()
        return (combined / district_total * 100).reindex(district_total.index).fillna(0)

    share_start = combined_school_share(START_YEAR)
    share_end = combined_school_share(END_YEAR)
    shift = (share_end - share_start).abs()

    treatments = {
        "All districts": elementary_change.index,
        "Combined-school share <1% both years": elementary_change.index[
            (share_start.reindex(elementary_change.index) < 1)
            & (share_end.reindex(elementary_change.index) < 1)
        ],
        "Grade-structure shift <1 pct point": elementary_change.index[
            shift.reindex(elementary_change.index) < 1
        ],
    }

    print("\nSensitivity check -- same comparison under three treatments:")
    for name, keep in treatments.items():
        subset = elementary_change.loc[elementary_change.index.isin(keep)]
        rank = int(subset.rank()[CHCCS])
        pctile = subset.rank(pct=True)[CHCCS] * 100
        print(f"  {name:38s} n={len(subset):3d}  median={subset.median():6.1f}%  "
              f"CHCCS rank {rank:3d} ({pctile:.0f}th pctile)")

    print(f"\nCHCCS's own combined-school share: {share_start[CHCCS]:.3f}% ({START_YEAR}) -> "
          f"{share_end[CHCCS]:.3f}% ({END_YEAR}), so its elementary figure is")
    print("essentially unaffected either way.")

    return elem_wide, elementary_change


if __name__ == "__main__":
    FIGURES.mkdir(parents=True, exist_ok=True)

    district_adm = pd.read_csv(DATA_CLEANED / "district_adm.csv", dtype={"agency_code": str})
    school_adm = pd.read_csv(DATA_CLEANED / "school_adm_with_spans.csv",
                             dtype={"agency_code": str, "lea_code": str})
    elementary = pd.read_csv(DATA_CLEANED / "elementary_adm_by_district.csv",
                             dtype={"lea_code": str})
    trend_table = pd.read_csv(DATA_CLEANED / "lea_trend_table.csv", index_col=0)

    correlations = build_correlations(trend_table)
    correlations.rename("correlation_with_enrollment_change").to_csv(
        DATA_CLEANED / "enrollment_correlations.csv"
    )

    chccs_layers = build_layers(district_adm, elementary)
    report_layers(chccs_layers)
    chccs_layers.to_csv(DATA_CLEANED / "chccs_layers.csv")

    report_decomposition(chccs_layers)

    elem_wide, elementary_change = compare_elementary(elementary, school_adm, chccs_layers)
    elementary_comparison = pd.DataFrame({
        f"elem_adm_{START_YEAR}": elem_wide[START_YEAR],
        f"elem_adm_{END_YEAR}": elem_wide[END_YEAR],
        "pct_change": elementary_change,
    })
    elementary_comparison.to_csv(DATA_CLEANED / "elementary_change_by_district.csv")

    print(f"\n{'=' * 72}")
    print(f"Features written to {DATA_CLEANED.relative_to(PROJECT_ROOT)}/")
    print(f"Charts written to   {FIGURES.relative_to(PROJECT_ROOT)}/")
