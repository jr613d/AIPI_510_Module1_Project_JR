"""
Build the compact dataset that powers the NC enrollment dashboard.

Inputs (all in data/raw/, see README.md for provenance):
  nc_dpi_rcd_adm_2024-25.csv          NC DPI Average Daily Membership, 2006-2025
  nc_dpi_rcd_location_2024-25.xlsx    NC DPI agency directory (names, counties, charter flag)
  cb_2023_37_unsd_500k.zip            Census cartographic boundaries, NC unified school districts
  cb_2023_us_county_500k.zip          Census cartographic boundaries, US counties (filtered to NC)

Outputs:
  data/cleaned/lea_adm_wide.csv        one row per traditional LEA, one column per year
  data/cleaned/county_adm_wide.csv     one row per county: LEA total, charter total, combined
  data/cleaned/charter_adm_by_county_wide.csv
  data/cleaned/lea_crosswalk.csv       DPI code -> name -> county -> Census GEOID
  data/cleaned/dashboard_data.json     everything the HTML needs (series + topology)

Every step is plain pandas; no clever abstractions, so it can be read top to bottom.
"""

import difflib
import io
import json
import re
import zipfile
from pathlib import Path

import pandas as pd
import shapefile  # pyshp
import topojson

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "cleaned"
CLEAN.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2006, 2026))

# ---------------------------------------------------------------------------
# 1. Enrollment (ADM) series
# ---------------------------------------------------------------------------
adm = pd.read_csv(RAW / "nc_dpi_rcd_adm_2024-25.csv", dtype={"agency_code": str, "category_code": str})
# category_code blank == all grades combined. Anything else is a grade-span slice.
adm = adm[adm["category_code"].isna()].copy()
adm["year"] = adm["year"].astype(int)

loc = pd.read_excel(RAW / "nc_dpi_rcd_location_2024-25.xlsx", dtype=str)
loc["year"] = loc["year"].astype(int)

# --- Traditional LEAs -------------------------------------------------------
lea_names = (
    loc[loc["agency_level"] == "LEA"]
    .sort_values("year")
    .groupby("agency_code")
    .agg(name=("name", "last"), county=("county", "last"))
)

lea_adm = adm[adm["agency_code"].str.endswith("LEA")]
lea_wide = lea_adm.pivot_table(index="agency_code", columns="year", values="avg_student_num", aggfunc="sum")
lea_wide = lea_wide.reindex(columns=YEARS)

# Keep only geographic districts with a complete 20-year history. That drops the
# two residential Schools for the Deaf (296/297) and a handful of short-lived codes.
complete = lea_wide.notna().all(axis=1)
lea_wide = lea_wide[complete]
lea_wide = lea_wide.join(lea_names)
assert len(lea_wide) == 115, f"expected 115 LEAs, got {len(lea_wide)}"

# Clean up display names a little (keep DPI's official name in a separate column)
def display_name(name: str) -> str:
    n = name.replace("Winston Salem / Forsyth County Schools", "Winston-Salem/Forsyth County Schools")
    n = n.replace("Newton Conover", "Newton-Conover")
    return n

lea_wide["display_name"] = lea_wide["name"].map(display_name)

# --- Charter schools --------------------------------------------------------
charter_loc = loc[(loc["agency_level"] == "SCH") & (loc["designation_Type"] == "C")][
    ["year", "agency_code", "name", "county"]
]
charter_adm = adm[~adm["agency_code"].str.endswith("LEA") & (adm["agency_code"] != "NC-SEA")]
charter_adm = charter_adm.merge(charter_loc, on=["year", "agency_code"], how="inner")

# The two statewide virtual charters (00A/00B) are listed under Durham but serve the
# whole state; keep them in the statewide charter total but out of any county.
VIRTUAL_PREFIXES = ("00A", "00B")
charter_adm["is_virtual"] = charter_adm["agency_code"].str[:3].isin(VIRTUAL_PREFIXES)

charter_by_county = (
    charter_adm[~charter_adm["is_virtual"]]
    .pivot_table(index="county", columns="year", values="avg_student_num", aggfunc="sum")
    .reindex(columns=YEARS)
    .fillna(0)
    .astype(int)
)
charter_schools_by_county = (
    charter_adm[~charter_adm["is_virtual"]]
    .groupby(["county", "year"])["agency_code"].nunique()
    .unstack("year").reindex(columns=YEARS).fillna(0).astype(int)
)
charter_state = charter_adm.groupby("year")["avg_student_num"].sum().reindex(YEARS)
charter_virtual_state = charter_adm[charter_adm["is_virtual"]].groupby("year")["avg_student_num"].sum().reindex(YEARS).fillna(0)

# --- Counties ---------------------------------------------------------------
county_lea = lea_wide.groupby("county")[YEARS].sum()
all_counties = sorted(set(lea_wide["county"]))
assert len(all_counties) == 100, len(all_counties)
county_charter = charter_by_county.reindex(all_counties).fillna(0).astype(int)
county_total = county_lea + county_charter

# --- ADM by school grade-span category (for the elementary tab) -----------------
# The LEA-level rows with category_code E/M/H in rcd_adm are the AVERAGE ADM of the
# LEA's schools in that category (CHCCS 2025: E = 411 = 4,522 students / 11 schools),
# not a total. So elementary totals are built here by summing school rows, using each
# school's grade-span category from rcd_location for that year:
#   E = elementary school, I = elementary + middle (K-8), M = middle, H = high,
#   A = all grades (K-12), T = middle + high.
sch_loc = loc[loc["agency_level"] == "SCH"][["year", "agency_code", "category_code"]].rename(columns={"category_code": "span"})
school_adm = adm[~adm["agency_code"].str.endswith("LEA") & (adm["agency_code"] != "NC-SEA")].merge(sch_loc, on=["year", "agency_code"], how="left")
school_adm["span"] = school_adm["span"].fillna("U")
school_adm["is_charter"] = ~school_adm["agency_code"].str[:3].str.isdigit()
school_adm["lea"] = school_adm["agency_code"].str[:3] + "LEA"
SPANS = ["E", "I", "M", "H", "A", "T", "U"]   # U = school not found in that year's location table (1-4 schools a year statewide)

def span_wide(df, index_col):
    w = df.pivot_table(index=index_col, columns=["span", "year"], values="avg_student_num", aggfunc="sum").fillna(0)
    return w

lea_span = span_wide(school_adm[~school_adm["is_charter"] & school_adm["lea"].isin(lea_wide.index)], "lea")
# integrity: school rows sum to the LEA total row every year
for y in YEARS:
    tot_sum = sum(lea_span[(sp, y)] if (sp, y) in lea_span.columns else 0 for sp in SPANS)
    assert (tot_sum.reindex(lea_wide.index).fillna(0) - lea_wide[y]).abs().max() == 0, f"school rows do not sum to LEA totals in {y}"
charter_span_county = span_wide(charter_adm.merge(sch_loc, on=["year", "agency_code"], how="left").assign(span=lambda d: d["span"].fillna("U"))[lambda d: ~d["is_virtual"]], "county")
charter_span_state = charter_adm.merge(sch_loc, on=["year", "agency_code"], how="left").assign(span=lambda d: d["span"].fillna("U")).groupby(["span", "year"])["avg_student_num"].sum()

def span_series(w, key, sp):
    return [int(w.loc[key, (sp, y)]) if key in w.index and (sp, y) in w.columns else 0 for y in YEARS]

# ---------------------------------------------------------------------------
# 2. Geography: Census cartographic boundaries -> one TopoJSON with two layers
# ---------------------------------------------------------------------------
def read_shapefile_from_zip(zip_path: Path):
    with zipfile.ZipFile(zip_path) as z:
        base = [n for n in z.namelist() if n.endswith(".shp")][0][:-4]
        shp = io.BytesIO(z.read(base + ".shp"))
        dbf = io.BytesIO(z.read(base + ".dbf"))
        shx = io.BytesIO(z.read(base + ".shx"))
        reader = shapefile.Reader(shp=shp, dbf=dbf, shx=shx)
        return reader.__geo_interface__["features"]

unsd_features = read_shapefile_from_zip(RAW / "cb_2023_37_unsd_500k.zip")
county_features = [f for f in read_shapefile_from_zip(RAW / "cb_2023_us_county_500k.zip") if f["properties"]["STATEFP"] == "37"]
assert len(county_features) == 100

# County name -> GEOID
county_geoid = {f["properties"]["NAME"]: f["properties"]["GEOID"] for f in county_features}

# Match DPI LEA names to Census district names. Most match after light normalisation;
# a few need explicit overrides because the two agencies spell them differently.
def norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    for w in ["public", "schools", "school", "system", "board of education", "graded", "district", "county", "city", "the"]:
        s = re.sub(rf"\b{w}\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()

OVERRIDES = {
    "340LEA": "Forsyth County Schools",
    "640LEA": "Nash-Rocky Mount Schools",
    "700LEA": "Pasquotank County Schools",
    "780LEA": "Robeson County Schools",
    "491LEA": "Mooresville City Schools",
    "250LEA": "Craven County Schools",
}
census_names = {f["properties"]["NAME"]: f["properties"]["GEOID"] for f in unsd_features}
census_norm = {norm(n): n for n in census_names}

matches = {}
for code, row in lea_wide.iterrows():
    if code in OVERRIDES:
        matches[code] = OVERRIDES[code]
        continue
    key = norm(row["name"])
    if key in census_norm:
        matches[code] = census_norm[key]
        continue
    close = difflib.get_close_matches(key, list(census_norm), n=1, cutoff=0.85)
    if close:
        matches[code] = census_norm[close[0]]
    else:
        raise SystemExit(f"No Census match for {code} {row['name']!r} (norm={key!r})")

assert len(set(matches.values())) == 115, "two LEAs matched the same Census district"
lea_wide["census_name"] = pd.Series(matches)
lea_wide["geoid"] = lea_wide["census_name"].map(census_names)
lea_wide["county_geoid"] = lea_wide["county"].map(county_geoid)
assert lea_wide["county_geoid"].notna().all()

# Attach DPI code to each district polygon; drop polygons with no DPI LEA
# (Camp Lejeune, Fort Bragg, Cherokee Central are federal/tribal, not NC LEAs).
geoid_to_code = {g: c for c, g in lea_wide["geoid"].items()}
lea_geo = []
for f in unsd_features:
    g = f["properties"]["GEOID"]
    if g in geoid_to_code:
        lea_geo.append({"type": "Feature", "geometry": f["geometry"],
                        "properties": {"id": geoid_to_code[g], "layer": "lea"}})
county_geo = [
    {"type": "Feature", "geometry": f["geometry"],
     "properties": {"id": f["properties"]["GEOID"], "layer": "county"}}
    for f in county_features
]

# Both layers go into ONE topology so shared borders (a county line that is also a
# district line) become one shared arc. The HTML splits them back apart by `layer`.
topo = topojson.Topology(
    data={"type": "FeatureCollection", "features": lea_geo + county_geo},
    prequantize=20000,
    topology=True,
    toposimplify=0.002,          # degrees; roughly 200 m, invisible at state scale
)
topo_json = json.loads(topo.to_json())
for geom in topo_json["objects"]["data"]["geometries"]:
    geom["properties"].pop("__geom_name", None)

# ---------------------------------------------------------------------------
# 3. Write outputs
# ---------------------------------------------------------------------------
lea_out = lea_wide[["display_name", "name", "county", "geoid", "county_geoid"] + YEARS].rename(columns={"name": "dpi_name"})
lea_out.to_csv(CLEAN / "lea_adm_wide.csv", index_label="agency_code")
lea_out[["display_name", "dpi_name", "county", "geoid", "county_geoid"]].to_csv(CLEAN / "lea_crosswalk.csv", index_label="agency_code")

county_out = pd.concat(
    {"lea": county_lea, "charter": county_charter, "total": county_total}, axis=1
)
county_out.columns = [f"{kind}_{yr}" for kind, yr in county_out.columns]
county_out.insert(0, "county_geoid", [county_geoid[c] for c in county_out.index])
county_out.to_csv(CLEAN / "county_adm_wide.csv", index_label="county")
charter_by_county.to_csv(CLEAN / "charter_adm_by_county_wide.csv", index_label="county")

state_lea = lea_wide[YEARS].sum()
payload = {
    "years": YEARS,
    "leas": {
        code: {
            "name": row["display_name"],
            "county": row["county"],
            "countyId": row["county_geoid"],
            "adm": [int(row[y]) for y in YEARS],
        }
        for code, row in lea_wide.iterrows()
    },
    "counties": {
        county_geoid[c]: {
            "name": c,
            "lea": [int(v) for v in county_lea.loc[c]],
            "charter": [int(v) for v in county_charter.loc[c]],
            "charterSchools": [int(v) for v in charter_schools_by_county.reindex(all_counties).fillna(0).astype(int).loc[c]],
            "leaCodes": sorted(lea_wide.index[lea_wide["county"] == c].tolist()),
        }
        for c in all_counties
    },
    "state": {
        "lea": [int(v) for v in state_lea],
        "charter": [int(v) for v in charter_state],
        "charterVirtual": [int(v) for v in charter_virtual_state],
        "charterSchools": [int(v) for v in charter_adm.groupby("year")["agency_code"].nunique().reindex(YEARS)],
    },
    "bySpan": {
        "spans": {"E": "Elementary", "I": "Elementary + middle (K-8)", "M": "Middle", "H": "High", "A": "All grades", "T": "Middle + high", "U": "Unclassified"},
        "leas": {code: {sp: span_series(lea_span, code, sp) for sp in SPANS} for code in lea_wide.index},
        "countyCharter": {county_geoid[c]: {sp: span_series(charter_span_county, c, sp) for sp in SPANS} for c in all_counties},
        "stateLea": {sp: [int(lea_span[(sp, y)].sum()) if (sp, y) in lea_span.columns else 0 for y in YEARS] for sp in SPANS},
        "stateCharter": {sp: [int(charter_span_state.get((sp, y), 0)) for y in YEARS] for sp in SPANS},
    },
    "topology": topo_json,
}
(CLEAN / "dashboard_data.json").write_text(json.dumps(payload, separators=(",", ":")))

print(f"LEAs: {len(lea_wide)}   counties: {len(all_counties)}   charter schools 2025: {payload['state']['charterSchools'][-1]}")
print(f"State LEA ADM 2006 -> 2025: {state_lea.iloc[0]:,} -> {state_lea.iloc[-1]:,}")
print(f"State charter ADM 2006 -> 2025: {charter_state.iloc[0]:,} -> {charter_state.iloc[-1]:,}")
print("Elementary (E) ADM statewide 2006 -> 2025:", payload["bySpan"]["stateLea"]["E"][0], "->", payload["bySpan"]["stateLea"]["E"][-1],
      "| K-8 (I):", payload["bySpan"]["stateLea"]["I"][-1], "| charter E:", payload["bySpan"]["stateCharter"]["E"][-1])
print("CHCCS E:", payload["bySpan"]["leas"]["681LEA"]["E"])
lea_e = pd.DataFrame({code: payload["bySpan"]["leas"][code]["E"] for code in lea_wide.index}, index=YEARS).T
lea_e.insert(0, "display_name", lea_wide["display_name"])
lea_e.to_csv(CLEAN / "lea_elementary_adm_wide.csv", index_label="agency_code")
print(f"dashboard_data.json: {(CLEAN / 'dashboard_data.json').stat().st_size/1e6:.2f} MB")
