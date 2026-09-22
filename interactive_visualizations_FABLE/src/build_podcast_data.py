"""
Small extra data set for the podcast companion page: CHCCS elementary schools one by
one, and Orange County children by age group (elementary-age proxy). Everything else
the page needs comes from dashboard_data.json and choice_population_data.json.

Output: data/cleaned/podcast_data.json
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "cleaned"
YEARS = list(range(2006, 2026))

adm = pd.read_csv(RAW / "nc_dpi_rcd_adm_2024-25.csv", dtype={"agency_code": str, "category_code": str})
loc = pd.read_excel(RAW / "nc_dpi_rcd_location_2024-25.xlsx", dtype=str)
loc["year"] = loc["year"].astype(int)
sch = loc[loc["agency_level"] == "SCH"][["year", "agency_code", "name", "category_code"]]

# CHCCS elementary schools (span E in that year's location table)
s = adm[adm["category_code"].isna() & adm["agency_code"].str.startswith("681") & (adm["agency_code"] != "681LEA")]
s = s.drop(columns="category_code").merge(sch, on=["year", "agency_code"], how="left")
e = s[s["category_code"] == "E"].pivot_table(index="agency_code", columns="year", values="avg_student_num").reindex(columns=YEARS)
names = sch.sort_values("year").groupby("agency_code")["name"].last()
def short(n):
    for w in [" Dual Language Magnet Elementary School", " Elementary School", "Charles and Lucile ", "Mel and Zora ", "Elizabeth ", "Mary ", "Frank Porter Graham"]:
        n = n.replace(w, "FPG" if w == "Frank Porter Graham" else "")
    return n.strip()
schools = {code: {"name": short(names[code]), "adm": [None if pd.isna(v) else int(v) for v in e.loc[code]]} for code in e.index}

# Orange County children by age group: intercensal (2005-2009), Vintage 2019 (2010-2019), Vintage 2024 (2020-2024)
pe = RAW / "census_popest"
c0 = pd.read_csv(pe / "co-est00int-alldata-37.csv", encoding="latin-1")
c0 = c0[(c0["CTYNAME"] == "Orange County") & c0["YEAR"].between(8, 11)]          # 8=7/1/2006 ... 11=7/1/2009
g0 = c0.pivot_table(index="YEAR", columns="AGEGRP", values="TOT_POP")
under5_0 = (g0[0] + g0[1]).tolist(); a59_0 = g0[2].tolist(); a1014_0 = g0[3].tolist()
c1 = pd.read_csv(pe / "cc-est2019-agesex-37.csv", encoding="latin-1")
c1 = c1[(c1["CTYNAME"] == "Orange County") & c1["YEAR"].between(3, 12)].sort_values("YEAR")
c2 = pd.read_csv(pe / "cc-est2024-agesex-37.csv", encoding="latin-1")
c2 = c2[(c2["CTYNAME"] == "Orange County") & c2["YEAR"].between(2, 6)].sort_values("YEAR")
ages = {
    "years": YEARS,                                     # estimate of July `year` -> the school year ending that June; none yet for 2025
    "under5": [int(v) for v in under5_0 + c1["UNDER5_TOT"].tolist() + c2["UNDER5_TOT"].tolist()] + [None],
    "age5_9": [int(v) for v in a59_0 + c1["AGE59_TOT"].tolist() + c2["AGE59_TOT"].tolist()] + [None],
    "age10_14": [int(v) for v in a1014_0 + c1["AGE1014_TOT"].tolist() + c2["AGE1014_TOT"].tolist()] + [None],
}
assert all(len(v) == 20 for k, v in ages.items() if k != "years")

# The district's own forward numbers, transcribed from CHCCS board documents in the parent
# project (see data/raw/chccs_board/): the closure study's per-school K-5 forecast by
# Carolina Demography (2025-26 through 2035-36) and the board deck's district ADM
# projection (FY2026 through FY2031; FY2025 actual = 11,065).
fc = pd.read_csv(RAW / "chccs_board" / "closure_study_elementary_forecast_2026-2036.csv")
fc_years = [int(c) for c in fc.columns if c.isdigit()]
elem_forecast = {y: int(fc[str(y)].sum()) for y in fc_years}
assert elem_forecast[2026] == 4294, elem_forecast[2026]          # the study's own stated current-year K-5 ADM
proj = pd.read_csv(RAW / "chccs_board" / "board_deck_district_adm_projection.csv")
k12_forecast = {2026: 10758}                                       # FY2026 "projected/actual" on deck p9
k12_forecast.update({int(r.fiscal_year): int(r.projected_adm) for r in proj.itertuples()})
name_map = {"Carrboro Elementary": "681304", "Ephesus Elementary": "681311", "Estes Hills Elementary": "681312", "FPG Elementary": "681316",
            "Glenwood Elementary": "681320", "McDougle Elementary": "681326", "Morris Grove Elementary": "681332", "Northside Elementary": "681300",
            "Rashkis Elementary": "681334", "Scroggs Elementary": "681330", "Seawell Elementary": "681310"}
school_forecast = {name_map[r.school]: {str(y): int(getattr(r, f"_{fc.columns.get_loc(str(y)) + 1}")) for y in fc_years} for r in fc.itertuples()}

payload = {"chccsSchools": schools, "closureCandidates": ["681311", "681320", "681310"], "orangeAges": ages,
           "board": {"years": fc_years, "elementary": [elem_forecast[y] for y in fc_years],
                     "k12Years": sorted(k12_forecast), "k12": [k12_forecast[y] for y in sorted(k12_forecast)],
                     "schools": school_forecast,
                     "source": "CHCCS closure study (May 7, 2026; Carolina Demography forecast) and Board of Education retreat deck (Dec. 11, 2025)"}}
(CLEAN / "podcast_data.json").write_text(json.dumps(payload, separators=(",", ":")))
print({k: v["name"] for k, v in schools.items()})
print("Orange 5-9:", ages["age5_9"]); print("Orange under 5:", ages["under5"])
print("board elementary forecast:", elem_forecast); print("board K-12:", k12_forecast)
print("2024-25 actual vs 2025-26 board figure, per school:", {v["name"]: (v["adm"][-1], school_forecast[k]["2026"]) for k, v in schools.items()})
