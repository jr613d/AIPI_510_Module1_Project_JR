"""
Assemble the podcast companion page (a simpler, three-chapter view of the same data).

Inlines D3, topojson-client, dashboard_data.json, choice_population_data.json and
podcast_data.json into src/podcast_template.html.

Output: dashboard/nc_enrollment_podcast.html
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "src" / "podcast_template.html"
VENDOR = ROOT / "dashboard" / "vendor"
CLEAN = ROOT / "data" / "cleaned"
OUT = ROOT / "dashboard" / "nc_enrollment_podcast.html"

html = TEMPLATE.read_text()
parts = {
    "<!--__D3__-->": (VENDOR / "d3.v7.min.js").read_text(),
    "<!--__TOPOJSON__-->": (VENDOR / "topojson-client.min.js").read_text(),
    "/*__DATA__*/null": (CLEAN / "dashboard_data.json").read_text(),
    "/*__DATA2__*/null": (CLEAN / "choice_population_data.json").read_text(),
    "/*__PODCAST__*/null": (CLEAN / "podcast_data.json").read_text(),
}
for tag, blob in parts.items():
    assert "</script" not in blob.lower(), tag
    assert html.count(tag) == 1, tag
    html = html.replace(tag, blob, 1)
OUT.write_text(html)
print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1e6:.2f} MB)")
