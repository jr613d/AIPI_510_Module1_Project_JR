"""
Sanity checks on the cleaned dashboard data. Run after build_dashboard_data.py:

    .venv/bin/python tests/check_dashboard_data.py

Plain asserts, no test framework needed.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "data" / "cleaned" / "dashboard_data.json").read_text())

years = d["years"]
assert years == list(range(2006, 2026)), years
assert len(d["leas"]) == 115, len(d["leas"])
assert len(d["counties"]) == 100, len(d["counties"])

# every LEA has a full series of positive integers
for code, lea in d["leas"].items():
    assert len(lea["adm"]) == 20 and all(v > 0 for v in lea["adm"]), code
    assert lea["countyId"] in d["counties"], code

# county LEA totals equal the sum of their member districts
for cid, c in d["counties"].items():
    for i in range(20):
        assert c["lea"][i] == sum(d["leas"][k]["adm"][i] for k in c["leaCodes"]), (cid, i)

# statewide totals equal the sum over LEAs / counties (+ virtual charters)
for i in range(20):
    assert d["state"]["lea"][i] == sum(l["adm"][i] for l in d["leas"].values()), i
    county_charter = sum(c["charter"][i] for c in d["counties"].values())
    assert d["state"]["charter"][i] == county_charter + d["state"]["charterVirtual"][i], i

# known figures, cross-checked against the CHCCS board deck (11,065 in 2024-25)
chccs = d["leas"]["681LEA"]["adm"]
assert chccs[-1] == 11065 and max(chccs) == 12335 and years[chccs.index(12335)] == 2019

# geometry: one polygon per LEA and per county, ids match the series
geoms = d["topology"]["objects"]["data"]["geometries"]
lea_ids = {g["properties"]["id"] for g in geoms if g["properties"]["layer"] == "lea"}
county_ids = {g["properties"]["id"] for g in geoms if g["properties"]["layer"] == "county"}
assert lea_ids == set(d["leas"]), lea_ids ^ set(d["leas"])
assert county_ids == set(d["counties"]), county_ids ^ set(d["counties"])

print("all checks passed")

# ---------------------------------------------------------------------------
# Tabs 2 and 3 data
# ---------------------------------------------------------------------------
d2 = json.loads((ROOT / "data" / "cleaned" / "choice_population_data.json").read_text())
assert d2["npYears"] == list(range(2006, 2027)) and d2["popYears"] == years
assert set(d2["nonpublic"]) == set(d["counties"])
assert set(d2["population"]["counties"]) == set(d["counties"])
assert set(d2["population"]["leas"]) == set(d["leas"])
for gid, c in d2["nonpublic"].items():
    assert len(c["private"]) == 21 and len(c["home"]) == 21, gid
    assert all(v is not None and v >= 0 for v in c["private"]), gid
    assert all(v is not None and v >= 0 for v in c["home"]), gid
# population is aligned estimate-year = DPI year, so the last year (2024-25) has no value yet
for gid, c in d2["population"]["counties"].items():
    assert all(v > 0 for v in c["age517"][:-1]) and all(v > 0 for v in c["total"][:-1]) and c["age517"][-1] is None, gid
    assert all(a < t for a, t in zip(c["age517"][:-1], c["total"][:-1])), gid
for code, l in d2["population"]["leas"].items():
    assert all(v > 0 for v in l["age517"][:-1]) and all(v > 0 for v in l["total"][:-1]) and l["age517"][-1] is None, code
# known figures from the source reports
assert d2["nonpublicState"]["private"][d2["npYears"].index(2025)] == 135738
assert d2["nonpublicState"]["home"][d2["npYears"].index(2025)] == 165243
assert d2["vouchers"]["byCounty"]["37135"] == 616         # Orange County, 2024-25
assert d2["vouchers"]["state"]["2025"]["total"] == 80472
assert d2["population"]["leas"]["681LEA"]["age517"][-2] == 12309   # SAIPE 2024 -> DPI year 2024 (2023-24), as in the notebook
assert d2["population"]["leas"]["681LEA"]["age517"][years.index(2019)] == 13065 and d2["population"]["leas"]["681LEA"]["total"][years.index(2019)] == 93239
print("tab 2/3 checks passed")

# ---------------------------------------------------------------------------
# Tab 0: ADM by school grade-span category
# ---------------------------------------------------------------------------
bs = d["bySpan"]
assert set(bs["leas"]) == set(d["leas"])
for code, spans in bs["leas"].items():
    total = [sum(spans[sp][i] for sp in spans) for i in range(20)]
    # school rows (by span, including the few unclassified ones) sum exactly to the district total
    assert total == d["leas"][code]["adm"], code
assert bs["leas"]["681LEA"]["E"][-1] == 4522 and bs["leas"]["681LEA"]["E"][-1] * 11 // 11 == 4522
assert bs["leas"]["030LEA"]["E"] == [0] * 20          # Alleghany: K-8 only
assert bs["stateLea"]["E"][-1] == 580857
print("tab 0 checks passed")
