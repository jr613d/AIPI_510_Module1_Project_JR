"""
Headless-browser smoke test for the built dashboard.

Makes a temporary copy of dashboard/nc_enrollment_dashboard.html with a script
appended that drives every control on every tab (levels, metrics/measures, views,
base years, sort orders, table view, play/stop, a few map clicks) and reports any
JavaScript exception. Runs Google Chrome headless and fails if an error is logged.

    .venv/bin/python tests/smoke_headless.py
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "dashboard" / "nc_enrollment_dashboard.html"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

DRIVER = r"""
<script>
(function () {
  const errors = [];
  window.addEventListener('error', e => errors.push('window.error: ' + e.message + ' @ ' + (e.error && e.error.stack ? e.error.stack.split('\n').slice(0, 7).map(l => l.replace(/file:\S*smoke.html/, '')).join(' <- ') : e.lineno)));
  function setSelect(sel, v) { sel.value = v; sel.dispatchEvent(new Event('change', { bubbles: true })); }
  function step(name, fn) { try { fn(); } catch (e) { errors.push(name + ': ' + (e && e.stack || e)); } }
  let count = 0;
  // ---- tab 1
  step('tab1 metrics', () => {
    for (const lv of ['lea', 'county']) {
      document.querySelector('#levelSeg button[data-v="' + lv + '"]').click();
      const ms = document.getElementById('metricSel');
      for (const o of ms.options) { if (o.disabled) continue; setSelect(ms, o.value); for (const b of [2006, 2015, 2019, 2024]) { setSelect(document.getElementById('baseSel'), b); count++; } }
      for (const so of document.getElementById('sortSel').options) setSelect(document.getElementById('sortSel'), so.value);
      document.getElementById('tableDetails').open = true; document.getElementById('tableDetails').dispatchEvent(new Event('toggle'));
      document.querySelector('#mapMain path.unit').dispatchEvent(new MouseEvent('click', { bubbles: true }));
      const r = document.getElementById('yearRange'); r.value = 3; r.dispatchEvent(new Event('input'));
      document.getElementById('playBtn').click(); document.getElementById('playBtn').click();
    }
  });
  // ---- tabs 2 and 3
  for (const tab of ['tab0', 'tab2', 'tab3']) {
    step(tab + ' open', () => document.querySelector('.tabbar button[data-tab="' + tab + '"]').click());
    const root = document.getElementById(tab), q = s => root.querySelector('[data-role="' + s + '"]');
    step(tab + ' controls', () => {
      const levelBtns = root.querySelectorAll('.controls .seg button');
      const levels = levelBtns.length ? Array.from(levelBtns) : [null];
      for (const lb of levels) {
        if (lb) lb.click();
        for (const mo of q('measure').options) {
          setSelect(q('measure'), mo.value);
          for (const vo of q('view').options) {
            setSelect(q('view'), vo.value);
            for (const b of [2008, 2015, 2019]) { if (!q('base').disabled) setSelect(q('base'), b); count++; }
            const r = q('range'); if (!r.disabled) { r.value = 4; r.dispatchEvent(new Event('input')); r.value = r.max; r.dispatchEvent(new Event('input')); }
          }
        }
        for (const so of q('sort').options) setSelect(q('sort'), so.value);
        q('tableDetails').open = true; q('tableDetails').dispatchEvent(new Event('toggle'));
        q('mapMain').querySelector('path.unit').dispatchEvent(new MouseEvent('click', { bubbles: true }));
        q('play').click(); q('play').click();
      }
    });
  }
  step('theme', () => { document.getElementById('themeBtn').click(); document.getElementById('themeBtn').click(); });
  console.log('SMOKE_DONE combos=' + count + ' errors=' + errors.length);
  for (const e of errors) console.log('SMOKE_ERROR ' + e.replace(/\n/g, ' | '));
})();
</script>
"""

html = HTML.read_text()
assert "</body>" in html
with tempfile.TemporaryDirectory() as tmp:
    test_html = Path(tmp) / "smoke.html"
    test_html.write_text(html.replace("</body>", DRIVER + "</body>", 1))
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--enable-logging=stderr", "--v=0",
           "--virtual-time-budget=20000", "--window-size=1360,2000", "--screenshot=" + str(Path(tmp) / "shot.png"),
           "file://" + str(test_html)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=180).stderr

console = [re.sub(r'^.*?CONSOLE\S*\s*', '', line) for line in out.splitlines() if "CONSOLE" in line]
uncaught = [line for line in console if "Uncaught" in line or "SMOKE_ERROR" in line]
done = [line for line in console if "SMOKE_DONE" in line]
for line in console:
    if "SMOKE" in line or "Uncaught" in line or "Error" in line:
        print(line[:400])
if not done:
    print("smoke driver did not finish"); sys.exit(1)
if uncaught:
    print(f"{len(uncaught)} error(s)"); sys.exit(1)
print("smoke test passed")

# ---- podcast companion and school-options page: load each and fail on any JavaScript error
for POD in (ROOT / "dashboard" / "nc_enrollment_podcast.html", ROOT / "dashboard" / "nc_school_options.html"):
    if not POD.exists():
        continue
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--enable-logging=stderr", "--v=0", "--virtual-time-budget=8000", "--window-size=1300,2000", "file://" + str(POD)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=180).stderr
    errs = [l for l in out.splitlines() if "CONSOLE" in l and ("Uncaught" in l or "Error" in l)]
    for l in errs:
        print(l[:300])
    if errs:
        print(POD.name + " has errors"); sys.exit(1)
    print(POD.name + " loads clean")
