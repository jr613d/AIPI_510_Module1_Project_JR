"""
Download the raw files that are NOT committed to the repository because they are large and
freely re-downloadable from the Census Bureau and NCES. Everything else in data/raw/ (DPI
tables, DNPE reports, NCSEAA reports, board documents) is committed.

    .venv/bin/python src/fetch_raw_data.py            # skips files that already exist
    .venv/bin/python src/fetch_raw_data.py --force    # re-download everything
    .venv/bin/python src/fetch_raw_data.py --dest DIR # write somewhere else (for testing)

Files fetched:
  data/raw/cb_2023_37_unsd_500k.zip, cb_2023_us_county_500k.zip     Census cartographic boundaries
  data/raw/saipe/ussd05.txt ... ussd24.txt                          Census SAIPE school-district estimates
  data/raw/census_popest/co-est00int-alldata-37.csv,
                         cc-est2019-agesex-37.csv, cc-est2024-agesex-37.csv
                                                                    Census county population by age
  data/raw/nces/EDGE_GEOCODE_PRIVATESCH_2122.xlsx,
                EDGE_GEOCODE_PUBLICSCH_2324.xlsx                    NCES school coordinates
  data/raw/nces/pss2122_nc.csv                                      NCES Private School Survey 2021-22, NC rows only
"""
import argparse
import io
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CENSUS = "https://www2.census.gov"
NCES = "https://nces.ed.gov"

FILES = {
    "cb_2023_37_unsd_500k.zip": f"{CENSUS}/geo/tiger/GENZ2023/shp/cb_2023_37_unsd_500k.zip",
    "cb_2023_us_county_500k.zip": f"{CENSUS}/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip",
    "census_popest/co-est00int-alldata-37.csv": f"{CENSUS}/programs-surveys/popest/datasets/2000-2010/intercensal/county/co-est00int-alldata-37.csv",
    "census_popest/cc-est2019-agesex-37.csv": f"{CENSUS}/programs-surveys/popest/datasets/2010-2019/counties/asrh/cc-est2019-agesex-37.csv",
    "census_popest/cc-est2024-agesex-37.csv": f"{CENSUS}/programs-surveys/popest/datasets/2020-2024/counties/asrh/cc-est2024-agesex-37.csv",
}
for y in range(2005, 2025):
    FILES[f"saipe/ussd{y % 100:02d}.txt"] = f"{CENSUS}/programs-surveys/saipe/datasets/{y}/{y}-school-districts/ussd{y % 100:02d}.txt"
ZIPPED = {  # target -> (zip url, member suffix inside the zip)
    "nces/EDGE_GEOCODE_PRIVATESCH_2122.xlsx": (f"{NCES}/programs/edge/data/EDGE_GEOCODE_PRIVATESCH_2122.zip", "EDGE_GEOCODE_PRIVATESCH_2122.xlsx"),
    "nces/EDGE_GEOCODE_PUBLICSCH_2324.xlsx": (f"{NCES}/programs/edge/data/EDGE_GEOCODE_PUBLICSCH_2324.zip", "EDGE_GEOCODE_PUBLICSCH_2324.xlsx"),
}
PSS_URL = f"{NCES}/surveys/pss/zip/pss2122_pu_csv.zip"


def curl(url: str) -> bytes:
    """Fetch with curl; the interpreter's own CA bundle does not always trust these hosts."""
    r = subprocess.run(["curl", "-sSL", "-m", "600", "-A", "Mozilla/5.0", url], capture_output=True, timeout=700)
    if r.returncode != 0 or len(r.stdout) < 1000:
        raise RuntimeError(f"download failed: {url}\n{r.stderr.decode()[:300]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dest", default=str(ROOT / "data" / "raw"))
    args = ap.parse_args()
    dest = Path(args.dest)
    done = skipped = 0

    def want(rel: str) -> bool:
        p = dest / rel
        if p.exists() and not args.force:
            return False
        p.parent.mkdir(parents=True, exist_ok=True)
        return True

    for rel, url in FILES.items():
        if want(rel):
            (dest / rel).write_bytes(curl(url)); done += 1; print("fetched", rel)
        else:
            skipped += 1
    for rel, (url, member) in ZIPPED.items():
        if want(rel):
            with zipfile.ZipFile(io.BytesIO(curl(url))) as z:
                name = next(n for n in z.namelist() if n.endswith(member))
                (dest / rel).write_bytes(z.read(name))
            done += 1; print("fetched", rel)
        else:
            skipped += 1
    rel = "nces/pss2122_nc.csv"
    if want(rel):
        import pandas as pd
        with zipfile.ZipFile(io.BytesIO(curl(PSS_URL))) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
            df = pd.read_csv(io.BytesIO(z.read(name)), encoding="latin-1", low_memory=False, dtype=str)
        nc = df[df["PSTABB"].str.strip() == "NC"]
        keep = [c for c in nc.columns if not c.startswith("REPW")]
        nc[keep].to_csv(dest / rel, index=False); done += 1; print("fetched", rel, f"({len(nc)} NC schools)")
    else:
        skipped += 1
    print(f"done: {done} fetched, {skipped} already present")


if __name__ == "__main__":
    sys.exit(main())
