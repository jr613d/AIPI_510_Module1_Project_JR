"""
Inventory of K-5 school options other than CHCCS within 25 miles of the district's centre,
with coordinates for the podcast map.

Sources (data/raw/):
  nc_dpi_rcd_location_2024-25.xlsx          charter schools, grade spans, cities (2024-25)
  nc_dpi_rcd_adm_2024-25.csv                charter ADM 2024-25
  nces/EDGE_GEOCODE_PUBLICSCH_2324.xlsx     NCES coordinates for public (incl. charter) schools
  nces/pss2122_nc.csv                       NCES Private School Universe Survey 2021-22, NC rows
  nces/EDGE_GEOCODE_PRIVATESCH_2122.xlsx    NCES coordinates for private schools (joined on PPIN)
  dnpe_directory/dnpe_private_school_directory_2026-01.csv
                                            NC DNPE private school directory (Jan 2026); schools
                                            missing from the 2021-22 survey are geocoded with the
                                            Census Bureau geocoder
  ncseaa/os_2023-24_annual_report.pdf       Opportunity Scholarship recipients by nonpublic school
  cb_2023_37_unsd_500k.zip                  CHCCS boundary -> centroid

Output: data/cleaned/school_options.json, data/cleaned/school_options.csv
"""
import io
import json
import math
import re
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
import pdfplumber
import shapefile
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parent.parent
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "cleaned"
RADIUS_MAX = 25.0
NEARBY_COUNTIES = {"Orange", "Durham", "Chatham", "Wake", "Alamance", "Person", "Lee", "Granville", "Caswell", "Randolph"}

# ---------------------------------------------------------------- district centre
with zipfile.ZipFile(RAW / "cb_2023_37_unsd_500k.zip") as z:
    base = [n for n in z.namelist() if n.endswith(".shp")][0][:-4]
    rdr = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), dbf=io.BytesIO(z.read(base + ".dbf")), shx=io.BytesIO(z.read(base + ".shx")))
chccs_geom = next(shape(sr.shape.__geo_interface__) for sr in rdr.shapeRecords() if sr.record["GEOID"] == "3700720")
CLON, CLAT = chccs_geom.centroid.x, chccs_geom.centroid.y


def miles(lat, lon):
    r = 3958.7613
    p1, p2 = math.radians(CLAT), math.radians(lat)
    dphi, dl = math.radians(lat - CLAT), math.radians(lon - CLON)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def norm(s):
    s = str(s).lower().replace("&", "and").replace("st.", "st").replace("saint", "st")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\b(the|of|inc|school|schools|academy|charter|elementary|catholic|christian|day|for|at|a|an)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- grade helpers
def dpi_grade(code):
    return {"PK": -1, "0K": 0, "KG": 0, "K": 0}.get(code, int(code) if code.isdigit() else None)

PSS_GRADE = {1: "ungraded", 2: "PK", 3: "K", 4: "T1", 5: "T1", 6: "1", 7: "2", 8: "3", 9: "4", 10: "5", 11: "6", 12: "7", 13: "8", 14: "9", 15: "10", 16: "11", 17: "12"}
PSS_NUM = {2: -1, 3: 0, 4: 0, 5: 1, 6: 1, 7: 2, 8: 3, 9: 4, 10: 5, 11: 6, 12: 7, 13: 8, 14: 9, 15: 10, 16: 11, 17: 12}
TYPOLOGY = {1: "Catholic (parochial)", 2: "Catholic (diocesan)", 3: "Catholic (private order)", 4: "Conservative Christian", 5: "Other religious (affiliated)", 6: "Other religious (unaffiliated)", 7: "Nonsectarian (regular)", 8: "Nonsectarian (special emphasis)", 9: "Nonsectarian (special education)"}


def serves_k5(lo, hi):
    return lo is not None and hi is not None and lo <= 5 and hi >= 0


schools = []

# ---------------------------------------------------------------- charters (DPI + NCES coordinates)
loc = pd.read_excel(RAW / "nc_dpi_rcd_location_2024-25.xlsx", dtype=str)
loc["year"] = loc["year"].astype(int)
adm = pd.read_csv(RAW / "nc_dpi_rcd_adm_2024-25.csv", dtype={"agency_code": str, "category_code": str})
adm25 = adm[(adm["year"] == 2025) & adm["category_code"].isna()].set_index("agency_code")["avg_student_num"]
charters = loc[(loc["year"] == 2025) & (loc["agency_level"] == "SCH") & (loc["designation_Type"] == "C")].copy()
first_year = loc[(loc["agency_level"] == "SCH") & (loc["designation_Type"] == "C")].groupby("agency_code")["year"].min()
pub = pd.read_excel(RAW / "nces" / "EDGE_GEOCODE_PUBLICSCH_2324.xlsx", dtype=str)
pub = pub[pub["STATE"] == "NC"].copy()
pub["key"] = pub["NAME"].map(norm)
pub_by_key = {}
for _, r in pub.iterrows():
    pub_by_key.setdefault(r["key"], []).append(r)

unmatched_charters = []
for _, c in charters.iterrows():
    if c["agency_code"][:3] in ("00A", "00B"):
        continue                                                   # statewide virtual, handled below
    key = norm(c["name"])
    cands = pub_by_key.get(key, [])
    if not cands:
        cands = [r for k, rows in pub_by_key.items() for r in rows if key and (key in k or k in key) and abs(len(k) - len(key)) <= 6]
    if len(cands) > 1:
        same_city = [r for r in cands if str(r["CITY"]).strip().lower() == str(c["city"]).strip().lower()]
        cands = same_city or cands[:1]
    if not cands:
        unmatched_charters.append((c["agency_code"], c["name"], c["city"]))
        continue
    r = cands[0]
    lat, lon = float(r["LAT"]), float(r["LON"])
    d = miles(lat, lon)
    if d > RADIUS_MAX:
        continue
    lo_s, hi_s = str(c["grade_span"]).split(":") if ":" in str(c["grade_span"]) else (None, None)
    lo, hi = (dpi_grade(lo_s), dpi_grade(hi_s)) if lo_s else (None, None)
    schools.append({
        "id": c["agency_code"], "name": c["name"], "type": "charter", "grades": str(c["grade_span"]).replace("0K", "K").replace(":", "-"),
        "servesK5": serves_k5(lo, hi), "students": int(adm25.get(c["agency_code"], 0)) or None, "studentsYear": "2024-25 ADM",
        "city": c["city"], "county": c["county"], "lat": lat, "lon": lon, "miles": round(d, 1),
        "typology": "Public charter (tuition-free, lottery)", "opened": int(first_year.get(c["agency_code"], 0)) or None, "source": "NC DPI 2024-25; NCES EDGE 2023-24 coordinates",
    })

# ---------------------------------------------------------------- private schools (PSS 2021-22 + NCES coordinates)
pss = pd.read_csv(RAW / "nces" / "pss2122_nc.csv", dtype=str)
geo = pd.read_excel(RAW / "nces" / "EDGE_GEOCODE_PRIVATESCH_2122.xlsx", dtype=str).set_index("PPIN")
pss_keys = set()
for _, p in pss.drop_duplicates("PPIN").iterrows():
    if p["PPIN"] not in geo.index:
        continue
    g = geo.loc[p["PPIN"]]
    lat, lon = float(g["LAT"]), float(g["LON"])
    d = miles(lat, lon)
    pss_keys.add(norm(p["PINST"]))
    if d > RADIUS_MAX:
        continue
    lo, hi = int(p["LOGR2022"]), int(p["HIGR2022"])
    schools.append({
        "id": "PSS" + p["PPIN"], "name": str(p["PINST"]).title().replace("'S", "'s"), "type": "private",
        "grades": PSS_GRADE.get(lo, "?") + "-" + PSS_GRADE.get(hi, "?"), "servesK5": serves_k5(PSS_NUM.get(lo), PSS_NUM.get(hi)),
        "students": int(p["NUMSTUDS"]) if str(p["NUMSTUDS"]).isdigit() else None, "studentsYear": "2021-22 (NCES survey)",
        "city": str(g["CITY"]).title(), "county": str(g["NMCNTY"]).replace(" County", ""), "lat": lat, "lon": lon, "miles": round(d, 1),
        "typology": TYPOLOGY.get(int(p["TYPOLOGY"]) if str(p["TYPOLOGY"]).isdigit() else 0, "Private"), "opened": None,
        "source": "NCES Private School Survey 2021-22; NCES EDGE coordinates",
    })

# ---------------------------------------------------------------- DNPE directory: schools not in the 2021-22 survey
dnpe = pd.read_csv(RAW / "dnpe_directory" / "dnpe_private_school_directory_2026-01.csv", encoding="utf-8-sig", dtype=str)
dnpe = dnpe[dnpe["County"].str.strip().isin(NEARBY_COUNTIES)]
geocode_log = []


def census_geocode(addr):
    url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?" + urllib.parse.urlencode({"address": addr, "benchmark": "Public_AR_Current", "format": "json"})
    try:
        out = subprocess.run(["curl", "-sL", "-m", "30", url], capture_output=True, text=True, timeout=40).stdout
        js = json.loads(out)
        m = js["result"]["addressMatches"]
        if m:
            return float(m[0]["coordinates"]["y"]), float(m[0]["coordinates"]["x"])
    except Exception as e:            # noqa: BLE001 - log and move on
        geocode_log.append(f"{addr}: {e}")
    return None


for _, r in dnpe.iterrows():
    key = norm(r["SchoolName"])
    if key in pss_keys or any(key and (key in k or k in key) and abs(len(k) - len(key)) <= 4 for k in pss_keys):
        continue
    street = r["PhysicalAddress"] if isinstance(r["PhysicalAddress"], str) else r["Street"]
    city = r["PhysicalCity"] if isinstance(r["PhysicalCity"], str) else r["City"]
    zipc = r["PhysicalZip"] if isinstance(r["PhysicalZip"], str) else r["Zip"]
    if not isinstance(street, str) or not isinstance(city, str):
        geocode_log.append(f"{r['SchoolName']}: no address in directory")
        continue
    hit = census_geocode(f"{street}, {city}, NC {zipc if isinstance(zipc, str) else ''}")
    approx = False
    if not hit:
        # second try: strip suite/unit text and use only the first street in a compound address
        cleaned = re.split(r",| and | & | #|Ste|Suite|Unit", street)[0].strip()
        hit = census_geocode(f"{cleaned}, {city}, NC {zipc if isinstance(zipc, str) else ''}")
    if not hit and isinstance(zipc, str):
        # last resort: the ZIP code's location, flagged as approximate (roughly a mile or two)
        hit = census_geocode(f"{city}, NC {zipc}")
        approx = hit is not None
    time.sleep(0.2)
    if not hit:
        geocode_log.append(f"{r['SchoolName']}: geocoder found no match for {street}, {city}")
        continue
    lat, lon = hit
    d = miles(lat, lon)
    if d > RADIUS_MAX:
        continue
    schools.append({
        "id": "DNPE" + re.sub(r"\W", "", r["SchoolName"])[:24], "name": r["SchoolName"].strip(), "type": "private", "grades": "not reported",
        "servesK5": None, "students": None, "studentsYear": None, "city": city.title(), "county": r["County"].strip(), "lat": lat, "lon": lon, "miles": round(d, 1),
        "typology": "Private (in DNPE directory, not in the 2021-22 NCES survey)", "opened": None, "source": "NC DNPE directory Jan 2026; Census geocoder" + (" (ZIP-level, approximate)" if approx else ""),
        "approx": approx,
    })

# ---------------------------------------------------------------- vouchers by nonpublic school (NCSEAA 2023-24)
vt = "\n".join((p.extract_text() or "") for p in pdfplumber.open(str(RAW / "ncseaa" / "os_2023-24_annual_report.pdf")).pages)
vouchers = {}
cities = sorted({str(c).strip().lower() for c in pd.concat([pub["CITY"], geo["CITY"], dnpe["PhysicalCity"], dnpe["City"]]).dropna()}, key=len, reverse=True)
for line in vt.splitlines():
    m = re.match(r"^(.+?)\s+(\d[\d,]*)\s+\$[\d,]+\s*$", line)
    if not m or m.group(1).startswith("Nonpublic"):
        continue
    head, n = m.group(1).strip(), int(m.group(2).replace(",", ""))
    low = head.lower()
    city = next((c for c in cities if low.endswith(" " + c)), None)
    name = head[: -len(city) - 1] if city else head
    vouchers[norm(name)] = n
for s in schools:
    if s["type"] == "private":
        k = norm(s["name"])
        v = vouchers.get(k)
        if v is None:
            for vk, vv in vouchers.items():
                if k and (k == vk or (len(k) > 6 and (k in vk or vk in k))):
                    v = vv
                    break
        s["vouchers2024"] = v

# ---------------------------------------------------------------- CHCCS elementary schools (for the map) and virtual charters
chccs_el = []
for _, r in pub[pub["LEAID"] == "3700720"].iterrows():
    if re.search(r"Elementary|Elem", r["NAME"]):
        chccs_el.append({"name": r["NAME"], "lat": float(r["LAT"]), "lon": float(r["LON"])})
virtual = [{"name": c["name"], "grades": str(c["grade_span"]).replace("0K", "K").replace(":", "-"), "students": int(adm25.get(c["agency_code"], 0))}
           for _, c in charters.iterrows() if c["agency_code"][:3] in ("00A", "00B")]

# ---------------------------------------------------------------- write
schools.sort(key=lambda s: s["miles"])
payload = {"center": {"lat": CLAT, "lon": CLON}, "radii": [5, 25], "schools": schools, "chccsElementary": chccs_el, "virtualCharters": virtual,
           "notes": {"unmatchedCharters": unmatched_charters, "geocodeLog": geocode_log}}
(CLEAN / "school_options.json").write_text(json.dumps(payload, separators=(",", ":")))
pd.DataFrame(schools).to_csv(CLEAN / "school_options.csv", index=False)
within5 = [s for s in schools if s["miles"] <= 5]
print(f"centre {CLAT:.4f}, {CLON:.4f}; schools within 25 mi: {len(schools)} (charter {sum(s['type']=='charter' for s in schools)}, private {sum(s['type']=='private' for s in schools)})")
print(f"within 5 mi: {len(within5)}")
for s in within5:
    print(f"  {s['miles']:4.1f} mi  {s['type']:8s} {s['name'][:45]:45s} {s['grades']:12s} K-5={s['servesK5']} students={s['students']} vouchers={s.get('vouchers2024')}")
near_unmatched = [u for u in unmatched_charters if loc[(loc["agency_code"] == u[0]) & (loc["year"] == 2025)]["county"].iloc[0] in NEARBY_COUNTIES]
print("unmatched charters statewide:", len(unmatched_charters), "| in nearby counties:", near_unmatched)
print("geocode log:", geocode_log[:10])
print("CHCCS elementary geocoded:", len(chccs_el), "virtual:", virtual)
