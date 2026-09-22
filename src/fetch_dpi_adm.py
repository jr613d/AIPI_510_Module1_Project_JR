"""
Pulls CHCCS's real historical enrollment (Average Daily Membership) out of
NC DPI's official School Report Card bulk data.

Why this exists: NC DPI publishes enrollment as one clean, official table
(rcd_adm) inside a public ZIP download. 

The full ZIP is large (~270MB combined) because it bundles ~67 unrelated
tables. Rather than re-download that every time, this script works from a
copy of the one file we need that's already saved in data_sources/
(nc_dpi_rcd_adm_2024-25.xlsx). See data_sources/INDEX.md for where that
file came from.
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = PROJECT_ROOT / "data_sources" / "nc_dpi_rcd_adm_2024-25.xlsx"
OUT_FILE = PROJECT_ROOT / "data" / "cleaned" / "district_adm_history.csv"

CHCCS_AGENCY_CODE = "681LEA"  # the district-wide total row, confirmed against
                              # the board deck's own reported 2025 figure (11,065)


def load_chccs_adm_history() -> pd.DataFrame:
    """Return CHCCS's real historical district-wide ADM, one row per year."""
    df = pd.read_excel(RAW_FILE, sheet_name="Sheet1")

    # category_code blank == "all grades combined" (the district total we want,
    # not a single grade-span slice -- see data_sources/INDEX.md for the schema)
    chccs = df[
        (df["agency_code"] == CHCCS_AGENCY_CODE) & (df["category_code"].isna() | (df["category_code"] == ""))
    ].copy()

    chccs = chccs[["year", "avg_student_num"]].rename(columns={"avg_student_num": "actual_adm"})
    chccs = chccs.sort_values("year").reset_index(drop=True)
    return chccs


if __name__ == "__main__":
    history = load_chccs_adm_history()
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(history)} years of CHCCS enrollment history to {OUT_FILE}")
    print(history)
