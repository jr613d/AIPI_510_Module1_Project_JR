"""
Shared constants and one shared helper function, used by all the other
scripts in src/.

This file is deliberately tiny. It holds only things that would otherwise
be copy-pasted into three different scripts -- the folder paths and the
percent-change calculation. Everything else lives in the script that uses
it, so each pipeline stage can be read top to bottom without jumping
between files.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Folder paths
# ---------------------------------------------------------------------------
# __file__ is this file (src/common.py). .parent is src/, .parent.parent is
# the project folder. Building paths this way means the scripts work no
# matter which directory you run them from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_SOURCES = PROJECT_ROOT / "data_sources"   # raw files, exactly as downloaded
DATA_CLEANED = PROJECT_ROOT / "data" / "cleaned"  # tables our scripts produce
FIGURES = PROJECT_ROOT / "figures"             # charts our scripts produce

# ---------------------------------------------------------------------------
# The one district this project is about
# ---------------------------------------------------------------------------
# NC DPI identifies Chapel Hill-Carrboro City Schools as LEA 681. Its
# district-wide rows use the agency_code "681LEA"; its individual schools
# use codes in the 681300-681338 range.
CHCCS = "681LEA"


def pct_change_by_lea(df, value_col, start_year, end_year):
    """Percent change in value_col between two years, one number per district.

    Returns a pandas Series indexed by agency_code. A district missing
    either year comes back as NaN rather than being dropped, so the caller
    can decide what to do about it.

    Assumes df already has exactly one row per (agency_code, year) -- any
    filtering (to district-level rows, to a single subgroup, etc.) needs to
    happen before calling this.
    """
    start_values = df[df["year"] == start_year].set_index("agency_code")[value_col]
    end_values = df[df["year"] == end_year].set_index("agency_code")[value_col]
    return (end_values - start_values) / start_values * 100
