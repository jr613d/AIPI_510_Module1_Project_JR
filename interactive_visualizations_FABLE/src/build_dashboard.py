"""
Assemble the single-file dashboard.

Reads src/dashboard_template.html and inlines three things so the result runs
offline by double-clicking it:
  - dashboard/vendor/d3.v7.min.js            (D3 v7, from cdn.jsdelivr.net)
  - dashboard/vendor/topojson-client.min.js  (topojson-client v3)
  - data/cleaned/dashboard_data.json         (built by build_dashboard_data.py)
  - data/cleaned/choice_population_data.json (built by build_choice_population_data.py)
  - src/dashboard_pages23.html / .js         (tabs 2 and 3 markup and engine)

Output: dashboard/nc_enrollment_dashboard.html
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "src" / "dashboard_template.html"
VENDOR = ROOT / "dashboard" / "vendor"
DATA = ROOT / "data" / "cleaned" / "dashboard_data.json"
DATA2 = ROOT / "data" / "cleaned" / "choice_population_data.json"
TABS_HTML = ROOT / "src" / "dashboard_pages23.html"
TABS_JS = ROOT / "src" / "dashboard_pages23.js"
OUT = ROOT / "dashboard" / "nc_enrollment_dashboard.html"

html = TEMPLATE.read_text()
d3 = (VENDOR / "d3.v7.min.js").read_text()
topo = (VENDOR / "topojson-client.min.js").read_text()
data = DATA.read_text()
data2 = DATA2.read_text()
tabs_html = TABS_HTML.read_text()
tabs_js = TABS_JS.read_text()

# A "</script>" inside inlined JSON or JS would end the script block early.
for name, blob in (("d3", d3), ("topojson", topo), ("data", data), ("data2", data2), ("tabs_js", tabs_js)):
    assert "</script" not in blob.lower(), f"{name} contains a script end tag"

html = html.replace("<!--__D3__-->", d3, 1)
html = html.replace("<!--__TOPOJSON__-->", topo, 1)
html = html.replace("/*__DATA__*/null", data, 1)
html = html.replace("/*__DATA2__*/null", data2, 1)
html = html.replace("<!--__TABS_HTML__-->", tabs_html, 1)
html = html.replace("<!--__TABS_JS__-->", tabs_js, 1)
for tag in ("__D3__", "__TOPOJSON__", "__DATA__", "__DATA2__", "__TABS_HTML__", "__TABS_JS__"):
    assert tag not in html, tag

OUT.write_text(html)
print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1e6:.2f} MB)")
