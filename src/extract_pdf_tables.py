"""
Pulls the tables that only exist in CHCCS's PDFs -- the district's
own forward-looking projections and financial model, and one per-school
enrollment table from the closure study.

Two different extraction methods are used, depending on whether the PDF has machine-readable text or not:

1. TEXT-PARSED tables (district projection, financial impact): these PDFs
   have real, selectable text, so we pull the text and parse it with regex.
   Machine-extracted -- rerun this script and you get the same numbers.

2. MANUALLY-TRANSCRIBED table (per-school elementary ADM grid): the closure
   study's per-school forecast is a *chart image*, not text -- pypdf
   physically cannot read the numbers out of it. Those numbers
   were read directly off the rendered chart image with the help of AI (data_sources -- see
   INDEX.md) and typed in below. Cross-checked against the surrounding
   prose text, which independently states Ephesus goes from 343 to 423
   students and Seawell from 364 to 340 -- both match the transcribed
   table exactly.


"""

import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOARD_DECK = PROJECT_ROOT / "data_sources" / "board_retreat_deck_2025-12-11.pdf"
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"


def _pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def extract_district_projection() -> pd.DataFrame:
    """District-wide 5-year forward ADM projection, text-parsed from the board deck."""
    text = _pdf_text(BOARD_DECK)
    pattern = r"FY (\d{4}) ([\d,]+) \(([\d,]+)\) (-?[\d.]+)%"
    rows = []
    for match in re.finditer(pattern, text):
        year, adm, yoy_change, yoy_pct = match.groups()
        rows.append(
            {
                "fiscal_year": int(year),
                "projected_adm": int(adm.replace(",", "")),
                "yoy_change": -int(yoy_change.replace(",", "")),  # shown as a loss
                "yoy_growth_pct": float(yoy_pct),
            }
        )
    df = pd.DataFrame(rows).drop_duplicates(subset="fiscal_year").sort_values("fiscal_year")
    return df.reset_index(drop=True)


def extract_financial_impact() -> pd.DataFrame:
    """Five-year financial impact table, text-parsed from the board deck.

    Both series here cover FY2027-FY2031 only -- FY2026 is the "Estimated"
    starting baseline in the board deck, with no computed impact figure of
    its own, so it isn't a row in this table.

    Sanity-checked: "Cumulative Impact" is the running sum of "Total Local
    Impact Expected" (536,597 -> 4,305,063 -> 11,743,032 -> 22,751,901 ->
    37,849,147, which matches summing 536,597 + 3,768,466 + 7,437,969 +
    11,008,869 + 15,097,246 exactly) -- confirms the parsed numbers line up
    with the board deck's own arithmetic, not just its formatting.
    """
    text = _pdf_text(BOARD_DECK)
    # PDF line breaks land in slightly different spots on different pages
    # (page 10 breaks after "Loss", page 12 after "ADM") -- normalize
    # whitespace so the label search doesn't depend on exact line breaks.
    normalized = re.sub(r"\s+", " ", text)

    def numbers_after(label: str, count: int):
        idx = normalized.find(label)
        if idx == -1:
            raise ValueError(f"Could not find '{label}' in the board deck text")
        window = normalized[idx : idx + len(label) + 200]
        found = re.findall(r"\(?[\d,]+\)?", window)
        found = [f for f in found if any(ch.isdigit() for ch in f)]
        return [int(f.strip("()").replace(",", "")) * (-1 if f.startswith("(") else 1) for f in found[:count]]

    state_funding_loss = numbers_after("Estimated Reduction in State Funding for ADM Loss at Current Staffing Levels", 5)
    cumulative_impact = numbers_after("Cumulative Impact", 5)

    df = pd.DataFrame(
        {
            "fiscal_year": [2027, 2028, 2029, 2030, 2031],
            "cumulative_local_impact": cumulative_impact,
            "state_funding_loss_from_adm": state_funding_loss,
        }
    )
    return df


def elementary_school_adm_grid() -> pd.DataFrame:
    """All 11 CHCCS elementary schools' projected ADM, 2026-2036.

    MANUALLY TRANSCRIBED -- see the module docstring above. Source: a chart
    image ("ADM: 2025-26 Through 2035-36 by School") on page 13 of the
    closure study, in data_sources/closure_study_2026-05-07.pdf.
    """
    data = {
        "school": [
            "Carrboro Elementary", "Ephesus Elementary", "Estes Hills Elementary",
            "FPG Elementary", "Glenwood Elementary", "McDougle Elementary",
            "Morris Grove Elementary", "Northside Elementary", "Rashkis Elementary",
            "Scroggs Elementary", "Seawell Elementary",
        ],
        2026: [462, 343, 324, 499, 394, 469, 371, 335, 367, 366, 364],
        2027: [444, 375, 353, 491, 387, 487, 364, 316, 336, 347, 354],
        2028: [430, 387, 362, 505, 385, 495, 357, 313, 321, 333, 344],
        2029: [413, 394, 376, 503, 384, 491, 346, 306, 298, 314, 335],
        2030: [409, 405, 375, 499, 396, 510, 362, 298, 283, 311, 343],
        2031: [398, 417, 389, 498, 421, 511, 356, 291, 253, 307, 336],
        2032: [395, 421, 397, 496, 421, 505, 359, 290, 253, 309, 341],
        2033: [395, 420, 398, 495, 420, 501, 362, 289, 253, 312, 344],
        2034: [392, 422, 400, 492, 419, 499, 366, 289, 254, 315, 343],
        2035: [390, 422, 401, 489, 418, 496, 368, 288, 255, 314, 341],
        2036: [388, 423, 403, 487, 418, 495, 371, 289, 256, 314, 340],
    }
    df = pd.DataFrame(data)
    # closure-candidate flag, since Ephesus/Glenwood/Seawell are this study's actual subject
    df["closure_candidate"] = df["school"].isin(["Ephesus Elementary", "Glenwood Elementary", "Seawell Elementary"])
    return df


if __name__ == "__main__":
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)

    projection = extract_district_projection()
    projection.to_csv(CLEANED_DIR / "district_adm_projection.csv", index=False)
    print(f"District projection ({len(projection)} rows):\n{projection}\n")

    financial = extract_financial_impact()
    financial.to_csv(CLEANED_DIR / "financial_impact.csv", index=False)
    print(f"Financial impact ({len(financial)} rows):\n{financial}\n")

    schools = elementary_school_adm_grid()
    schools.to_csv(CLEANED_DIR / "elementary_school_adm.csv", index=False)
    print(f"Elementary school ADM grid ({len(schools)} schools):\n{schools[['school', 2026, 2036, 'closure_candidate']]}\n")
