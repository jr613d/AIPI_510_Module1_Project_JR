"""
Assemble the standalone school-options page (map and inventory of charter and private
schools within 25 miles of the CHCCS district center).

Inlines D3, topojson-client, dashboard_data.json (boundaries), choice_population_data.json
(home school and voucher figures) and school_options.json into src/school_options_template.html.

Output: dashboard/nc_school_options.html
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "src" / "school_options_template.html"
VENDOR = ROOT / "dashboard" / "vendor"
CLEAN = ROOT / "data" / "cleaned"
OUT = ROOT / "dashboard" / "nc_school_options.html"

html = TEMPLATE.read_text()
parts = {
    "<!--__D3__-->": (VENDOR / "d3.v7.min.js").read_text(),
    "<!--__TOPOJSON__-->": (VENDOR / "topojson-client.min.js").read_text(),
    "/*__DATA__*/null": (CLEAN / "dashboard_data.json").read_text(),
    "/*__DATA2__*/null": (CLEAN / "choice_population_data.json").read_text(),
    "/*__OPTIONS__*/null": (CLEAN / "school_options.json").read_text(),
}
for tag, blob in parts.items():
    assert "</script" not in blob.lower(), tag
    assert html.count(tag) == 1, tag
    html = html.replace(tag, blob, 1)
OUT.write_text(html)
print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1e6:.2f} MB)")
