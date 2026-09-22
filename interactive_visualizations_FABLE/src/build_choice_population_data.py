"""
Build the data behind dashboard tabs 2 (private schools, home schools, vouchers) and
3 (school-age population), keyed to the same counties and LEAs as tab 1.

Inputs (data/raw/):
  dnpe_private/<yyyy-yy>.pdf|.docx   NC DNPE private school statistical summaries, 2005-06 .. 2025-26
  dnpe_home/<yyyy-yy>.pdf|.docx      NC DNPE home school statistical summaries, 2005-06 .. 2025-26
  ncseaa/*.pdf                       NCSEAA Opportunity Scholarship reports (county table 2024-25,
                                     annual reports with "prior LEA" tables)
  saipe/ussdYY.txt                   Census SAIPE school-district population estimates, 2005 .. 2024
  census_popest/*.csv                Census county population estimates by age, 2000 .. 2024
  ../cleaned/dashboard_data.json     tab-1 output, for county and LEA ids/names

Outputs (data/cleaned/):
  nonpublic_by_county_long.csv, population_county_long.csv, population_lea_long.csv,
  vouchers_prior_lea_long.csv, choice_population_data.json (what the HTML embeds)

Year convention everywhere: the school year's ENDING year (2025 == 2024-25). Population
estimates are dated July 1 and are matched to the school year that ENDS that June, i.e.
the estimate year and the DPI year label are the same (July 2024 estimate -> 2024 -> the
2023-24 school year). This is the convention the CHCCS notebook uses. The latest estimate
(2024) therefore leaves 2024-25 without a population value.
"""

import json
import re
from pathlib import Path

import docx
import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "cleaned"

tab1 = json.loads((CLEAN / "dashboard_data.json").read_text())
COUNTY_GEOID = {c["name"]: gid for gid, c in tab1["counties"].items()}
COUNTIES = sorted(COUNTY_GEOID)
LEA_NAME = {code: l["name"] for code, l in tab1["leas"].items()}
assert len(COUNTIES) == 100

ADM_YEARS = tab1["years"]                 # 2006 .. 2025
NP_YEARS = list(range(2006, 2027))        # non-public data runs one year further (2025-26)

# ---------------------------------------------------------------------------
# Helpers for the DNPE reports
# ---------------------------------------------------------------------------
COUNTY_ALT = "|".join(re.escape(c) for c in sorted(COUNTIES, key=len, reverse=True))
PAIR_RE = re.compile(rf"\b({COUNTY_ALT})\s+(\d{{1,3}}(?:[,.]\d{{3}})+|\d+)\b")

SKIP_RX = re.compile(r"(ENROLLMENT BY GRADE|BY GRADES?\b|BY SEX|BY GENDER|BY TYPE|BY AGE|CLASSIFIED BY|BY GRADE RANGES|"
                     r"ENROLLMENT BY GRADE & COUNTY|STATEWIDE ENROLLMENT)", re.I)
HEADINGS = {
    "dnpe_private": {
        "priv_enr": re.compile(r"PRIVATE SCHOOL ENROLLMENT BY COUNT", re.I),
        "priv_num": re.compile(r"(PRIVATE SCHOOL NUMBERS BY COUNT|NUMBER OF [A-Z\- ]*SCHOOLS BY COUNT|SCHOOLS BY COUNT)", re.I),
        "skip": SKIP_RX,
    },
    "dnpe_home": {
        "home_num": re.compile(r"(HOME SCHOOLS BY COUNT|NUMBER OF [A-Z ]*SCHOOLS BY COUNT)", re.I),
        "home_enr": re.compile(r"ESTIMATED ENROLLMENT BY COUNT", re.I),
        "skip": SKIP_RX,
    },
}


def to_int(s: str) -> int:
    return int(re.sub(r"[,.]", "", s))


def document_text(path: Path) -> str:
    """Whole report as one text blob; Word tables become 'County N County N ...' lines."""
    if path.suffix == ".docx":
        d = docx.Document(str(path))
        lines = []
        body = d.element.body
        for child in body.iterchildren():
            tag = child.tag.split("}")[1]
            if tag == "p":
                txt = "".join((t.text or "") if t.tag.endswith("}t") else "\t" for t in child.iter() if t.tag.endswith("}t") or t.tag.endswith("}tab"))
                lines.append(txt)
            elif tag == "tbl":
                for row in child.iter():
                    if row.tag.endswith("}tr"):
                        cells = []
                        for cell in row.iter():
                            if cell.tag.endswith("}tc"):
                                cells.append("".join(t.text or "" for t in cell.iter() if t.tag.endswith("}t")).strip())
                        lines.append("  ".join(cells))
        return "\n".join(lines)
    with pdfplumber.open(str(path)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


def parse_dnpe(path: Path, wanted: tuple[str, ...]) -> dict[str, dict[str, int]]:
    """Return {table_type: {county: value}} for the wanted table types in one report."""
    text = document_text(path)
    marks = []
    for kind, rx in HEADINGS[path.parent.name].items():
        for m in rx.finditer(text):
            marks.append((m.start(), kind))
    marks.sort()
    out: dict[str, dict[str, int]] = {}
    for i, (pos, kind) in enumerate(marks):
        if kind not in wanted:
            continue
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        seg = text[pos:end]
        vals: dict[str, int] = {}
        for name, num in PAIR_RE.findall(seg):
            if name not in vals:              # first occurrence wins (a continuation heading repeats nothing)
                vals[name] = to_int(num)
        if len(vals) >= 50:
            # merge if the same table type appears twice (table split across pages with a repeated heading)
            out.setdefault(kind, {}).update({k: v for k, v in vals.items() if k not in out.get(kind, {})})
    return out


def year_label_to_end_year(stem: str) -> int:
    return int(stem[:4]) + 1


def parse_dnpe_folder(folder: Path, wanted: tuple[str, ...]) -> tuple[pd.DataFrame, list[str]]:
    rows, notes = [], []
    for path in sorted(folder.iterdir()):
        if path.suffix not in (".pdf", ".docx"):
            continue
        year = year_label_to_end_year(path.stem)
        got = parse_dnpe(path, wanted)
        for kind in wanted:
            vals = got.get(kind, {})
            missing = [c for c in COUNTIES if c not in vals]
            if not vals:
                notes.append(f"{folder.name} {path.stem}: no '{kind}' table found")
            elif missing:
                notes.append(f"{folder.name} {path.stem} {kind}: {len(missing)} counties missing ({', '.join(missing[:6])}{'...' if len(missing) > 6 else ''})")
            for c in COUNTIES:
                rows.append({"year": year, "county": c, "kind": kind, "value": vals.get(c)})
    return pd.DataFrame(rows), notes


priv, notes_p = parse_dnpe_folder(RAW / "dnpe_private", ("priv_enr", "priv_num"))
home, notes_h = parse_dnpe_folder(RAW / "dnpe_home", ("home_num", "home_enr"))
nonpub = pd.concat([priv, home]).pivot_table(index=["county", "year"], columns="kind", values="value", aggfunc="first")
nonpub = nonpub.reindex(pd.MultiIndex.from_product([COUNTIES, NP_YEARS], names=["county", "year"]))
for k in ("priv_enr", "priv_num", "home_num", "home_enr"):
    if k not in nonpub.columns:
        nonpub[k] = None

# --- source typos found in review ----------------------------------------------
# Each entry is a value printed in a DNPE report that its own neighbours and totals
# show to be wrong. They are set to missing here and filled by the interpolation
# below, and listed in the dashboard notes. (year = school year ending year)
SOURCE_CORRECTIONS = [
    # 2013-14 home school report prints "Alexander 3"; 2012-13 = 304, 2014-15 = 337.
    ("home_num", "Alexander", 2014, "printed as 3; digits dropped in the report"),
    # 2022-23 home school report prints Alamance 3,610, identical to Iredell's entry on
    # the same line; neighbours are 2,454 and 2,235 and the report's own grand total
    # (152,717) is 1,828 below the sum of its county rows.
    ("home_enr", "Alamance", 2023, "printed as 3,610, duplicating Iredell's value"),
]
for kind, county, year, why in SOURCE_CORRECTIONS:
    nonpub.loc[(county, year), kind] = None

# --- fill the gaps we know about --------------------------------------------
# 2015-16 home school report is not published on the DNPE site; interpolate that
# year from 2014-15 and 2016-17 and flag it in the output.
interpolated = {}
for k in ("home_num", "home_enr", "priv_enr", "priv_num"):
    wide = nonpub[k].unstack("year").astype("float")
    before = wide.copy()
    wide = wide.interpolate(axis=1, limit_area="inside", limit=1)
    filled = (before.isna() & wide.notna())
    for county in wide.index:
        for yr in wide.columns:
            if filled.loc[county, yr]:
                interpolated.setdefault(k, set()).add(int(yr))
    nonpub[k] = wide.stack(future_stack=True).reindex(nonpub.index)
notes_fill = [f"{k}: interpolated years {sorted(v)}" for k, v in interpolated.items()]

# Statewide totals from the report text (for validation / the statewide chart)
def parse_state_totals(folder: Path, patterns: dict[str, str]) -> dict[int, dict[str, int]]:
    out = {}
    for path in sorted(folder.iterdir()):
        if path.suffix not in (".pdf", ".docx"):
            continue
        text = document_text(path)
        year = year_label_to_end_year(path.stem)
        rec = {}
        for key, rx in patterns.items():
            m = re.search(rx, text, re.I)
            if m:
                rec[key] = to_int(m.group(1))
        out[year] = rec
    return out

priv_state = parse_state_totals(RAW / "dnpe_private", {
    "students": r"Total students\s+(\d{1,3}(?:,\d{3})+|\d+)",
    "schools": r"Total schools\s+(\d{1,3}(?:,\d{3})+|\d+)",
})
home_state = parse_state_totals(RAW / "dnpe_home", {
    "students": r"(?:Total All Ages|Grand Total|Total)\s+(\d{1,3}(?:,\d{3})+)\s*$",
    "schools": r"(?:Statewide Total:?|Grand Total)\s+(\d{1,3}(?:,\d{3})+)",
})
# home-school reports: the by-age table total is the student estimate; the by-county schools total is schools
for year, rec in home_state.items():
    text = document_text(next(p for p in (RAW / "dnpe_home").iterdir() if year_label_to_end_year(p.stem) == year and p.suffix in (".pdf", ".docx")))
    m_students = re.findall(r"(?:Total All Ages|Grand Total|Total)\s+(\d{1,3}(?:,\d{3})+)", text)
    m_schools = re.findall(r"Statewide Total:?\s+(\d{1,3}(?:,\d{3})+)", text)
    if m_students:
        rec["students"] = max(to_int(x) for x in m_students)   # the largest total on the page is the all-ages student estimate
    if m_schools:
        rec["schools"] = to_int(m_schools[0])

# ---------------------------------------------------------------------------
# Opportunity Scholarships (vouchers)
# ---------------------------------------------------------------------------
def pdf_text(path: Path) -> str:
    with pdfplumber.open(str(path)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)

# 2024-25 recipients by county of residence (legislative staff table from NCSEAA data)
vtext = pdf_text(RAW / "ncseaa" / "os_2024-25_by_county.pdf")
voucher_county_2025 = {}
row_re = re.compile(rf"^({COUNTY_ALT})\s+(\d[\d,]*)\s+\d+%\s+(\d[\d,]*)\s+\d+%\s+(\d[\d,]*)\s+\d+%\s+(\d[\d,]*)\s+\d+%\s+(\d[\d,]*)\s*$", re.M)
for m in row_re.finditer(vtext):
    voucher_county_2025[m.group(1)] = to_int(m.group(6))
missing_v = [c for c in COUNTIES if c not in voucher_county_2025]
# The last row of a page can lose its total to a page break; fall back to the tier sum.
for m in re.finditer(rf"^({COUNTY_ALT})\s+(\d[\d,]*)\s+\d+%\s+(\d[\d,]*)\s+\d+%\s+(\d[\d,]*)\s+\d+%\s+(\d[\d,]*)\s+\d+%", vtext, re.M):
    if m.group(1) not in voucher_county_2025:
        voucher_county_2025[m.group(1)] = sum(to_int(m.group(i)) for i in (2, 3, 4, 5))
missing_v = [c for c in COUNTIES if c not in voucher_county_2025]
if missing_v:
    # a row can be lost from the text layer; look for it word by word
    with pdfplumber.open(str(RAW / "ncseaa" / "os_2024-25_by_county.pdf")) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            for i, w in enumerate(words):
                if w["text"] in missing_v:
                    nums = [x["text"] for x in words[i + 1:i + 10] if re.fullmatch(r"\d[\d,]*", x["text"])]
                    if len(nums) >= 5:
                        voucher_county_2025[w["text"]] = to_int(nums[4])
    missing_v = [c for c in COUNTIES if c not in voucher_county_2025]

# Annual reports: statewide totals and "prior LEA of new recipients"
def norm(s: str) -> str:
    s = s.lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    for w in ["public", "schools", "school", "system", "board of education", "graded", "district", "county", "city", "the", "of"]:
        s = re.sub(rf"\b{w}\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()

lea_by_norm = {norm(n): code for code, n in LEA_NAME.items()}
LEA_OVERRIDES = {
    "winston salem forsyth": "340LEA", "forsyth": "340LEA", "nash rocky mount": "640LEA", "nash": "640LEA",
    "elizabeth city pasquotank": "700LEA", "pasquotank": "700LEA", "robeson": "780LEA", "mooresville": "491LEA",
    "craven": "250LEA", "randolph": "760LEA", "charlotte mecklenburg": "600LEA", "chapel hill carrboro": "681LEA",
    "alamance burlington": "010LEA", "iredell statesville": "490LEA", "rowan salisbury": "800LEA",
    "edenton chowan": "210LEA", "newton conover": "182LEA", "clinton": "821LEA", "asheboro": "761LEA",
    "hickory": "181LEA", "kannapolis": "132LEA", "lexington": "291LEA", "thomasville": "292LEA",
    "roanoke rapids": "421LEA", "weldon": "422LEA", "whiteville": "241LEA", "elkin": "861LEA",
    "mount airy": "862LEA", "asheville": "111LEA",
}
def lea_code_for(name: str):
    k = norm(name)
    if k in LEA_OVERRIDES:
        return LEA_OVERRIDES[k]
    if k in lea_by_norm:
        return lea_by_norm[k]
    for kk, code in lea_by_norm.items():
        if kk == k or kk.replace(" ", "") == k.replace(" ", ""):
            return code
    return None

voucher_state = {}
voucher_prior_lea = {}
unmatched_lea_names = set()
for path in sorted((RAW / "ncseaa").glob("os_*_annual_report.pdf")):
    year = int(path.stem.split("_")[1][:4]) + 1
    text = pdf_text(path)
    m = re.search(r"scholarship funding for ([\d,]+) students", text)
    if m:
        voucher_state[year] = {"total": to_int(m.group(1))}
    m2 = re.search(r"New Students\s+([\d,]+)", text)
    if m2:
        voucher_state[year]["new"] = to_int(m2.group(1))
    # prior-LEA table: lines "Name N" between the heading and "Renewal Students"
    seg = re.search(r"Local Education Agency Recipients(.*?)(?:Renewal Students|Renewals)\s+[\d,]+", text, re.S)
    if seg:
        table = {}
        for line in seg.group(1).splitlines():
            mm = re.match(r"^(.*?[A-Za-z\)])\s+(\d[\d,]*)\s*$", line.strip())
            if not mm:
                continue
            nm, n = mm.group(1).strip(), to_int(mm.group(2))
            if nm.startswith("Local Education Agency"):
                continue
            code = lea_code_for(nm)
            if code:
                table[code] = table.get(code, 0) + n
            else:
                table.setdefault("_other", 0)
                table["_other"] += n
                unmatched_lea_names.add((year, nm))
        voucher_prior_lea[year] = table

# ---------------------------------------------------------------------------
# Population: Census SAIPE (school districts) and PEP (counties)
# ---------------------------------------------------------------------------
geoid_to_lea = {l_geoid: code for code, l_geoid in
                pd.read_csv(CLEAN / "lea_crosswalk.csv", dtype=str).set_index("agency_code")["geoid"].items()}
saipe_rows = []
for path in sorted((RAW / "saipe").glob("ussd*.txt")):
    est_year = 2000 + int(path.stem[4:6])
    for line in path.read_text(encoding="latin-1").splitlines():
        if not line.startswith("37 "):
            continue
        m = re.match(r"^37 (\d{5}) (.+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+\S+\s+\S+\s*$", line)
        if not m:
            continue
        geoid = "37" + m.group(1)
        if geoid in geoid_to_lea:
            saipe_rows.append({"year": est_year, "agency_code": geoid_to_lea[geoid],
                               "total_pop": int(m.group(3)), "pop_5_17": int(m.group(4)), "pov_5_17": int(m.group(5))})
saipe = pd.DataFrame(saipe_rows)
saipe_wide = saipe.pivot_table(index="agency_code", columns="year", values=["total_pop", "pop_5_17", "pov_5_17"])
assert set(saipe_wide.index) == set(LEA_NAME), set(LEA_NAME) ^ set(saipe_wide.index)
assert set(saipe_wide["pop_5_17"].columns) >= set(ADM_YEARS[:-1]), "SAIPE should cover 2006-2024"

# County: three vintages stitched together. AGE 5-17 = AGE513 + AGE1417 where available;
# the 2000-2010 intercensal file only has 5-year groups, so 15-17 is taken as 3/5 of 15-19.
pe = RAW / "census_popest"
c0 = pd.read_csv(pe / "co-est00int-alldata-37.csv", encoding="latin-1", dtype={"COUNTY": str})
c0["county"] = c0["CTYNAME"].str.replace(" County", "", regex=False)
# YEAR codes: 2=7/1/2000 ... 11=7/1/2009 (12=4/1/2010 census, 13=7/1/2010 estimate)
# AGEGRP codes: 0 = under 1, 1 = 1-4, 2 = 5-9, 3 = 10-14, 4 = 15-19, ... 18 = 85+, 99 = total
c0 = c0[c0["YEAR"].between(2, 11)].copy()
c0["est_year"] = 1998 + c0["YEAR"]
tot0 = c0[c0["AGEGRP"] == 99].set_index(["county", "est_year"])["TOT_POP"]
g = c0[c0["AGEGRP"].isin([2, 3, 4])].pivot_table(index=["county", "est_year"], columns="AGEGRP", values="TOT_POP")
g519 = g[2] + g[3] + g[4]                           # ages 5-19 (5-year groups only in this vintage)

c1 = pd.read_csv(pe / "cc-est2019-agesex-37.csv", encoding="latin-1")
c1["county"] = c1["CTYNAME"].str.replace(" County", "", regex=False)
c1 = c1[c1["YEAR"].between(3, 12)].copy()          # 3=7/1/2010 ... 12=7/1/2019
c1["est_year"] = 2007 + c1["YEAR"]
# Convert 5-19 to 5-17 with each county's own July-2010 ratio of (5-17)/(5-19). A flat
# 3/5 share of 15-19 would badly overstate 15-17 in college counties (Orange, Watauga,
# Pitt, ...) where 18- and 19-year-old students swell the 15-19 group.
base10 = c1[c1["YEAR"] == 3].set_index("county")
ratio = ((base10["AGE513_TOT"] + base10["AGE1417_TOT"]) / (base10["AGE59_TOT"] + base10["AGE1014_TOT"] + base10["AGE1519_TOT"]))
age0 = (g519 * g519.index.get_level_values("county").map(ratio).values).round().astype(int)
c2 = pd.read_csv(pe / "cc-est2024-agesex-37.csv", encoding="latin-1")
c2["county"] = c2["CTYNAME"].str.replace(" County", "", regex=False)
c2 = c2[c2["YEAR"].between(2, 6)].copy()           # 2=7/1/2020 ... 6=7/1/2024
c2["est_year"] = 2018 + c2["YEAR"]
recent = pd.concat([c1, c2])
tot1 = recent.set_index(["county", "est_year"])["POPESTIMATE"]
age1 = (recent.set_index(["county", "est_year"])["AGE513_TOT"] + recent.set_index(["county", "est_year"])["AGE1417_TOT"])

county_tot = pd.concat([tot0, tot1]).sort_index()
county_age = pd.concat([age0, age1]).sort_index()
county_pop = pd.DataFrame({"total_pop": county_tot, "pop_5_17": county_age}).reset_index()
county_pop["year"] = county_pop["est_year"]                          # July 2024 estimate -> 2024 -> the 2023-24 school year
county_pop = county_pop[county_pop["year"].isin(ADM_YEARS)]
assert set(county_pop["county"]) == set(COUNTIES)
cp_wide = county_pop.pivot_table(index="county", columns="year", values=["total_pop", "pop_5_17"])
assert cp_wide["pop_5_17"].notna().all().all() and list(cp_wide["pop_5_17"].columns) == ADM_YEARS[:-1]

# ---------------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------------
CLEAN.mkdir(exist_ok=True)
np_long = nonpub.reset_index().rename(columns={"priv_enr": "private_students", "priv_num": "private_schools",
                                               "home_num": "home_schools", "home_enr": "home_students_est"})
np_long["county_geoid"] = np_long["county"].map(COUNTY_GEOID)
np_long.to_csv(CLEAN / "nonpublic_by_county_long.csv", index=False)
county_pop.assign(county_geoid=county_pop["county"].map(COUNTY_GEOID))[["county", "county_geoid", "year", "total_pop", "pop_5_17"]].to_csv(CLEAN / "population_county_long.csv", index=False)
saipe.sort_values(["agency_code", "year"]).to_csv(CLEAN / "population_lea_long.csv", index=False)
pd.DataFrame([{"year": y, "agency_code": k, "new_recipients_prior_lea": v} for y, t in voucher_prior_lea.items() for k, v in t.items()]).to_csv(CLEAN / "vouchers_prior_lea_long.csv", index=False)

def series(df_wide, col, key, years):
    s = df_wide[col].loc[key] if col else df_wide.loc[key]
    return [None if pd.isna(s.get(y)) else int(round(s.get(y))) for y in years]

np_by_kind = {k: nonpub[k].unstack("year") for k in ("priv_enr", "priv_num", "home_num", "home_enr")}
payload = {
    "npYears": NP_YEARS,
    "popYears": ADM_YEARS,
    "nonpublic": {
        COUNTY_GEOID[c]: {
            "private": series(np_by_kind["priv_enr"], None, c, NP_YEARS),
            "privateSchools": series(np_by_kind["priv_num"], None, c, NP_YEARS),
            "home": series(np_by_kind["home_enr"], None, c, NP_YEARS),
            "homeSchools": series(np_by_kind["home_num"], None, c, NP_YEARS),
        } for c in COUNTIES
    },
    "nonpublicState": {
        "private": [priv_state.get(y, {}).get("students") for y in NP_YEARS],
        "privateSchools": [priv_state.get(y, {}).get("schools") for y in NP_YEARS],
        "home": [home_state.get(y, {}).get("students") for y in NP_YEARS],
        "homeSchools": [home_state.get(y, {}).get("schools") for y in NP_YEARS],
        "privateCountySum": [int(np_by_kind["priv_enr"][y].sum()) if np_by_kind["priv_enr"][y].notna().any() else None for y in NP_YEARS],
        "homeCountySum": [int(np_by_kind["home_enr"][y].sum()) if np_by_kind["home_enr"][y].notna().any() else None for y in NP_YEARS],
    },
    "interpolated": {k: sorted(v) for k, v in interpolated.items()},
    "corrections": [{"kind": k, "county": c, "year": y, "why": w} for k, c, y, w in SOURCE_CORRECTIONS],
    "vouchers": {
        "countyYear": 2025,
        "byCounty": {COUNTY_GEOID[c]: n for c, n in voucher_county_2025.items() if c in COUNTY_GEOID},
        "state": voucher_state,
        "priorLea": {str(y): {k: v for k, v in t.items()} for y, t in voucher_prior_lea.items()},
    },
    "population": {
        "counties": {COUNTY_GEOID[c]: {"total": series(cp_wide, "total_pop", c, ADM_YEARS), "age517": series(cp_wide, "pop_5_17", c, ADM_YEARS)} for c in COUNTIES},
        "leas": {code: {"total": series(saipe_wide, "total_pop", code, ADM_YEARS), "age517": series(saipe_wide, "pop_5_17", code, ADM_YEARS), "pov517": series(saipe_wide, "pov_5_17", code, ADM_YEARS)} for code in LEA_NAME},
    },
}
(CLEAN / "choice_population_data.json").write_text(json.dumps(payload, separators=(",", ":")))

print("=== parse notes ===")
for n in notes_p + notes_h + notes_fill:
    print(" -", n)
print("voucher county rows:", len(voucher_county_2025), "missing:", missing_v)
print("voucher state totals:", voucher_state)
print("prior-LEA years:", {y: len(t) for y, t in voucher_prior_lea.items()}, "unmatched:", sorted(unmatched_lea_names)[:12])
print("private statewide:", {y: v for y, v in priv_state.items()})
print("home statewide:", {y: v for y, v in home_state.items()})
print("county sums private:", payload["nonpublicState"]["privateCountySum"])
print("county sums home:", payload["nonpublicState"]["homeCountySum"])
print("Orange County nonpublic:", payload["nonpublic"][COUNTY_GEOID["Orange"]])
print("Orange County pop 5-17:", payload["population"]["counties"][COUNTY_GEOID["Orange"]]["age517"])
print("CHCCS pop 5-17:", payload["population"]["leas"]["681LEA"]["age517"])
print(f"choice_population_data.json: {(CLEAN / 'choice_population_data.json').stat().st_size/1e6:.2f} MB")
