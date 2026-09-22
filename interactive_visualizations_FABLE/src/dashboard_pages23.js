/* Tabs 2 and 3: a generic page engine (map + inset, strip, line chart, cards, heatmap,
   table) driven by a page config, plus page-specific context charts. Tab 1 has its own,
   older code and is not touched by anything here. */
(function () {
  'use strict';
  const D1 = DATA, D2 = DATA2, EVENTS = window.NC_EVENTS;
  const Y1 = D1.years, NY1 = Y1.length;                    // 2006..2025 (ADM + population)
  const TRIANGLE_LEA = ['681LEA', '680LEA', '320LEA', '920LEA', '190LEA'];
  const TRIANGLE_COUNTY = ['37135', '37063', '37183', '37037'];

  // ------------------------------------------------------------------ helpers
  const fmtInt = d3.format(',');
  const signed = (v, d) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d);
  const sy = y => (y - 1) + '-' + String(y).slice(2);
  const cssVar = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const mean = a => a.reduce((s, v) => s + v, 0) / a.length;
  const isNum = v => v !== null && v !== undefined && Number.isFinite(v);
  function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
  function row(k, v) { const r = el('div', 'row'); r.append(el('span', 'k', k), el('span', '', v)); return r; }

  const tt = document.getElementById('tt');
  function showTip(nodes, ev) { tt.replaceChildren(...nodes); tt.style.display = 'block'; moveTip(ev); }
  function moveTip(ev) {
    const pad = 14, w = tt.offsetWidth, h = tt.offsetHeight;
    let x = ev.clientX + pad, y = ev.clientY + pad;
    if (x + w > window.innerWidth - 8) x = ev.clientX - w - pad;
    if (y + h > window.innerHeight - 8) y = ev.clientY - h - pad;
    tt.style.left = x + 'px'; tt.style.top = y + 'px';
  }
  const hideTip = () => { tt.style.display = 'none'; };
  const hoverable = (sel, tipFn) => sel.on('pointerenter', (ev, d) => showTip(tipFn(d), ev)).on('pointermove', moveTip).on('pointerleave', hideTip);

  // ------------------------------------------------------------------ geography (shared)
  const topo = D1.topology;
  const allFeatures = topojson.feature(topo, topo.objects.data).features;
  for (const f of allFeatures) {
    const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
    for (const poly of polys) poly.forEach((ring, i) => { const a = d3.geoArea({ type: 'Polygon', coordinates: [ring] }); if ((a > 2 * Math.PI) !== (i > 0)) ring.reverse(); });
  }
  const FEAT = { lea: allFeatures.filter(f => f.properties.layer === 'lea'), county: allFeatures.filter(f => f.properties.layer === 'county') };
  const featById = new Map(allFeatures.map(f => [f.properties.layer + ':' + f.properties.id, f]));
  const countyGeomObj = { type: 'GeometryCollection', geometries: topo.objects.data.geometries.filter(g => g.properties.layer === 'county') };
  const stateOutline = topojson.mesh(topo, countyGeomObj, (a, b) => a === b);
  const countyMesh = topojson.mesh(topo, countyGeomObj, (a, b) => a !== b);
  const MAIN_W = 800, MAIN_H = 400, INSET_W = 400, INSET_H = 400;
  const newProj = () => d3.geoAlbers().rotate([79.6, 0]).center([0, 35.5]).parallels([34.4, 36.3]);
  const projMain = newProj().fitExtent([[6, 6], [MAIN_W - 6, MAIN_H - 6]], { type: 'FeatureCollection', features: FEAT.county });
  const pathMain = d3.geoPath(projMain);

  // ------------------------------------------------------------------ shared series
  const nameOf = (level, id) => level === 'lea' ? D1.leas[id].name : D1.counties[id].name + ' County';
  const SHORT = { '681LEA': 'CHCCS', '340LEA': 'WS/Forsyth', '250LEA': 'Craven', '760LEA': 'Randolph', '780LEA': 'Robeson', '491LEA': 'Mooresville', '700LEA': 'Eliz. City-Pasquotank', '640LEA': 'Nash', '600LEA': 'Charlotte-Meck.', '010LEA': 'Alamance-Burlington', '490LEA': 'Iredell-Statesville', '800LEA': 'Rowan-Salisbury', '210LEA': 'Edenton-Chowan' };
  function shortName(level, id) {
    if (level === 'county') return D1.counties[id].name + ' Co.';
    if (SHORT[id]) return SHORT[id];
    return D1.leas[id].name.replace(' County Public Schools', '').replace(' County Schools', '').replace(' Public Schools', '').replace(' City Schools', ' City').replace(' Schools', '');
  }
  const admCounty = id => D1.counties[id].lea.map((v, i) => v + D1.counties[id].charter[i]);
  const admOf = (level, id) => level === 'lea' ? D1.leas[id].adm : admCounty(id);
  const popOf = (level, id) => level === 'lea' ? D2.population.leas[id].age517 : D2.population.counties[id].age517;
  const totPopOf = (level, id) => level === 'lea' ? D2.population.leas[id].total : D2.population.counties[id].total;
  const stateAdm = D1.state.lea.map((v, i) => v + D1.state.charter[i]);
  const statePop = Y1.map((y, i) => Object.values(D2.population.counties).every(c => isNum(c.age517[i])) ? d3.sum(Object.values(D2.population.counties), c => c.age517[i]) : null);
  const lastPop = (() => { for (let i = NY1 - 1; i >= 0; i--) if (isNum(statePop[i])) return i; return NY1 - 1; })();   // latest year with a population estimate
  const np = D2.nonpublic, NPY = D2.npYears;
  const at1 = (arr, y) => { const i = Y1.indexOf(y); return i < 0 ? null : arr[i]; };   // value of an ADM-year array at year y
  const npState = {
    private: D2.nonpublicState.private.map((v, i) => v ?? D2.nonpublicState.privateCountySum[i]),
    home: D2.nonpublicState.home.map((v, i) => v ?? D2.nonpublicState.homeCountySum[i]),
  };

  // ------------------------------------------------------------------ page engine
  function createPage(cfg) {
    const root = cfg.root, q = s => root.querySelector('[data-role="' + s + '"]');
    const YEARS = cfg.years, NY = YEARS.length;
    const st = { level: cfg.defaultLevel, measure: cfg.defaultMeasure, view: cfg.defaultView, base: cfg.defaultBase, yi: cfg.defaultYear ? YEARS.indexOf(cfg.defaultYear) : NY - 1, lineMode: 'index', sort: 'latest',
      selected: {}, slots: {}, playing: false, timer: null };
    for (const lv of cfg.levels) { st.selected[lv.id] = [cfg.anchor[lv.id]]; st.slots[lv.id] = new Map([[cfg.anchor[lv.id], 1]]); }
    const M = () => cfg.measures.find(m => m.id === st.measure);
    const ids = () => st.level === 'lea' ? Object.keys(D1.leas) : Object.keys(D1.counties);
    const focus = () => cfg.focus[st.level], anchor = () => cfg.anchor[st.level];
    const sel = () => st.selected[st.level], slotOf = id => st.slots[st.level].get(id), slotColor = s => cssVar('--s' + s), isSel = id => sel().includes(id);
    const name = id => nameOf(st.level, id), sname = id => shortName(st.level, id);
    const yr = () => YEARS[st.yi];
    function toggleSelect(id) {
      const s = st.selected[st.level], m = st.slots[st.level];
      if (s.includes(id)) { if (s.length === 1) return; s.splice(s.indexOf(id), 1); m.delete(id); }
      else { if (s.length >= 8) return; const used = new Set(m.values()); let k = 1; while (used.has(k)) k++; s.push(id); m.set(id, k); }
      renderAll();
    }

    // ---- views available for a measure
    const VIEWS = {
      level: { label: 'Level', kind: 'seq' },
      yoy: { label: '1-year change (%)', kind: 'div', pct: true },
      avg3: { label: '3-year avg. annual change (%)', kind: 'div', pct: true },
      cum: { label: 'Cumulative change since base (%)', kind: 'div', pct: true },
      peak: { label: 'Below own peak (%)', kind: 'negseq', pct: true },
      cumpts: { label: 'Change since base (points)', kind: 'div', pts: true },
    };
    function viewsFor(m) {
      if (m.single || m.usesBase) return ['level'];
      if (m.kind === 'count') return ['level', 'yoy', 'avg3', 'cum', 'peak'];
      if (m.kind === 'share') return ['level', 'cumpts'];
      return ['level'];
    }
    // ---- raw measure series aligned to YEARS
    const rawCache = new Map();
    function raw(id) { const k = st.level + ':' + st.measure + ':' + (M().usesBase ? st.base + ':' : '') + id; if (!rawCache.has(k)) rawCache.set(k, M().series(st.level, id)); return rawCache.get(k); }
    function metricSeries(id) {
      const s = raw(id), bi = YEARS.indexOf(st.base), out = new Array(NY).fill(null), v = st.view;
      if (v === 'level') return s.map(x => isNum(x) ? x : null);
      if (v === 'yoy') { for (let i = 1; i < NY; i++) out[i] = isNum(s[i]) && isNum(s[i - 1]) && s[i - 1] > 0 ? (s[i] / s[i - 1] - 1) * 100 : null; }
      else if (v === 'avg3') { const y = []; for (let i = 1; i < NY; i++) y[i] = isNum(s[i]) && isNum(s[i - 1]) && s[i - 1] > 0 ? (s[i] / s[i - 1] - 1) * 100 : null; for (let i = 3; i < NY; i++) out[i] = [y[i - 2], y[i - 1], y[i]].every(isNum) ? mean([y[i - 2], y[i - 1], y[i]]) : null; }
      else if (v === 'cum') { for (let i = bi; i < NY; i++) out[i] = isNum(s[i]) && isNum(s[bi]) && s[bi] > 0 ? (s[i] / s[bi] - 1) * 100 : null; }
      else if (v === 'peak') { let mx = 0; for (let i = 0; i < NY; i++) { if (!isNum(s[i])) continue; mx = Math.max(mx, s[i]); out[i] = mx > 0 ? (s[i] / mx - 1) * 100 : null; } }
      else if (v === 'cumpts') { for (let i = bi; i < NY; i++) out[i] = isNum(s[i]) && isNum(s[bi]) ? s[i] - s[bi] : null; }
      return out;
    }
    let cache = new Map();
    function recompute() { cache = new Map(); for (const id of ids()) cache.set(id, metricSeries(id)); }
    const valueAt = (id, i = st.yi) => cache.get(id)[i];
    function fmtVal(v) {
      if (!isNum(v)) return 'n/a';
      const m = M(), vw = VIEWS[st.view];
      if (vw.pct) return signed(v, 1) + '%';
      if (vw.pts || (st.view === 'level' && m.signed)) return signed(v, 1) + ' ' + m.unit;
      if (m.kind === 'cat') return m.classes[v].label;
      if (m.kind === 'share') return v.toFixed(1) + (m.unit === '%' ? '%' : '');
      return fmtInt(Math.round(v));
    }
    function metricLabel() { const m = M(), vw = VIEWS[st.view]; return st.view === 'level' ? m.label : m.label + ' · ' + vw.label.replace(' (%)', '').replace(' (points)', '') + ((st.view === 'cum' || st.view === 'cumpts') ? ' ' + sy(st.base) : ''); }

    // ---- colour
    let color = null, domain = null;
    function niceSpan(x) { if (!isNum(x) || x <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(x))); const m = x / p; const n = m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10; return n * p; }
    function buildColor() {
      const m = M(), vw = VIEWS[st.view], neutral = cssVar('--neutral');
      const all = []; for (const s of cache.values()) for (const v of s) if (isNum(v)) all.push(v);
      if (m.kind === 'cat') { color = v => isNum(v) ? m.classes[v].color() : 'url(#hatch)'; domain = null; return; }
      if (vw.kind === 'div' || (st.view === 'level' && m.signed)) {
        const span = niceSpan(d3.quantile(all.map(Math.abs).sort(d3.ascending), 0.9) || 1);
        const left = d3.piecewise(d3.interpolateLab, [cssVar('--neg-deep'), cssVar('--neg'), neutral]), right = d3.piecewise(d3.interpolateLab, [neutral, cssVar('--pos'), cssVar('--pos-deep')]);
        domain = [-span, span]; color = d3.scaleDiverging(t => t < 0.5 ? left(t * 2) : right((t - 0.5) * 2)).domain([-span, 0, span]).clamp(true);
      } else if (vw.kind === 'negseq') {
        const span = niceSpan(d3.quantile(all.map(Math.abs).sort(d3.ascending), 0.9) || 1);
        domain = [-span, 0]; color = d3.scaleSequential(d3.piecewise(d3.interpolateLab, [cssVar('--neg-deep'), cssVar('--neg'), neutral])).domain([-span, 0]).clamp(true);
      } else {
        const hi = niceSpan(d3.quantile(all.sort(d3.ascending), 0.95) || 1);
        const ramp = m.hue === 'orange' ? [cssVar('--seq2-lo'), cssVar('--s2'), cssVar('--seq2-hi')] : [cssVar('--seq-lo'), cssVar('--pos'), cssVar('--seq-hi')];
        domain = [0, hi]; color = d3.scaleSequential(d3.piecewise(d3.interpolateLab, ramp)).domain([0, hi]).clamp(true);
      }
    }
    const fill = v => isNum(v) ? color(v) : 'url(#hatch)';

    // ---- tooltip for a unit
    function unitTip(id) {
      const m = M(), s = raw(id), v = valueAt(id), nodes = [];
      nodes.push(el('div', 't', name(id) + (st.level === 'lea' ? ' · ' + D1.leas[id].county + ' Co.' : '')));
      nodes.push(el('div', 'big' + (!isNum(v) || m.kind === 'cat' ? '' : v < 0 ? ' neg' : v > 0 ? ' pos' : ''), fmtVal(v)));
      nodes.push(el('div', 'k', metricLabel() + ', ' + sy(yr())));
      if (m.kind !== 'cat' && st.view !== 'level') nodes.push(row(m.label + ' ' + sy(yr()), isNum(s[st.yi]) ? (m.kind === 'share' ? s[st.yi].toFixed(1) + (m.unit === '%' ? '%' : '') : fmtInt(Math.round(s[st.yi]))) : 'n/a'));
      for (const r of (m.tipRows ? m.tipRows(st.level, id, st.yi) : [])) nodes.push(row(r[0], r[1]));
      if (m.kind !== 'cat') nodes.push(spark(s, 250, 44, st.yi));
      nodes.push(el('div', 'sub', 'Click to ' + (isSel(id) ? 'remove from' : 'add to') + ' the comparison'));
      return nodes;
    }
    function spark(s, w, h, hi) {
      const svg = d3.create('svg').attr('width', w).attr('height', h).attr('viewBox', [0, 0, w, h]);
      const vals = s.map((v, i) => [i, v]).filter(d => isNum(d[1]));
      if (!vals.length) return svg.node();
      const x = d3.scaleLinear().domain([0, NY - 1]).range([2, w - 2]), y = d3.scaleLinear().domain([d3.min(vals, d => d[1]) * 0.98, d3.max(vals, d => d[1]) * 1.02 || 1]).range([h - 3, 3]);
      svg.append('path').attr('d', d3.line().x(d => x(d[0])).y(d => y(d[1]))(vals)).attr('fill', 'none').attr('stroke', cssVar('--ink-2')).attr('stroke-width', 1.5);
      if (isNum(s[hi])) svg.append('circle').attr('cx', x(hi)).attr('cy', y(s[hi])).attr('r', 3.5).attr('fill', cssVar('--ink'));
      return svg.node();
    }

    // ---- controls
    function buildControls() {
      const host = q('controls'); host.replaceChildren();
      const r1 = el('div', 'ctl-row');
      if (cfg.levels.length > 1) {
        const c = el('div', 'ctl'); c.append(el('span', 'lbl', 'Level'));
        const seg = el('div', 'seg'); seg.setAttribute('role', 'group');
        for (const lv of cfg.levels) { const b = el('button', '', lv.label); b.type = 'button'; b.dataset.v = lv.id; b.setAttribute('aria-pressed', String(lv.id === st.level)); b.onclick = () => { st.level = lv.id; seg.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', String(x === b))); syncOptions(); renderAll(); }; seg.append(b); }
        c.append(seg); r1.append(c);
      }
      const cm = el('div', 'ctl'); const lm = el('label', '', 'Measure'); const ms = el('select'); ms.dataset.role = 'measure';
      ms.onchange = () => { st.measure = ms.value; syncOptions(); renderAll(); }; cm.append(lm, ms); r1.append(cm);
      const cv = el('div', 'ctl'); cv.append(el('label', '', 'View')); const vs = el('select'); vs.dataset.role = 'view'; vs.onchange = () => { st.view = vs.value; syncOptions(); renderAll(); }; cv.append(vs); r1.append(cv);
      const cb = el('div', 'ctl'); cb.dataset.role = 'baseCtl'; cb.append(el('label', '', 'Base year')); const bs = el('select'); bs.dataset.role = 'base';
      YEARS.slice(0, NY - 1).forEach(y => { const o = el('option', '', sy(y)); o.value = y; bs.append(o); }); bs.value = st.base;
      bs.onchange = () => { st.base = +bs.value; if (st.yi < YEARS.indexOf(st.base)) st.yi = NY - 1; renderAll(); }; cb.append(bs); r1.append(cb);
      host.append(r1);
      const tr = el('div', 'time-row');
      const play = el('button', 'play'); play.type = 'button'; play.innerHTML = '&#9654;'; play.setAttribute('aria-label', 'Play timeline'); play.dataset.role = 'play';
      play.onclick = () => st.playing ? stopPlay() : startPlay();
      const sw = el('div', 'slider-wrap'); const range = document.createElement('input'); range.type = 'range'; range.min = 0; range.max = NY - 1; range.step = 1; range.value = st.yi; range.dataset.role = 'range'; range.setAttribute('aria-label', 'School year');
      range.oninput = () => { stopPlay(); setYear(+range.value); };
      const ticks = el('div', 'ev-ticks');
      for (const e of EVENTS) { const t = (e.x - YEARS[0]) / (YEARS[NY - 1] - YEARS[0]); if (t < 0 || t > 1.03) continue; const tick = el('div', 'ev-tick'); tick.style.left = (Math.min(t, 1) * 100) + '%'; tick.append(el('i'), el('span', 'ev-badge' + (e.beyond ? ' beyond' : ''), String(e.n))); tick.addEventListener('pointerenter', ev => showTip([el('div', 't', e.n + '. ' + e.label + ' · ' + e.when), el('div', '', e.detail)], ev)); tick.addEventListener('pointermove', moveTip); tick.addEventListener('pointerleave', hideTip); ticks.append(tick); }
      sw.append(range, ticks);
      const yb = el('div', 'year-big'); yb.dataset.role = 'yearBig';
      tr.append(play, sw, yb); host.append(tr);
      syncOptions();
    }
    function syncOptions() {
      const ms = q('measure'), allowed = cfg.measures.filter(x => !x.levels || x.levels.includes(st.level));
      if (!allowed.some(x => x.id === st.measure)) st.measure = allowed[0].id;
      ms.replaceChildren(); for (const x of allowed) { const o = el('option', '', x.label); o.value = x.id; ms.append(o); } ms.value = st.measure;
      const m = M(), vs = q('view'), avail = viewsFor(m);
      if (!avail.includes(st.view)) st.view = avail.includes(cfg.defaultView) ? cfg.defaultView : avail[0];
      vs.replaceChildren(); for (const v of avail) { const o = el('option', '', VIEWS[v].label); o.value = v; vs.append(o); } vs.value = st.view; vs.disabled = avail.length === 1;
      const needsBase = st.view === 'cum' || st.view === 'cumpts' || m.usesBase;
      q('baseCtl').style.opacity = needsBase ? 1 : 0.45; q('base').disabled = !needsBase;
      if (m.single) { st.yi = YEARS.indexOf(m.single); }
      q('range').disabled = !!m.single; q('play').disabled = !!m.single;
      if (m.single) stopPlay();
    }
    function startPlay() {
      st.playing = true; q('play').innerHTML = '&#10074;&#10074;';
      const startAt = (st.view === 'cum' || st.view === 'cumpts' || M().usesBase) ? YEARS.indexOf(st.base) : (st.view === 'avg3' ? 3 : st.view === 'yoy' ? 1 : 0);
      if (st.yi >= NY - 1) setYear(startAt);
      st.timer = setInterval(() => { if (st.yi >= NY - 1) { stopPlay(); return; } setYear(st.yi + 1); }, 900);
    }
    function stopPlay() { if (!st.playing) return; st.playing = false; clearInterval(st.timer); q('play').innerHTML = '&#9654;'; }
    function setYear(i) { st.yi = Math.max(0, Math.min(NY - 1, i)); renderYear(); }

    // ---- maps
    let projInset = null, pathInset = null;
    function buildMap(svgSel, path, W, H, clip) {
      svgSel.selectAll('*').remove();
      const cid = 'clip-' + cfg.key + '-' + (clip ? 'inset' : 'main');
      if (clip) svgSel.append('clipPath').attr('id', cid).append('rect').attr('width', W).attr('height', H).attr('rx', 8);
      const g = svgSel.append('g').attr('clip-path', clip ? 'url(#' + cid + ')' : null);
      if (clip) g.append('rect').attr('class', 'frame').attr('width', W).attr('height', H).attr('rx', 8);
      const units = g.append('g').selectAll('path').data(FEAT[st.level], f => f.properties.id).join('path').attr('class', 'unit').attr('d', path)
        .attr('fill', f => fill(valueAt(f.properties.id))).classed('selected', f => isSel(f.properties.id)).on('click', (ev, f) => toggleSelect(f.properties.id));
      hoverable(units, f => unitTip(f.properties.id));
      if (st.level === 'lea') g.append('path').attr('class', 'mesh').attr('d', path(countyMesh)).style('stroke', cssVar('--axis')).style('stroke-width', 0.5).style('opacity', 0.6);
      g.append('path').attr('class', 'outline').attr('d', path(stateOutline));
      g.append('path').attr('class', 'focus-ring').attr('d', path({ type: 'FeatureCollection', features: focus().map(id => featById.get(st.level + ':' + id)) }));
      if (clip) g.append('g').selectAll('text').data(focus().map(id => featById.get(st.level + ':' + id))).join('text').attr('class', 'lbl').attr('transform', f => 'translate(' + path.centroid(f) + ')').attr('text-anchor', 'middle')
        .each(function (f) { const nm = name(f.properties.id).replace(' City Schools', '').replace(' Public Schools', '').replace(' County Schools', ' County').replace(' Schools', ''); const parts = nm.split(' '); const lines = parts.length > 2 ? [parts.slice(0, -1).join(' '), parts[parts.length - 1]] : [nm]; d3.select(this).selectAll('tspan').data(lines).join('tspan').attr('x', 0).attr('dy', (d, i) => i === 0 ? (lines.length > 1 ? '-0.2em' : '0.35em') : '1.1em').text(d => d); });
    }
    function renderMaps() {
      projInset = newProj(); projInset.fitExtent([[14, 14], [INSET_W - 14, INSET_H - 14]], { type: 'FeatureCollection', features: focus().map(id => featById.get(st.level + ':' + id)) }); pathInset = d3.geoPath(projInset);
      buildMap(d3.select(q('mapMain')), pathMain, MAIN_W, MAIN_H, false);
      buildMap(d3.select(q('mapInset')), pathInset, INSET_W, INSET_H, true);
      q('mapTitle').textContent = 'Statewide · ' + (st.level === 'lea' ? '115 districts' : '100 counties') + ' · ' + sy(yr());
      const ih = q('insetHint'); if (ih) ih.textContent = (st.level === 'lea' ? 'Chapel Hill-Carrboro, Orange, Durham, Wake and Chatham' : 'Orange, Durham, Wake and Chatham counties') + ', same colors as the state map.';
    }
    function updateMapFills() { d3.select(root).selectAll('.map-svg path.unit').attr('fill', f => fill(valueAt(f.properties.id))).classed('selected', f => isSel(f.properties.id)); }
    function renderLegend() {
      const host = q('legend'), m = M(); host.replaceChildren();
      host.append(el('span', '', metricLabel() + (m.kind === 'cat' ? '' : ' (' + (VIEWS[st.view].pct ? '%' : VIEWS[st.view].pts ? 'pts' : m.unit) + ')')));
      if (m.kind === 'cat') {
        for (const c of m.classes) { const s = el('span'); const sw = el('span', 'swatch'); sw.style.background = c.color(); s.append(sw, document.createTextNode(c.label)); host.append(s); }
      } else {
        const stops = d3.range(0, 1.0001, 0.1).map(t => color(domain[0] + t * (domain[1] - domain[0])));
        const bar = el('div', 'bar'); bar.style.background = 'linear-gradient(90deg,' + stops.join(',') + ')';
        const ticks = el('div', 'bar-ticks'); const f = v => VIEWS[st.view].pct || VIEWS[st.view].pts || m.signed ? signed(v, 0) : fmtInt(Math.round(v));
        ticks.append(el('span', '', (domain[0] < 0 ? '≤ ' : '') + f(domain[0])), el('span', '', f((domain[0] + domain[1]) / 2)), el('span', '', '≥ ' + f(domain[1])));
        const wrap = el('div'); wrap.append(bar, ticks); host.append(wrap);
      }
      const h = el('span'); const sw = el('span', 'swatch'); sw.style.backgroundImage = 'repeating-linear-gradient(45deg, var(--axis) 0 1px, var(--neutral) 1px 5px)'; h.append(sw, document.createTextNode('no value')); host.append(h);
    }

    // ---- strip
    function renderStrip() {
      const svg = d3.select(q('strip')), W = 1200, H = 110; svg.selectAll('*').remove();
      const m = M();
      q('stripTitle').textContent = 'Where does each ' + (st.level === 'lea' ? 'district' : 'county') + ' sit in ' + sy(yr()) + '? · ' + metricLabel();
      if (m.kind === 'cat') { renderCatStrip(svg, W, H); return; }
      const vals = ids().map(id => ({ id, v: valueAt(id) })).filter(d => isNum(d.v));
      if (!vals.length) { svg.append('text').attr('x', 20).attr('y', 50).attr('fill', cssVar('--muted')).text('No values for this year.'); return; }
      const lo = Math.min(domain[0], d3.min(vals, d => d.v)), hi = Math.max(domain[1], d3.max(vals, d => d.v));
      const x = d3.scaleLinear().domain([lo, hi]).nice().range([40, W - 40]);
      const bins = d3.bin().domain(x.domain()).thresholds(90).value(d => d.v)(vals);
      const r = 4.2, baseY = H - 28;
      const tf = v => VIEWS[st.view].pct ? signed(v, 0) + '%' : (VIEWS[st.view].pts || m.signed) ? signed(v, 0) : d3.format('~s')(v);
      svg.append('g').attr('class', 'axis').attr('transform', 'translate(0,' + (baseY + 6) + ')').call(d3.axisBottom(x).ticks(12).tickFormat(tf).tickSize(4));
      const med = d3.median(vals, d => d.v);
      svg.append('line').attr('x1', x(med)).attr('x2', x(med)).attr('y1', 8).attr('y2', baseY + 4).attr('stroke', cssVar('--ink'));
      svg.append('text').attr('x', x(med) + 5).attr('y', 14).attr('font-size', 11).attr('fill', cssVar('--ink-2')).text('median ' + fmtVal(med));
      if (domain[0] < 0 && domain[1] > 0) svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', baseY - 60).attr('y2', baseY + 4).attr('stroke', cssVar('--axis'));
      const dots = []; for (const b of bins) { const cx = x((b.x0 + b.x1) / 2); b.sort((a, c) => a.v - c.v).forEach((d, k) => dots.push({ ...d, cx, cy: baseY - k * (r * 2 + 0.5) })); }
      const g = svg.append('g');
      hoverable(g.selectAll('circle').data(dots.filter(d => !isSel(d.id))).join('circle').attr('cx', d => d.cx).attr('cy', d => d.cy).attr('r', r).attr('fill', d => color(d.v)).attr('stroke', cssVar('--surface')).style('cursor', 'pointer').on('click', (ev, d) => toggleSelect(d.id)), d => unitTip(d.id));
      const s = dots.filter(d => isSel(d.id));
      hoverable(g.selectAll('circle.sel').data(s).join('circle').attr('class', 'sel').attr('cx', d => d.cx).attr('cy', d => d.cy).attr('r', r + 1.5).attr('fill', d => slotColor(slotOf(d.id))).attr('stroke', cssVar('--ink')).attr('stroke-width', 1.5).style('cursor', 'pointer').on('click', (ev, d) => toggleSelect(d.id)), d => unitTip(d.id));
      const labs = s.map(d => ({ ...d, lx: d.cx })).sort((a, b) => a.cx - b.cx);
      for (let i = 1; i < labs.length; i++) if (labs[i].lx - labs[i - 1].lx < 112) labs[i].lx = labs[i - 1].lx + 112;
      if (labs.length) { const shift = d3.mean(labs, d => d.cx) - d3.mean(labs, d => d.lx); const cs = Math.max(50 - labs[0].lx, Math.min(W - 50 - labs[labs.length - 1].lx, shift)); labs.forEach(d => { d.lx += cs; }); }
      g.selectAll('text.sl').data(labs).join('text').attr('x', d => d.lx).attr('y', 30).attr('font-size', 11).attr('font-weight', 600).attr('text-anchor', 'middle').attr('fill', cssVar('--ink')).text(d => sname(d.id) + ' ' + fmtVal(d.v));
      g.selectAll('line.sl').data(labs).join('line').attr('x1', d => d.lx).attr('x2', d => d.cx).attr('y1', 34).attr('y2', d => d.cy - r - 2).attr('stroke', cssVar('--muted'));
      const rank = vals.slice().sort((a, b) => a.v - b.v).findIndex(d => d.id === anchor());
      if (rank >= 0) svg.append('text').attr('x', W - 40).attr('y', 14).attr('text-anchor', 'end').attr('font-size', 11).attr('fill', cssVar('--ink-2')).text(sname(anchor()) + ' ranks ' + (rank + 1) + ' of ' + vals.length + ' (1 = lowest)');
    }
    function renderCatStrip(svg, W, H) {
      const m = M(), groups = m.classes.map((c, k) => ({ k, c, ids: ids().filter(id => valueAt(id) === k) }));
      const x = d3.scaleBand().domain(groups.map(g => g.k)).range([40, W - 40]).paddingInner(0.15);
      const g = svg.append('g');
      for (const grp of groups) {
        g.append('text').attr('x', x(grp.k)).attr('y', 20).attr('font-size', 12).attr('font-weight', 600).attr('fill', cssVar('--ink')).text(grp.c.label + ' · ' + grp.ids.length);
        const per = Math.floor(x.bandwidth() / 11), r = 4.2;
        const dots = grp.ids.map((id, i) => ({ id, cx: x(grp.k) + (i % per) * 11 + 5, cy: 34 + Math.floor(i / per) * 11 }));
        hoverable(g.selectAll('circle.g' + grp.k).data(dots).join('circle').attr('cx', d => d.cx).attr('cy', d => d.cy).attr('r', d => isSel(d.id) ? r + 1.5 : r).attr('fill', d => isSel(d.id) ? slotColor(slotOf(d.id)) : grp.c.color()).attr('stroke', d => isSel(d.id) ? cssVar('--ink') : cssVar('--surface')).style('cursor', 'pointer').on('click', (ev, d) => toggleSelect(d.id)), d => unitTip(d.id));
      }
    }

    // ---- event badges
    function drawEvents(g, x, top, bottom) {
      for (const e of EVENTS) { const xx = x(e.x); if (xx < x.range()[0] - 1 || xx > x.range()[1] + 1) continue; g.append('line').attr('class', 'ev-line' + (e.beyond ? ' beyond' : '')).attr('x1', xx).attr('x2', xx).attr('y1', top + 10).attr('y2', bottom); const b = g.append('g').attr('class', 'ev-badge-g' + (e.beyond ? ' beyond' : '')).attr('transform', 'translate(' + xx + ',' + top + ')').style('cursor', 'help'); b.append('circle').attr('r', 8); b.append('text').text(e.n); hoverable(b, () => [el('div', 't', e.n + '. ' + e.label + ' · ' + e.when), el('div', '', e.detail)]); }
    }

    // ---- line chart (generic: measure series per selected unit; or two-series pop vs adm)
    function renderLine() {
      const svg = d3.select(q('lineChart')), W = 760, H = 340; svg.selectAll('*').remove();
      const Mg = { t: 30, r: 150, b: 32, l: 56 }, bi = YEARS.indexOf(st.base), m = M();
      let series = [];
      if (cfg.lineChart === 'popVsAdm') {
        for (const id of sel()) {
          const p = popOf(st.level, id), a = admOf(st.level, id);
          series.push({ id, name: sname(id) + ' kids', color: slotColor(slotOf(id)), vals: p.map(v => isNum(v) && isNum(p[bi]) ? v / p[bi] * 100 : null), rawVals: p });
          series.push({ id, name: sname(id) + ' ADM', color: slotColor(slotOf(id)), dash: true, vals: a.map(v => v / a[bi] * 100), rawVals: a });
        }
      } else {
        const idx = st.lineMode === 'index';
        for (const id of sel()) { const s = raw(id); series.push({ id, name: sname(id), color: slotColor(slotOf(id)), vals: idx ? s.map(v => isNum(v) && isNum(s[bi]) && s[bi] > 0 ? v / s[bi] * 100 : null) : s.map(v => isNum(v) ? v : null), rawVals: s }); }
        if (m.stateSeries) { const s = m.stateSeries(); series.push({ id: 'state', name: 'NC total', ref: true, color: cssVar('--muted'), vals: idx ? s.map(v => isNum(v) && isNum(s[bi]) ? v / s[bi] * 100 : null) : s, rawVals: s }); }
      }
      const idx = cfg.lineChart === 'popVsAdm' || st.lineMode === 'index';
      const x = d3.scaleLinear().domain([YEARS[0], YEARS[NY - 1]]).range([Mg.l, W - Mg.r]);
      const allv = series.flatMap(s => s.vals.filter(isNum));
      if (m.single) { svg.append('text').attr('x', 56).attr('y', 40).attr('font-size', 12).attr('fill', cssVar('--muted')).text('Single-year measure (' + sy(m.single) + ' only): no time series to draw. See the map, strip and table.'); renderChips(); return; }
      if (!allv.length) { renderChips(); return; }
      const y = idx ? d3.scaleLinear().domain([Math.min(d3.min(allv), 100) - 2, Math.max(d3.max(allv), 100) + 2]).nice().range([H - Mg.b, Mg.t]) : d3.scaleLinear().domain([0, d3.max(allv) * 1.05]).nice().range([H - Mg.b, Mg.t]);
      svg.append('g').attr('class', 'axis').attr('transform', 'translate(' + Mg.l + ',0)').call(d3.axisLeft(y).ticks(6).tickFormat(v => idx ? v : d3.format('~s')(v)).tickSize(-(W - Mg.r - Mg.l))).call(g => { g.select('.domain').remove(); g.selectAll('line').attr('class', 'gridline'); });
      svg.append('g').attr('class', 'axis').attr('transform', 'translate(0,' + (H - Mg.b) + ')').call(d3.axisBottom(x).ticks(10).tickFormat(v => sy(v)).tickSize(4));
      if (idx) svg.append('line').attr('x1', Mg.l).attr('x2', W - Mg.r).attr('y1', y(100)).attr('y2', y(100)).attr('stroke', cssVar('--axis'));
      drawEvents(svg, x, Mg.t - 14, H - Mg.b);
      svg.append('line').attr('class', 'cursor-line').attr('x1', x(yr())).attr('x2', x(yr())).attr('y1', Mg.t).attr('y2', H - Mg.b);
      const line = d3.line().x((d, i) => x(YEARS[i])).y(d => y(d)).defined(d => isNum(d));
      const g = svg.append('g');
      for (const s of series) g.append('path').attr('class', 'series-line' + (s.ref ? ' ref' : '')).attr('d', line(s.vals)).attr('stroke', s.color).attr('stroke-dasharray', s.dash ? '5 4' : null);
      const lastIdx = s => { for (let i = NY - 1; i >= 0; i--) if (isNum(s.vals[i])) return i; return -1; };
      const labs = series.map(s => ({ s, li: lastIdx(s) })).filter(d => d.li >= 0).map(d => ({ ...d, y: y(d.s.vals[d.li]) })).sort((a, b) => a.y - b.y);
      for (let i = 1; i < labs.length; i++) if (labs[i].y - labs[i - 1].y < 13) labs[i].y = labs[i - 1].y + 13;
      g.selectAll('circle.end').data(labs).join('circle').attr('class', 'end-dot').attr('cx', d => x(YEARS[d.li])).attr('cy', d => y(d.s.vals[d.li])).attr('r', 3.5).attr('fill', d => d.s.color);
      g.selectAll('text.sl').data(labs).join('text').attr('class', 'series-label').attr('x', d => x(YEARS[d.li]) + 8).attr('y', d => d.y).attr('dy', '0.35em').attr('fill', d => d.s.ref ? cssVar('--muted') : cssVar('--ink')).text(d => d.s.name + ' ' + (idx ? d.s.vals[d.li].toFixed(1) : (m.kind === 'share' ? d.s.vals[d.li].toFixed(1) : fmtInt(Math.round(d.s.vals[d.li])))));
      const hover = svg.append('g').style('display', 'none'); const hl = hover.append('line').attr('stroke', cssVar('--ink')).attr('y1', Mg.t).attr('y2', H - Mg.b).attr('opacity', .5); const hd = hover.append('g');
      svg.append('rect').attr('x', Mg.l).attr('y', Mg.t).attr('width', W - Mg.r - Mg.l).attr('height', H - Mg.b - Mg.t).attr('fill', 'transparent').style('cursor', 'crosshair')
        .on('pointerenter', () => hover.style('display', null)).on('pointerleave', () => { hover.style('display', 'none'); hideTip(); })
        .on('pointermove', function (ev) {
          const [mx] = d3.pointer(ev); const i = YEARS.indexOf(Math.max(YEARS[0], Math.min(YEARS[NY - 1], Math.round(x.invert(mx)))));
          hl.attr('x1', x(YEARS[i])).attr('x2', x(YEARS[i]));
          hd.selectAll('circle').data(series.filter(s => isNum(s.vals[i]))).join('circle').attr('cx', x(YEARS[i])).attr('cy', s => y(s.vals[i])).attr('r', 4).attr('fill', s => s.color).attr('stroke', cssVar('--surface')).attr('stroke-width', 1.5);
          const nodes = [el('div', 't', sy(YEARS[i]))];
          for (const s of series) { const k = el('span', 'k'); const sw = el('i'); sw.style.cssText = 'display:inline-block;width:12px;height:2px;background:' + s.color + ';vertical-align:middle;margin-right:5px;' + (s.dash ? 'border-top:2px dashed ' + s.color + ';background:none;height:0;' : ''); k.append(sw, document.createTextNode(s.name)); const r = el('div', 'row'); r.append(k, el('span', '', !isNum(s.vals[i]) ? 'n/a' : (idx ? s.vals[i].toFixed(1) + ' (' + (isNum(s.rawVals[i]) ? (m.kind === 'share' && cfg.lineChart !== 'popVsAdm' ? s.rawVals[i].toFixed(1) : fmtInt(Math.round(s.rawVals[i]))) : 'n/a') + ')' : (m.kind === 'share' ? s.vals[i].toFixed(1) : fmtInt(Math.round(s.vals[i])))))); nodes.push(r); }
          if (idx) nodes.push(el('div', 'sub', 'Index: ' + sy(st.base) + ' = 100. Raw value in parentheses.'));
          showTip(nodes, ev);
        })
        .on('click', function (ev) { const [mx] = d3.pointer(ev); setYear(YEARS.indexOf(Math.max(YEARS[0], Math.min(YEARS[NY - 1], Math.round(x.invert(mx)))))); });
      svg.append('text').attr('x', Mg.l).attr('y', 14).attr('font-size', 11).attr('fill', cssVar('--muted')).text(idx ? 'Index, ' + sy(st.base) + ' = 100' : m.label);
      const lt = q('lineTitle'); if (lt) lt.textContent = m.label + ' over time';
      renderChips();
    }
    function renderChips() {
      const host = q('chips'); host.replaceChildren();
      for (const id of sel()) { const c = el('span', 'chip'); const i = el('i'); i.style.background = slotColor(slotOf(id)); c.append(i, document.createTextNode(sname(id))); if (sel().length > 1) { const b = el('button', '', '×'); b.setAttribute('aria-label', 'Remove ' + name(id)); b.onclick = () => toggleSelect(id); c.append(b); } host.append(c); }
      if (cfg.lineChart !== 'popVsAdm' && M().stateSeries) { const r = el('span', 'chip ref'); r.append(el('i'), document.createTextNode('NC total (reference)')); host.append(r); }
      if (sel().length < 8) { const h = el('span', '', ' ← click any map unit, dot, card or heatmap row to add one (up to 8)'); h.style.cssText = 'color:var(--muted);font-size:12px;align-self:center'; host.append(h); }
    }

    // ---- cards
    function renderCards() {
      const host = q('cards'); host.replaceChildren();
      q('cardsTitle').textContent = st.level === 'lea' ? 'Triangle focus: five districts' : 'Triangle focus: four counties';
      const bi = YEARS.indexOf(st.base), m = M();
      for (const id of focus()) {
        const card = el('div', 'mini'); card.tabIndex = 0; card.setAttribute('role', 'button');
        if (isSel(id)) { const d = el('span', 'dot'); d.style.background = slotColor(slotOf(id)); card.append(d); }
        card.append(el('div', 'n', name(id)));
        const w = 200, h = 48, svg = d3.create('svg').attr('viewBox', [0, 0, w, h]).attr('preserveAspectRatio', 'none');
        const x = d3.scaleLinear().domain([YEARS[0], YEARS[NY - 1]]).range([3, w - 3]);
        const col = isSel(id) ? slotColor(slotOf(id)) : cssVar('--ink-2');
        for (const e of EVENTS) if (e.x < YEARS[NY - 1]) svg.append('line').attr('x1', x(e.x)).attr('x2', x(e.x)).attr('y1', 4).attr('y2', h - 3).attr('stroke', cssVar('--grid'));
        if (cfg.lineChart === 'popVsAdm') {
          const p = popOf(st.level, id), a = admOf(st.level, id), pi = p.map(v => isNum(v) && isNum(p[bi]) ? v / p[bi] * 100 : null), ai = a.map(v => v / a[bi] * 100);
          const fin = pi.filter(isNum).concat(ai);
          const y = d3.scaleLinear().domain([d3.min(fin) - 1, d3.max(fin) + 1]).range([h - 3, 6]);
          svg.append('line').attr('x1', 3).attr('x2', w - 3).attr('y1', y(100)).attr('y2', y(100)).attr('stroke', cssVar('--axis'));
          svg.append('path').attr('d', d3.line().x((d, i) => x(YEARS[i])).y(d => y(d)).defined(isNum)(pi)).attr('fill', 'none').attr('stroke', col).attr('stroke-width', 1.8);
          svg.append('path').attr('d', d3.line().x((d, i) => x(YEARS[i])).y(d => y(d))(ai)).attr('fill', 'none').attr('stroke', col).attr('stroke-width', 1.8).attr('stroke-dasharray', '4 3');
          const yi2 = isNum(pi[st.yi]) ? st.yi : lastPop, gap = ai[yi2] - pi[yi2];
          card.append(el('div', 'v', isNum(p[yi2]) ? fmtInt(p[yi2]) + ' kids' : 'no estimate yet'));
          const d1 = el('div', 'd'); d1.append(document.createTextNode(sy(YEARS[yi2]) + ' · kids ' + signed(pi[yi2] - 100, 1) + '%, ADM ' + signed(ai[yi2] - 100, 1) + '% since ' + sy(st.base) + ' · gap '), Object.assign(el('b', gap < 0 ? 'neg' : 'pos'), { textContent: signed(gap, 1) + ' pts' })); card.append(d1);
        } else {
          const s = raw(id), vals = s.map((v, i) => [i, v]).filter(d => isNum(d[1]));
          const cur = s[st.yi], pk = vals.length ? vals.reduce((a, b) => b[1] > a[1] ? b : a)[0] : null;
          card.append(el('div', 'v', isNum(cur) ? (m.kind === 'share' ? cur.toFixed(1) + (m.unit === '%' ? '%' : '') : fmtInt(Math.round(cur))) : 'n/a'));
          const d1 = el('div', 'd');
          if (isNum(cur) && pk !== null && s[pk] > 0 && m.kind === 'count') { const pct = (cur / s[pk] - 1) * 100; d1.append(document.createTextNode(sy(yr()) + ' · '), Object.assign(el('b', pct < 0 ? 'neg' : 'pos'), { textContent: signed(pct, 1) + '%' }), document.createTextNode(' vs peak ' + sy(YEARS[pk]))); }
          else d1.append(document.createTextNode(sy(yr()) + ' · ' + m.label));
          card.append(d1);
          if (vals.length) {
            const y = d3.scaleLinear().domain([d3.min(vals, d => d[1]) * 0.97, d3.max(vals, d => d[1]) * 1.03 || 1]).range([h - 3, 6]);
            svg.append('path').attr('d', d3.area().x(d => x(YEARS[d[0]])).y0(h - 3).y1(d => y(d[1]))(vals)).attr('fill', isSel(id) ? col : cssVar('--muted')).attr('opacity', 0.15);
            svg.append('path').attr('d', d3.line().x(d => x(YEARS[d[0]])).y(d => y(d[1]))(vals)).attr('fill', 'none').attr('stroke', col).attr('stroke-width', 1.8);
            if (pk !== null) svg.append('circle').attr('cx', x(YEARS[pk])).attr('cy', y(s[pk])).attr('r', 3).attr('fill', cssVar('--ink'));
          }
        }
        svg.append('line').attr('x1', x(yr())).attr('x2', x(yr())).attr('y1', 4).attr('y2', h - 3).attr('stroke', cssVar('--ink')).attr('opacity', .5);
        card.append(svg.node());
        card.onclick = () => toggleSelect(id); card.onkeydown = ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); toggleSelect(id); } };
        card.addEventListener('pointerenter', ev => showTip(unitTip(id), ev)); card.addEventListener('pointermove', moveTip); card.addEventListener('pointerleave', hideTip);
        host.append(card);
      }
    }

    // ---- heatmap
    function renderHeat() {
      const svg = d3.select(q('heat')); svg.selectAll('*').remove();
      const m = M(), f = focus(), others = ids().filter(id => !f.includes(id)), bi = YEARS.indexOf(st.base);
      const key = { latest: id => { const v = cache.get(id)[NY - 1]; return isNum(v) ? v : Infinity; }, cum: id => { const s = raw(id); return isNum(s[bi]) && s[bi] ? (isNum(s[NY - 1]) ? s[NY - 1] : s[NY - 2]) / s[bi] : Infinity; }, size: id => -(admOf(st.level, id)[NY1 - 1]), name: id => name(id) }[st.sort];
      others.sort((a, b) => d3.ascending(key(a), key(b)));
      const rows = f.concat(others), LBL = 190, cw = 46, rh = 11, top = 44, W = LBL + cw * NY + 16, H = top + rows.length * rh + 14;
      svg.attr('viewBox', [0, 0, W, H]).attr('width', W).attr('height', H).style('width', 'auto').style('max-width', '100%');
      const x = i => LBL + i * cw, yOf = r => top + r * rh + (r >= f.length ? 6 : 0);
      svg.append('g').selectAll('text').data(YEARS).join('text').attr('class', 'col').attr('x', (d, i) => x(i) + cw / 2).attr('y', top - 6).text(d => sy(d));
      drawEvents(svg, d3.scaleLinear().domain([YEARS[0] - 0.5, YEARS[NY - 1] + 0.5]).range([LBL, LBL + cw * NY]), 12, H - 8);
      const g = svg.append('g');
      rows.forEach((id, r) => {
        const vals = cache.get(id), yy = yOf(r);
        g.append('text').attr('class', 'row' + (f.includes(id) ? ' pinned' : '') + (isSel(id) ? ' sel' : '')).attr('x', LBL - 6).attr('y', yy + rh - 2.5).attr('text-anchor', 'end').text(sname(id).slice(0, 30)).on('click', () => toggleSelect(id));
        if (isSel(id)) g.append('rect').attr('x', 0).attr('y', yy).attr('width', 5).attr('height', rh - 1).attr('fill', slotColor(slotOf(id)));
        hoverable(g.append('g').selectAll('rect').data(vals.map((v, i) => ({ v, i }))).join('rect').attr('class', 'cell').attr('x', d => x(d.i) + 0.5).attr('y', yy + 0.5).attr('width', cw - 1).attr('height', rh - 1).attr('fill', d => fill(d.v)).attr('rx', 1)
          .on('click', (ev, d) => { setYear(d.i); if (!isSel(id)) toggleSelect(id); }),
          d => [el('div', 't', name(id) + ' · ' + sy(YEARS[d.i])), el('div', 'big' + (!isNum(d.v) || m.kind === 'cat' ? '' : d.v < 0 ? ' neg' : ' pos'), fmtVal(d.v)), el('div', 'k', metricLabel()), row(m.label, isNum(raw(id)[d.i]) ? (m.kind === 'share' ? raw(id)[d.i].toFixed(1) : m.kind === 'cat' ? '' : fmtInt(Math.round(raw(id)[d.i]))) : 'n/a')]);
      });
      if (others.length) svg.append('line').attr('class', 'divider').attr('x1', 0).attr('x2', W).attr('y1', yOf(f.length) - 3).attr('y2', yOf(f.length) - 3);
      svg.append('rect').attr('x', x(st.yi)).attr('y', top - 2).attr('width', cw).attr('height', H - top - 4).attr('fill', 'none').attr('stroke', cssVar('--ink')).attr('stroke-width', 1.2).attr('rx', 2).attr('pointer-events', 'none');
      q('heatTitle').textContent = (st.level === 'lea' ? 'Every district, every year' : 'Every county, every year') + ' · ' + metricLabel();
    }

    // ---- table
    function renderTable() {
      const host = q('tableHost'); host.replaceChildren(); if (!q('tableDetails').open) return;
      const m = M();
      const rows = ids().map(id => ({ id, v: valueAt(id), r: raw(id)[st.yi] })).sort((a, b) => d3.ascending(isNum(a.v) ? a.v : Infinity, isNum(b.v) ? b.v : Infinity));
      const t = el('table', 'data'), th = el('tr');
      ['#', st.level === 'lea' ? 'District' : 'County', st.level === 'lea' ? 'County' : 'Districts', m.label + ' ' + sy(yr()), metricLabel()].forEach((h, i) => th.append(Object.assign(el('th', i >= 3 ? 'num' : ''), { textContent: h }))); t.append(th);
      rows.forEach((r, i) => { const tr = el('tr', isSel(r.id) ? 'hl' : ''); tr.append(el('td', '', String(i + 1)), el('td', '', name(r.id)), el('td', '', st.level === 'lea' ? D1.leas[r.id].county : D1.counties[r.id].leaCodes.map(k => shortName('lea', k)).join(', ')), el('td', 'num', isNum(r.r) ? (m.kind === 'share' ? r.r.toFixed(1) : m.kind === 'cat' ? m.classes[r.r].label : fmtInt(Math.round(r.r))) : 'n/a'), el('td', 'num', fmtVal(r.v))); t.append(tr); });
      host.append(t);
    }

    // ---- hash state
    function readHash() {
      const h = new URLSearchParams(location.hash.replace(/^#/, '')), k = cfg.key + '_';
      if (cfg.levels.some(l => l.id === h.get(k + 'level'))) st.level = h.get(k + 'level');
      if (cfg.measures.some(m => m.id === h.get(k + 'measure'))) st.measure = h.get(k + 'measure');
      if (VIEWS[h.get(k + 'view')]) st.view = h.get(k + 'view');
      if (YEARS.includes(+h.get(k + 'base')) && +h.get(k + 'base') < YEARS[NY - 1]) st.base = +h.get(k + 'base');
      if (YEARS.includes(+h.get(k + 'year'))) st.yi = YEARS.indexOf(+h.get(k + 'year'));
      if (h.get(k + 'sel')) { const pool = st.level === 'lea' ? D1.leas : D1.counties; const s = h.get(k + 'sel').split(',').filter(id => pool[id]).slice(0, 8); if (s.length) { st.selected[st.level] = s; st.slots[st.level] = new Map(s.map((id, i) => [id, i + 1])); } }
    }
    function writeHash() {
      const h = new URLSearchParams(location.hash.replace(/^#/, '')), k = cfg.key + '_';
      h.set(k + 'level', st.level); h.set(k + 'measure', st.measure); h.set(k + 'view', st.view); h.set(k + 'base', st.base); h.set(k + 'year', yr()); h.set(k + 'sel', sel().join(','));
      history.replaceState(null, '', '#' + h.toString());
    }

    // ---- orchestration
    const ctx = { st, q, YEARS, ids, raw, valueAt, cache: () => cache, sel, slotOf, slotColor, isSel, name, sname, yr, focus, anchor, toggleSelect, setYear, drawEvents, hoverable, showTip, hideTip, moveTip, el, row, color: () => color, fill, fmtVal, metricLabel, M, VIEWS, spark };
    function renderYear() {
      q('yearBig').textContent = sy(yr()); q('range').value = st.yi;
      updateMapFills(); q('mapTitle').textContent = 'Statewide · ' + (st.level === 'lea' ? '115 districts' : '100 counties') + ' · ' + sy(yr());
      renderStrip(); renderCards(); renderTable(); renderHeat();
      d3.select(q('lineChart')).select('.cursor-line').attr('x1', xLine(yr())).attr('x2', xLine(yr()));
      if (cfg.renderContextYear) cfg.renderContextYear(ctx);
      writeHash();
    }
    const xLine = d3.scaleLinear().domain([YEARS[0], YEARS[NY - 1]]).range([56, 760 - 150]);
    function renderAll() {
      recompute(); buildColor();
      q('yearBig').textContent = sy(yr()); q('range').value = st.yi;
      renderMaps(); renderLegend(); renderStrip(); renderLine(); renderCards(); renderHeat(); renderTable();
      if (cfg.renderKpis) cfg.renderKpis(ctx);
      if (cfg.renderContext) cfg.renderContext(ctx);
      writeHash();
    }
    function init() {
      readHash(); buildControls();
      const lm = q('lineMode'); if (lm) lm.querySelectorAll('button').forEach(b => b.addEventListener('click', () => { lm.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', String(x === b))); st.lineMode = b.dataset.v; renderLine(); }));
      q('sort').addEventListener('change', e => { st.sort = e.target.value; renderHeat(); });
      q('tableDetails').addEventListener('toggle', renderTable);
      renderAll();
      root.addEventListener('keydown', ev => { if (ev.target.matches('input, select, textarea, button')) return; if (ev.key === 'ArrowLeft') { stopPlay(); setYear(st.yi - 1); } if (ev.key === 'ArrowRight') { stopPlay(); setYear(st.yi + 1); } });
    }
    return { init, renderAll, stopPlay, ctx };
  }

  // ================================================================== TAB 0 config (elementary schools)
  const BS = D1.bySpan;
  const nz = a => a.map(v => v > 0 ? v : null);
  const leaSpan = (id, sps) => Y1.map((y, i) => sps.reduce((t, sp) => t + BS.leas[id][sp][i], 0));
  const countySpan = (gid, sps, withCharter) => Y1.map((y, i) => D1.counties[gid].leaCodes.reduce((t, k) => t + sps.reduce((u, sp) => u + BS.leas[k][sp][i], 0), 0) + (withCharter ? sps.reduce((u, sp) => u + BS.countyCharter[gid][sp][i], 0) : 0));
  const stateSpan = (sps, withCharter) => Y1.map((y, i) => sps.reduce((t, sp) => t + BS.stateLea[sp][i] + (withCharter ? BS.stateCharter[sp][i] : 0), 0));
  const spanTip = (lv, id, i) => {
    const e = lv === 'lea' ? BS.leas[id].E[i] : D1.counties[id].leaCodes.reduce((t, k) => t + BS.leas[k].E[i], 0);
    const k8 = lv === 'lea' ? BS.leas[id].I[i] : D1.counties[id].leaCodes.reduce((t, k) => t + BS.leas[k].I[i], 0);
    const rows = [['District E schools', fmtInt(e)], ['District K-8 (I) schools', fmtInt(k8)], ['All district ADM', fmtInt(admOf('lea' === lv ? 'lea' : 'county', id)[i] - (lv === 'county' ? D1.counties[id].charter[i] : 0))]];
    if (lv === 'county') rows.push(['Charter E + K-8 schools in county', fmtInt(BS.countyCharter[id].E[i] + BS.countyCharter[id].I[i])]);
    return rows;
  };
  const tab0 = createPage({
    root: document.getElementById('tab0'), key: 'p0', years: Y1, levels: [{ id: 'lea', label: 'Districts (LEAs)' }, { id: 'county', label: 'Counties' }], defaultLevel: 'lea',
    focus: { lea: TRIANGLE_LEA, county: TRIANGLE_COUNTY }, anchor: { lea: '681LEA', county: '37135' }, defaultMeasure: 'elemE', defaultView: 'cum', defaultBase: 2015, lineChart: 'measure',
    measures: [
      { id: 'elemE', label: 'Elementary schools (E) ADM, district schools', unit: 'students', kind: 'count', series: (lv, id) => nz(lv === 'lea' ? leaSpan(id, ['E']) : countySpan(id, ['E'], false)), stateSeries: () => stateSpan(['E'], false), tipRows: spanTip },
      { id: 'elemEI', label: 'Elementary + K-8 schools (E + I) ADM, district schools', unit: 'students', kind: 'count', series: (lv, id) => nz(lv === 'lea' ? leaSpan(id, ['E', 'I']) : countySpan(id, ['E', 'I'], false)), stateSeries: () => stateSpan(['E', 'I'], false), tipRows: spanTip },
      { id: 'elemE_c', label: 'Elementary schools (E) ADM, district + charter', unit: 'students', kind: 'count', levels: ['county'], series: (lv, id) => nz(countySpan(id, ['E'], true)), stateSeries: () => stateSpan(['E'], true), tipRows: spanTip },
      { id: 'elemEI_c', label: 'Elementary + K-8 (E + I) ADM, district + charter', unit: 'students', kind: 'count', levels: ['county'], series: (lv, id) => nz(countySpan(id, ['E', 'I'], true)), stateSeries: () => stateSpan(['E', 'I'], true), tipRows: spanTip },
      { id: 'elemShare', label: 'Elementary (E) share of district ADM (%)', unit: '%', kind: 'share', series: (lv, id) => { const e = lv === 'lea' ? leaSpan(id, ['E']) : countySpan(id, ['E'], false); const t = lv === 'lea' ? D1.leas[id].adm : D1.counties[id].lea; return Y1.map((y, i) => t[i] > 0 && e[i] > 0 ? e[i] / t[i] * 100 : null); }, stateSeries: () => Y1.map((y, i) => BS.stateLea.E[i] / D1.state.lea[i] * 100), tipRows: spanTip },
    ],
    renderKpis(c) {
      const host = c.q('kpis'); host.replaceChildren();
      const ce = BS.leas['681LEA'].E, cpk = d3.maxIndex(ce), se = BS.stateLea.E, spk = d3.maxIndex(se), i = NY1 - 1;
      const chE = BS.stateCharter.E[i] + BS.stateCharter.I[i];
      const tiles = [
        { v: fmtInt(ce[i]), l: 'CHCCS elementary-school students, ' + sy(Y1[i]) + ' (11 E schools)' },
        { v: signed((ce[i] / ce[cpk] - 1) * 100, 1) + '%', l: 'CHCCS elementary since its ' + sy(Y1[cpk]) + ' peak (' + fmtInt(ce[cpk]) + ')', cls: 'neg' },
        { v: signed((se[i] / se[spk] - 1) * 100, 1) + '%', l: 'All district E schools since their ' + sy(Y1[spk]) + ' peak (' + fmtInt(se[spk]) + ' to ' + fmtInt(se[i]) + ')', cls: 'neg' },
        { v: fmtInt(chE), l: 'Charter students in E or K-8 charter schools, ' + sy(Y1[i]) + ' (up from ' + fmtInt(BS.stateCharter.E[0] + BS.stateCharter.I[0]) + ' in ' + sy(Y1[0]) + ')', cls: 'pos' },
      ];
      for (const t of tiles) { const k = el('div', 'kpi'); k.append(el('div', 'v' + (t.cls ? ' ' + t.cls : ''), t.v), el('div', 'l', t.l)); host.append(k); }
    },
    renderContext(c) { renderElemSectors(c); renderGrowShrink0(c); },
    renderContextYear(c) { d3.select(c.q('ctx1')).select('.cursor-line').attr('x1', xCtx3(c.yr())).attr('x2', xCtx3(c.yr())); renderGrowShrink0(c); },
  });
  function renderElemSectors(c) {
    const svg = d3.select(c.q('ctx1')), W = 760, H = 300; svg.selectAll('*').remove();
    const Mg = { t: 30, r: 150, b: 32, l: 56 };
    const keys = [['District E schools', i => BS.stateLea.E[i], '--s1'], ['District K-8 (I) schools', i => BS.stateLea.I[i], '--s3'], ['Charter E + K-8 schools', i => BS.stateCharter.E[i] + BS.stateCharter.I[i], '--s2']];
    const rows = Y1.map((y, i) => { const o = { y }; keys.forEach(k => { o[k[0]] = k[1](i); }); return o; });
    const stack = d3.stack().keys(keys.map(k => k[0]))(rows);
    const x = xCtx3, y = d3.scaleLinear().domain([0, d3.max(rows, r => keys.reduce((t, k) => t + r[k[0]], 0)) * 1.05]).nice().range([H - Mg.b, Mg.t]);
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(' + Mg.l + ',0)').call(d3.axisLeft(y).ticks(6).tickFormat(d3.format('.2s')).tickSize(-(W - Mg.r - Mg.l))).call(g => { g.select('.domain').remove(); g.selectAll('line').attr('class', 'gridline'); });
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(0,' + (H - Mg.b) + ')').call(d3.axisBottom(x).ticks(10).tickFormat(v => sy(v)).tickSize(4));
    const area = d3.area().x(d => x(d.data.y)).y0(d => y(d[0])).y1(d => y(d[1]));
    stack.forEach((s, i) => svg.append('path').attr('d', area(s)).attr('fill', cssVar(keys[i][2])).attr('opacity', 0.85).attr('stroke', cssVar('--surface')).attr('stroke-width', 1.5));
    c.drawEvents(svg, x, Mg.t - 14, H - Mg.b);
    svg.append('line').attr('class', 'cursor-line').attr('x1', x(c.yr())).attr('x2', x(c.yr())).attr('y1', Mg.t).attr('y2', H - Mg.b);
    const lg = svg.append('g').attr('transform', 'translate(' + (W - Mg.r + 8) + ',' + (Mg.t + 8) + ')');
    keys.forEach((k, i) => { lg.append('rect').attr('x', 0).attr('y', i * 16).attr('width', 12).attr('height', 10).attr('rx', 2).attr('fill', cssVar(k[2])); lg.append('text').attr('x', 16).attr('y', i * 16 + 9).attr('font-size', 11).attr('fill', cssVar('--ink-2')).text(k[0] + ' ' + d3.format('.3s')(rows[NY1 - 1][k[0]])); });
    lg.append('text').attr('x', 0).attr('y', keys.length * 16 + 14).attr('font-size', 10).attr('fill', cssVar('--muted')).text('values for ' + sy(Y1[NY1 - 1]));
    svg.append('text').attr('x', Mg.l).attr('y', 14).attr('font-size', 11).attr('fill', cssVar('--muted')).text('Students (ADM), statewide');
    const hover = svg.append('g').style('display', 'none'); const hl = hover.append('line').attr('stroke', cssVar('--ink')).attr('y1', Mg.t).attr('y2', H - Mg.b).attr('opacity', .5);
    svg.append('rect').attr('x', Mg.l).attr('y', Mg.t).attr('width', W - Mg.r - Mg.l).attr('height', H - Mg.b - Mg.t).attr('fill', 'transparent').style('cursor', 'crosshair')
      .on('pointerenter', () => hover.style('display', null)).on('pointerleave', () => { hover.style('display', 'none'); hideTip(); })
      .on('pointermove', ev => { const [mx] = d3.pointer(ev); const i = Y1.indexOf(Math.max(Y1[0], Math.min(Y1[NY1 - 1], Math.round(x.invert(mx))))); hl.attr('x1', x(Y1[i])).attr('x2', x(Y1[i])); const r = rows[i]; showTip([el('div', 't', sy(Y1[i]))].concat(keys.map(k => row(k[0], fmtInt(r[k[0]])))).concat([row('Total', fmtInt(keys.reduce((t, k) => t + r[k[0]], 0)))]), ev); })
      .on('click', ev => { const [mx] = d3.pointer(ev); c.setYear(Y1.indexOf(Math.max(Y1[0], Math.min(Y1[NY1 - 1], Math.round(x.invert(mx)))))); });
  }
  function renderGrowShrink0(c) {
    const svg = d3.select(c.q('ctx2')), W = 520, H = 300; svg.selectAll('*').remove();
    const Mg = { t: 30, r: 16, b: 32, l: 40 }, n = c.ids().length;
    const counts = Y1.map((yv, i) => { if (i === 0) return null; let up = 0, down = 0; for (const id of c.ids()) { const s = c.raw(id); if (!isNum(s[i]) || !isNum(s[i - 1])) continue; if (s[i] > s[i - 1]) up++; else if (s[i] < s[i - 1]) down++; } return { yv, up, down }; }).filter(Boolean);
    const x = d3.scaleBand().domain(counts.map(d => d.yv)).range([Mg.l, W - Mg.r]).paddingInner(0.25), y = d3.scaleLinear().domain([-n, n]).range([H - Mg.b, Mg.t]);
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(' + Mg.l + ',0)').call(d3.axisLeft(y).ticks(6).tickFormat(v => Math.abs(v)).tickSize(-(W - Mg.r - Mg.l))).call(g => { g.select('.domain').remove(); g.selectAll('line').attr('class', 'gridline'); });
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(0,' + (H - Mg.b) + ')').call(d3.axisBottom(x).tickFormat(v => String(v).slice(2)).tickSize(0)).call(g => g.select('.domain').remove());
    svg.append('line').attr('x1', Mg.l).attr('x2', W - Mg.r).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', cssVar('--axis'));
    const bars = svg.append('g').selectAll('g').data(counts).join('g');
    bars.append('rect').attr('x', d => x(d.yv)).attr('width', x.bandwidth()).attr('y', d => y(d.up)).attr('height', d => Math.max(0, y(0) - y(d.up) - 1)).attr('fill', cssVar('--pos')).attr('rx', 2);
    bars.append('rect').attr('x', d => x(d.yv)).attr('width', x.bandwidth()).attr('y', y(0) + 1).attr('height', d => Math.max(0, y(0) - y(d.down) - 1)).attr('fill', cssVar('--neg')).attr('rx', 2);
    hoverable(bars.append('rect').attr('x', d => x(d.yv) - x.step() * 0.125).attr('width', x.step()).attr('y', Mg.t).attr('height', H - Mg.b - Mg.t).attr('fill', 'transparent').on('click', (ev, d) => c.setYear(Y1.indexOf(d.yv))), d => [el('div', 't', sy(d.yv)), row('Grew', String(d.up)), row('Shrank', String(d.down)), row('Flat or no value', String(n - d.up - d.down))]);
    c.drawEvents(svg, d3.scaleLinear().domain([Y1[1] - 0.5, Y1[NY1 - 1] + 0.5]).range([Mg.l, W - Mg.r]), Mg.t - 14, H - Mg.b);
    const cur = counts.find(d => d.yv === c.yr());
    if (cur) svg.append('rect').attr('x', x(cur.yv) - 2).attr('y', Mg.t).attr('width', x.bandwidth() + 4).attr('height', H - Mg.b - Mg.t).attr('fill', 'none').attr('stroke', cssVar('--ink')).attr('rx', 2).attr('pointer-events', 'none');
    c.q('gsTitle').textContent = 'How many ' + (c.st.level === 'lea' ? 'districts' : 'counties') + ' grew or shrank each year \u00b7 ' + c.M().label;
  }

  // ================================================================== TAB 2 config
  const npAt = (id, key, i) => np[id][key][i];
  const npSum = (id, i) => (isNum(np[id].private[i]) && isNum(np[id].home[i])) ? np[id].private[i] + np[id].home[i] : null;
  const tab2 = createPage({
    root: document.getElementById('tab2'), key: 'p2', years: NPY, levels: [{ id: 'county', label: 'Counties' }], defaultLevel: 'county',
    focus: { county: TRIANGLE_COUNTY }, anchor: { county: '37135' }, defaultMeasure: 'nonpublic', defaultView: 'cum', defaultBase: 2015, lineChart: 'measure',
    measures: [
      { id: 'nonpublic', label: 'Non-public students (private + home)', unit: 'students', kind: 'count', series: (lv, id) => NPY.map((y, i) => npSum(id, i)), stateSeries: () => NPY.map((y, i) => npState.private[i] + npState.home[i]),
        tipRows: (lv, id, i) => [['Private', fmtInt(np[id].private[i] ?? 0)], ['Home school (est.)', fmtInt(np[id].home[i] ?? 0)]] },
      { id: 'private', label: 'Private school students', unit: 'students', kind: 'count', series: (lv, id) => np[id].private.slice(), stateSeries: () => npState.private, tipRows: (lv, id, i) => [['Private schools', isNum(np[id].privateSchools[i]) ? String(np[id].privateSchools[i]) : 'n/a']] },
      { id: 'home', label: 'Home school students (est.)', unit: 'students', kind: 'count', hue: 'orange', series: (lv, id) => np[id].home.slice(), stateSeries: () => npState.home, tipRows: (lv, id, i) => [['Registered home schools', isNum(np[id].homeSchools[i]) ? fmtInt(np[id].homeSchools[i]) : 'n/a']] },
      { id: 'npShare', label: 'Non-public share of all students (%)', unit: '%', kind: 'share', series: (lv, id) => NPY.map((y, i) => { const a = at1(admCounty(id), y), n = npSum(id, i); return isNum(a) && isNum(n) ? n / (a + n) * 100 : null; }),
        stateSeries: () => NPY.map((y, i) => { const a = at1(stateAdm, y); return isNum(a) ? (npState.private[i] + npState.home[i]) / (a + npState.private[i] + npState.home[i]) * 100 : null; }),
        tipRows: (lv, id, i) => [['Public ADM (district + charter)', isNum(at1(admCounty(id), NPY[i])) ? fmtInt(at1(admCounty(id), NPY[i])) : 'n/a'], ['Non-public', isNum(npSum(id, i)) ? fmtInt(npSum(id, i)) : 'n/a']] },
      { id: 'npPer100', label: 'Non-public students per 100 school-age children', unit: 'per 100', kind: 'share', series: (lv, id) => NPY.map((y, i) => { const p = at1(D2.population.counties[id].age517, y), n = npSum(id, i); return isNum(p) && isNum(n) && p > 0 ? n / p * 100 : null; }),
        stateSeries: () => NPY.map((y, i) => { const p = at1(statePop, y); return isNum(p) ? (npState.private[i] + npState.home[i]) / p * 100 : null; }),
        tipRows: (lv, id, i) => [['Children 5-17', isNum(at1(D2.population.counties[id].age517, NPY[i])) ? fmtInt(at1(D2.population.counties[id].age517, NPY[i])) : 'n/a']] },
      { id: 'homeSchools', label: 'Registered home schools (households)', unit: 'schools', kind: 'count', hue: 'orange', series: (lv, id) => np[id].homeSchools.slice(), stateSeries: () => D2.nonpublicState.homeSchools },
      { id: 'privateSchools', label: 'Private schools', unit: 'schools', kind: 'count', series: (lv, id) => np[id].privateSchools.slice(), stateSeries: () => D2.nonpublicState.privateSchools },
      { id: 'vouchers', label: 'Opportunity Scholarship recipients, 2024-25', unit: 'students', kind: 'count', single: 2025, series: (lv, id) => NPY.map(y => y === 2025 ? (D2.vouchers.byCounty[id] ?? null) : null) },
      { id: 'vouchersPer100', label: 'Voucher recipients per 100 school-age children, 2024-25', unit: 'per 100', kind: 'share', single: 2025, series: (lv, id) => NPY.map(y => { const v = D2.vouchers.byCounty[id], p = at1(D2.population.counties[id].age517, 2025); return y === 2025 && isNum(v) && p > 0 ? v / p * 100 : null; }) },
    ],
    renderKpis(c) {
      const host = c.q('kpis'); host.replaceChildren();
      const iLast = NPY.length - 1, i19 = NPY.indexOf(2019), oc = '37135';
      const tiles = [
        { v: fmtInt(npState.private[iLast]), l: 'Private school students statewide, ' + sy(NPY[iLast]) + ' (' + signed((npState.private[iLast] / npState.private[i19] - 1) * 100, 0) + '% since ' + sy(2019) + ')', cls: 'pos' },
        { v: fmtInt(npState.home[iLast]), l: 'Home school students statewide (est.), ' + sy(NPY[iLast]) + ' (' + signed((npState.home[iLast] / npState.home[i19] - 1) * 100, 0) + '% since ' + sy(2019) + ')', cls: 'pos' },
        { v: fmtInt(D2.vouchers.state['2025'].total), l: 'Opportunity Scholarship students funded in 2024-25, up from ' + fmtInt(D2.vouchers.state['2024'].total) + ' the year before', cls: 'pos' },
        { v: (npSum(oc, NPY.indexOf(2025)) / (admCounty(oc)[NY1 - 1] + npSum(oc, NPY.indexOf(2025))) * 100).toFixed(1) + '%', l: 'Orange County students in private or home school, 2024-25 (' + fmtInt(npSum(oc, NPY.indexOf(2025))) + ' students; ' + fmtInt(D2.vouchers.byCounty[oc]) + ' on vouchers)' },
      ];
      for (const t of tiles) { const k = el('div', 'kpi'); k.append(el('div', 'v' + (t.cls ? ' ' + t.cls : ''), t.v), el('div', 'l', t.l)); host.append(k); }
    },
    renderContext(c) { renderSectors(c); renderShares(c); renderVoucherBars(c); renderPriorLea(c); },
    renderContextYear(c) { d3.select(c.q('ctx1')).select('.cursor-line').attr('x1', xCtx1(c.yr())).attr('x2', xCtx1(c.yr())); d3.select(c.q('ctx2')).select('.cursor-line').attr('x1', xCtx2(c.yr())).attr('x2', xCtx2(c.yr())); },
  });
  const xCtx1 = d3.scaleLinear().domain([NPY[0], NPY[NPY.length - 1]]).range([56, 760 - 150]);
  const xCtx2 = d3.scaleLinear().domain([NPY[0], NPY[NPY.length - 1]]).range([44, 520 - 16]);
  function renderSectors(c) {
    const svg = d3.select(c.q('ctx1')), W = 760, H = 320; svg.selectAll('*').remove();
    const Mg = { t: 30, r: 150, b: 32, l: 56 };
    const keys = [['District ADM', y => at1(D1.state.lea, y), '--s1'], ['Charter ADM', y => at1(D1.state.charter, y), '--s2'], ['Private', y => npState.private[NPY.indexOf(y)], '--s3'], ['Home (est.)', y => npState.home[NPY.indexOf(y)], '--s4']];
    const rows = NPY.map(y => { const o = { y }; keys.forEach(k => { o[k[0]] = k[1](y) ?? 0; }); return o; });
    const stack = d3.stack().keys(keys.map(k => k[0]))(rows);
    const x = xCtx1, y = d3.scaleLinear().domain([0, d3.max(rows, r => keys.reduce((s, k) => s + r[k[0]], 0)) * 1.05]).nice().range([H - Mg.b, Mg.t]);
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(' + Mg.l + ',0)').call(d3.axisLeft(y).ticks(6).tickFormat(d3.format('.2s')).tickSize(-(W - Mg.r - Mg.l))).call(g => { g.select('.domain').remove(); g.selectAll('line').attr('class', 'gridline'); });
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(0,' + (H - Mg.b) + ')').call(d3.axisBottom(x).ticks(10).tickFormat(v => sy(v)).tickSize(4));
    const area = d3.area().x(d => x(d.data.y)).y0(d => y(d[0])).y1(d => y(d[1])).defined(d => d.data.y <= 2025);
    stack.forEach((s, i) => svg.append('path').attr('d', area(s)).attr('fill', cssVar(keys[i][2])).attr('opacity', 0.85).attr('stroke', cssVar('--surface')).attr('stroke-width', 1.5));
    c.drawEvents(svg, x, Mg.t - 14, H - Mg.b);
    svg.append('line').attr('class', 'cursor-line').attr('x1', x(c.yr())).attr('x2', x(c.yr())).attr('y1', Mg.t).attr('y2', H - Mg.b);
    const lg = svg.append('g').attr('transform', 'translate(' + (W - Mg.r + 8) + ',' + (Mg.t + 8) + ')');
    keys.forEach((k, i) => { lg.append('rect').attr('x', 0).attr('y', i * 16).attr('width', 12).attr('height', 10).attr('rx', 2).attr('fill', cssVar(k[2])); lg.append('text').attr('x', 16).attr('y', i * 16 + 9).attr('font-size', 11).attr('fill', cssVar('--ink-2')).text(k[0] + ' ' + d3.format('.3s')(rows[NPY.indexOf(2025)][k[0]])); });
    lg.append('text').attr('x', 0).attr('y', keys.length * 16 + 14).attr('font-size', 10).attr('fill', cssVar('--muted')).text('values for 2024-25');
    svg.append('text').attr('x', Mg.l).attr('y', 14).attr('font-size', 11).attr('fill', cssVar('--muted')).text('Students by sector, statewide');
    const hover = svg.append('g').style('display', 'none'); const hl = hover.append('line').attr('stroke', cssVar('--ink')).attr('y1', Mg.t).attr('y2', H - Mg.b).attr('opacity', .5);
    svg.append('rect').attr('x', Mg.l).attr('y', Mg.t).attr('width', W - Mg.r - Mg.l).attr('height', H - Mg.b - Mg.t).attr('fill', 'transparent').style('cursor', 'crosshair')
      .on('pointerenter', () => hover.style('display', null)).on('pointerleave', () => { hover.style('display', 'none'); hideTip(); })
      .on('pointermove', ev => { const [mx] = d3.pointer(ev); const yv = Math.max(NPY[0], Math.min(NPY[NPY.length - 1], Math.round(x.invert(mx)))); hl.attr('x1', x(yv)).attr('x2', x(yv)); const r = rows[NPY.indexOf(yv)]; const tot = keys.reduce((s, k) => s + r[k[0]], 0); showTip([el('div', 't', sy(yv))].concat(keys.map(k => row(k[0], r[k[0]] ? fmtInt(r[k[0]]) + ' (' + (r[k[0]] / tot * 100).toFixed(1) + '%)' : 'n/a'))).concat([row('All sectors', fmtInt(tot))]), ev); })
      .on('click', ev => { const [mx] = d3.pointer(ev); c.setYear(NPY.indexOf(Math.max(NPY[0], Math.min(NPY[NPY.length - 1], Math.round(x.invert(mx)))))); });
  }
  function renderShares(c) {
    const svg = d3.select(c.q('ctx2')), W = 520, H = 320; svg.selectAll('*').remove();
    const Mg = { t: 30, r: 16, b: 32, l: 44 };
    const ser = [['Charter', '--s2', y => at1(D1.state.charter, y)], ['Private', '--s3', y => npState.private[NPY.indexOf(y)]], ['Home school', '--s4', y => npState.home[NPY.indexOf(y)]]];
    const tot = y => { const a = at1(D1.state.lea, y); return isNum(a) ? a + at1(D1.state.charter, y) + npState.private[NPY.indexOf(y)] + npState.home[NPY.indexOf(y)] : null; };
    const lines = ser.map(s => ({ name: s[0], color: cssVar(s[1]), vals: NPY.map(y => { const t = tot(y); const v = s[2](y); return isNum(t) && isNum(v) ? v / t * 100 : null; }) }));
    lines.push({ name: 'All non-district', color: cssVar('--ink'), vals: NPY.map((y, i) => lines.every(l => isNum(l.vals[i])) ? lines.reduce((s, l) => s + l.vals[i], 0) : null) });
    const x = xCtx2, y = d3.scaleLinear().domain([0, d3.max(lines, l => d3.max(l.vals.filter(isNum))) * 1.1]).nice().range([H - Mg.b, Mg.t]);
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(' + Mg.l + ',0)').call(d3.axisLeft(y).ticks(6).tickFormat(v => v + '%').tickSize(-(W - Mg.r - Mg.l))).call(g => { g.select('.domain').remove(); g.selectAll('line').attr('class', 'gridline'); });
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(0,' + (H - Mg.b) + ')').call(d3.axisBottom(x).ticks(6).tickFormat(v => sy(v)).tickSize(4));
    c.drawEvents(svg, x, Mg.t - 14, H - Mg.b);
    svg.append('line').attr('class', 'cursor-line').attr('x1', x(c.yr())).attr('x2', x(c.yr())).attr('y1', Mg.t).attr('y2', H - Mg.b);
    const line = d3.line().x((d, i) => x(NPY[i])).y(d => y(d)).defined(isNum);
    for (const l of lines) svg.append('path').attr('class', 'series-line').attr('d', line(l.vals)).attr('stroke', l.color);
    const li = NPY.indexOf(2025);
    const labs = lines.map(l => ({ l, y: y(l.vals[li]) })).sort((a, b) => a.y - b.y); for (let i = 1; i < labs.length; i++) if (labs[i].y - labs[i - 1].y < 13) labs[i].y = labs[i - 1].y + 13;
    svg.selectAll('text.sl').data(labs).join('text').attr('class', 'series-label').attr('x', x(2025) - 6).attr('y', d => d.y - 6).attr('text-anchor', 'end').attr('fill', cssVar('--ink')).text(d => d.l.name + ' ' + d.l.vals[li].toFixed(1) + '%');
    const hover = svg.append('g').style('display', 'none'); const hl = hover.append('line').attr('stroke', cssVar('--ink')).attr('y1', Mg.t).attr('y2', H - Mg.b).attr('opacity', .5);
    svg.append('rect').attr('x', Mg.l).attr('y', Mg.t).attr('width', W - Mg.r - Mg.l).attr('height', H - Mg.b - Mg.t).attr('fill', 'transparent').style('cursor', 'crosshair')
      .on('pointerenter', () => hover.style('display', null)).on('pointerleave', () => { hover.style('display', 'none'); hideTip(); })
      .on('pointermove', ev => { const [mx] = d3.pointer(ev); const yv = Math.max(NPY[0], Math.min(2025, Math.round(x.invert(mx)))); hl.attr('x1', x(yv)).attr('x2', x(yv)); const i = NPY.indexOf(yv); showTip([el('div', 't', sy(yv))].concat(lines.map(l => row(l.name, isNum(l.vals[i]) ? l.vals[i].toFixed(1) + '%' : 'n/a'))), ev); })
      .on('click', ev => { const [mx] = d3.pointer(ev); c.setYear(NPY.indexOf(Math.max(NPY[0], Math.min(2025, Math.round(x.invert(mx)))))); });
  }
  function renderVoucherBars(c) {
    const svg = d3.select(c.q('ctx3')), W = 760, H = 300; svg.selectAll('*').remove();
    const Mg = { t: 30, r: 16, b: 32, l: 56 };
    const yrs = Object.keys(D2.vouchers.state).map(Number).sort(), x = d3.scaleBand().domain(yrs).range([Mg.l, W - Mg.r]).paddingInner(0.3);
    const y = d3.scaleLinear().domain([0, d3.max(yrs, yv => D2.vouchers.state[yv].total) * 1.15]).nice().range([H - Mg.b, Mg.t]);
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(' + Mg.l + ',0)').call(d3.axisLeft(y).ticks(5).tickFormat(d3.format('~s')).tickSize(-(W - Mg.r - Mg.l))).call(g => { g.select('.domain').remove(); g.selectAll('line').attr('class', 'gridline'); });
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(0,' + (H - Mg.b) + ')').call(d3.axisBottom(x).tickFormat(v => sy(v)).tickSize(0)).call(g => g.select('.domain').remove());
    const g = svg.append('g').selectAll('g').data(yrs).join('g');
    g.append('rect').attr('x', yv => x(yv)).attr('width', x.bandwidth()).attr('y', yv => y(D2.vouchers.state[yv].total - (D2.vouchers.state[yv].new || 0))).attr('height', yv => y(0) - y(D2.vouchers.state[yv].total - (D2.vouchers.state[yv].new || 0))).attr('fill', cssVar('--s1')).attr('rx', 2);
    g.append('rect').attr('x', yv => x(yv)).attr('width', x.bandwidth()).attr('y', yv => y(D2.vouchers.state[yv].total)).attr('height', yv => Math.max(0, y(D2.vouchers.state[yv].total - (D2.vouchers.state[yv].new || 0)) - y(D2.vouchers.state[yv].total) - 2)).attr('fill', cssVar('--s2')).attr('rx', 2);
    g.append('text').attr('x', yv => x(yv) + x.bandwidth() / 2).attr('y', yv => y(D2.vouchers.state[yv].total) - 6).attr('text-anchor', 'middle').attr('font-size', 11).attr('font-weight', 600).attr('fill', cssVar('--ink')).text(yv => fmtInt(D2.vouchers.state[yv].total));
    hoverable(g.append('rect').attr('x', yv => x(yv)).attr('width', x.bandwidth()).attr('y', Mg.t).attr('height', H - Mg.b - Mg.t).attr('fill', 'transparent'), yv => [el('div', 't', sy(yv)), row('Total funded', fmtInt(D2.vouchers.state[yv].total)), row('New students', fmtInt(D2.vouchers.state[yv].new || 0)), row('Renewals', fmtInt(D2.vouchers.state[yv].total - (D2.vouchers.state[yv].new || 0)))]);
    const lg = svg.append('g').attr('transform', 'translate(' + (Mg.l + 6) + ',' + (Mg.t - 2) + ')');
    [['Renewals', '--s1'], ['New students', '--s2']].forEach((d, i) => { lg.append('rect').attr('x', i * 110).attr('y', 0).attr('width', 12).attr('height', 10).attr('rx', 2).attr('fill', cssVar(d[1])); lg.append('text').attr('x', i * 110 + 16).attr('y', 9).attr('font-size', 11).attr('fill', cssVar('--ink-2')).text(d[0]); });
    svg.append('text').attr('x', W - Mg.r).attr('y', 14).attr('text-anchor', 'end').attr('font-size', 10).attr('fill', cssVar('--muted')).text('2021-22 report not located; 2024-25 is the first universal year');
  }
  function renderPriorLea(c) {
    const host = c.q('ctx4'); host.replaceChildren();
    const yrs = Object.keys(D2.vouchers.priorLea).sort();
    const t = el('table', 'data'); const th = el('tr'); th.append(el('th', '', 'District'));
    for (const yv of yrs) { th.append(Object.assign(el('th', 'num'), { textContent: 'New ' + sy(+yv) })); th.append(Object.assign(el('th', 'num'), { textContent: 'per 1,000 ADM' })); }
    t.append(th);
    const rowsIds = TRIANGLE_LEA.concat(['_state']);
    for (const id of rowsIds) {
      const tr = el('tr', id === '681LEA' ? 'hl' : ''); tr.append(el('td', '', id === '_state' ? 'All NC districts' : D1.leas[id].name));
      for (const yv of yrs) {
        const tbl = D2.vouchers.priorLea[yv]; const n = id === '_state' ? d3.sum(Object.entries(tbl).filter(([k]) => k !== '_other'), d => d[1]) : (tbl[id] ?? 0);
        const adm = id === '_state' ? at1(D1.state.lea, +yv) : at1(D1.leas[id].adm, +yv);
        tr.append(el('td', 'num', fmtInt(n)), el('td', 'num', (n / adm * 1000).toFixed(1)));
      }
      t.append(tr);
    }
    host.append(t);
    const note = el('p', 'hint', 'Counts new scholarship recipients whose parents reported this district as the prior public school. Rate is per 1,000 of the district’s ADM that year. Statewide counts exclude students coming from charters, DoD schools or no public school.'); note.style.marginTop = '8px'; host.append(note);
  }

  // ================================================================== TAB 3 config
  const cumPct = (arr, bi, i) => isNum(arr[i]) && isNum(arr[bi]) && arr[bi] > 0 ? (arr[i] / arr[bi] - 1) * 100 : null;
  const QUAD = [
    { label: 'Kids up, enrollment up', color: () => cssVar('--s1') },
    { label: 'Kids up, enrollment down', color: () => cssVar('--s2') },
    { label: 'Kids down, enrollment down', color: () => cssVar('--muted') },
    { label: 'Kids down, enrollment up', color: () => cssVar('--s3') },
  ];
  function quadOf(dp, da) { if (!isNum(dp) || !isNum(da)) return null; return dp >= 0 ? (da >= 0 ? 0 : 1) : (da >= 0 ? 3 : 2); }
  let tab3;
  tab3 = createPage({
    root: document.getElementById('tab3'), key: 'p3', years: Y1, levels: [{ id: 'lea', label: 'Districts (LEAs)' }, { id: 'county', label: 'Counties' }], defaultLevel: 'lea',
    focus: { lea: TRIANGLE_LEA, county: TRIANGLE_COUNTY }, anchor: { lea: '681LEA', county: '37135' }, defaultMeasure: 'gap', defaultView: 'level', defaultBase: 2015, defaultYear: Y1[lastPop], lineChart: 'popVsAdm',
    measures: [
      { id: 'gap', label: 'Enrollment minus population gap since base', unit: 'pts', kind: 'share', usesBase: true, signed: true, series: (lv, id) => { const bi = Y1.indexOf(tab3 ? tab3.ctx.st.base : 2015); const p = popOf(lv, id), a = admOf(lv, id); return Y1.map((y, i) => i < bi ? null : (isNum(cumPct(a, bi, i)) && isNum(cumPct(p, bi, i)) ? cumPct(a, bi, i) - cumPct(p, bi, i) : null)); },
        tipRows: (lv, id, i) => { const bi = Y1.indexOf(tab3.ctx.st.base); return [['Kids 5-17 since ' + sy(Y1[bi]), signed(cumPct(popOf(lv, id), bi, i) ?? 0, 1) + '%'], ['Public ADM since ' + sy(Y1[bi]), signed(cumPct(admOf(lv, id), bi, i) ?? 0, 1) + '%'], ['Children 5-17', fmtInt(popOf(lv, id)[i])], ['Public ADM', fmtInt(admOf(lv, id)[i])]]; } },
      { id: 'quad', label: 'Quadrant: kids vs. enrollment since base', kind: 'cat', classes: QUAD, usesBase: true, series: (lv, id) => { const bi = Y1.indexOf(tab3 ? tab3.ctx.st.base : 2015); const p = popOf(lv, id), a = admOf(lv, id); return Y1.map((y, i) => i <= bi ? null : quadOf(cumPct(p, bi, i), cumPct(a, bi, i))); },
        tipRows: (lv, id, i) => { const bi = Y1.indexOf(tab3.ctx.st.base); return [['Kids 5-17 since ' + sy(Y1[bi]), signed(cumPct(popOf(lv, id), bi, i) ?? 0, 1) + '%'], ['Public ADM since ' + sy(Y1[bi]), signed(cumPct(admOf(lv, id), bi, i) ?? 0, 1) + '%']]; } },
      { id: 'pop517', label: 'School-age population (ages 5-17)', unit: 'children', kind: 'count', series: (lv, id) => popOf(lv, id).slice(), stateSeries: () => statePop, tipRows: (lv, id, i) => [['Public ADM', fmtInt(admOf(lv, id)[i])]] },
      { id: 'capture', label: 'Public students per 100 school-age children', unit: 'per 100', kind: 'share', series: (lv, id) => { const p = popOf(lv, id), a = admOf(lv, id); return Y1.map((y, i) => p[i] > 0 ? a[i] / p[i] * 100 : null); }, stateSeries: () => Y1.map((y, i) => stateAdm[i] / statePop[i] * 100), tipRows: (lv, id, i) => [['Children 5-17', fmtInt(popOf(lv, id)[i])], ['Public ADM' + (lv === 'lea' ? ' (district only)' : ' (district + charter)'), fmtInt(admOf(lv, id)[i])]] },
      { id: 'adm', label: 'Public school enrollment (ADM)', unit: 'students', kind: 'count', series: (lv, id) => admOf(lv, id).slice(), stateSeries: () => stateAdm, tipRows: (lv, id, i) => [['Children 5-17', fmtInt(popOf(lv, id)[i])]] },
      { id: 'totpop', label: 'Total population', unit: 'people', kind: 'count', series: (lv, id) => totPopOf(lv, id).slice(), tipRows: (lv, id, i) => [['Children 5-17', fmtInt(popOf(lv, id)[i])]] },
    ],
    renderKpis(c) {
      const host = c.q('kpis'); host.replaceChildren();
      const bi = Y1.indexOf(c.st.base), i = lastPop, span = sy(c.st.base) + ' to ' + sy(Y1[i]);
      const mk = (lv, id, label) => { const dp = cumPct(popOf(lv, id), bi, i), da = cumPct(admOf(lv, id), bi, i); return { v: signed(da - dp, 1) + ' pts', l: label + ': ADM ' + signed(da, 1) + '% vs. kids ' + signed(dp, 1) + '%, ' + span, cls: da - dp < 0 ? 'neg' : 'pos' }; };
      const dps = cumPct(statePop, bi, i), das = cumPct(stateAdm, bi, i);
      const tiles = [mk('lea', '681LEA', 'CHCCS'), mk('county', '37135', 'Orange County (all public)'), mk('county', '37183', 'Wake County (all public)'),
        { v: signed(das - dps, 1) + ' pts', l: 'North Carolina: public ADM ' + signed(das, 1) + '% vs. kids 5-17 ' + signed(dps, 1) + '%, ' + span, cls: das - dps < 0 ? 'neg' : 'pos' }];
      for (const t of tiles) { const k = el('div', 'kpi'); k.append(el('div', 'v' + (t.cls ? ' ' + t.cls : ''), t.v), el('div', 'l', t.l)); host.append(k); }
    },
    renderContext(c) { renderScatter(c); renderStateIndex(c); renderQuadBars(c); },
    renderContextYear(c) { renderScatter(c); d3.select(c.q('ctx1')).select('.cursor-line').attr('x1', xCtx3(c.yr())).attr('x2', xCtx3(c.yr())); renderQuadBars(c); },
  });
  const xCtx3 = d3.scaleLinear().domain([Y1[0], Y1[NY1 - 1]]).range([56, 760 - 150]);
  function renderScatter(c) {
    const svg = d3.select(c.q('scatter')), W = 1200, H = 460; svg.selectAll('*').remove();
    const Mg = { t: 24, r: 30, b: 40, l: 60 }, bi = Y1.indexOf(c.st.base), i = c.st.yi, lv = c.st.level;
    c.q('scatterHint').textContent = 'Each dot is one ' + (lv === 'lea' ? 'district' : 'county') + ' in ' + sy(c.yr()) + '. Horizontal: change in children aged 5-17 since ' + sy(c.st.base) + '. Vertical: change in public enrollment. Below the diagonal, enrollment lagged the child population; the shaded quadrant is "more kids, fewer students".';
    const pts = c.ids().map(id => ({ id, dp: cumPct(popOf(lv, id), bi, i), da: cumPct(admOf(lv, id), bi, i), size: admOf(lv, id)[i] })).filter(d => isNum(d.dp) && isNum(d.da));
    if (i <= bi || !pts.length) { svg.append('text').attr('x', Mg.l).attr('y', 40).attr('fill', cssVar('--muted')).text(i > bi ? 'No Census population estimate for ' + sy(c.yr()) + ' yet (estimates run through ' + sy(Y1[lastPop]) + ').' : 'Move the year past the base year to see changes.'); return; }
    const ext = Math.max(niceAbs(d3.max(pts, d => Math.abs(d.dp))), niceAbs(d3.max(pts, d => Math.abs(d.da))));
    const x = d3.scaleLinear().domain([-ext, ext]).range([Mg.l, W - Mg.r]), y = d3.scaleLinear().domain([-ext, ext]).range([H - Mg.b, Mg.t]);
    svg.append('rect').attr('x', x(0)).attr('y', y(0)).attr('width', x(ext) - x(0)).attr('height', y(-ext) - y(0)).attr('fill', cssVar('--s2')).attr('opacity', 0.07);
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(0,' + (H - Mg.b) + ')').call(d3.axisBottom(x).ticks(10).tickFormat(v => signed(v, 0) + '%').tickSize(-(H - Mg.b - Mg.t))).call(g => { g.select('.domain').remove(); g.selectAll('line').attr('class', 'gridline'); });
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(' + Mg.l + ',0)').call(d3.axisLeft(y).ticks(8).tickFormat(v => signed(v, 0) + '%').tickSize(-(W - Mg.r - Mg.l))).call(g => { g.select('.domain').remove(); g.selectAll('line').attr('class', 'gridline'); });
    svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', Mg.t).attr('y2', H - Mg.b).attr('stroke', cssVar('--axis'));
    svg.append('line').attr('x1', Mg.l).attr('x2', W - Mg.r).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', cssVar('--axis'));
    svg.append('line').attr('x1', x(-ext)).attr('x2', x(ext)).attr('y1', y(-ext)).attr('y2', y(ext)).attr('stroke', cssVar('--muted')).attr('stroke-dasharray', '3 4');
    svg.append('text').attr('x', W - Mg.r).attr('y', H - Mg.b - 6).attr('text-anchor', 'end').attr('font-size', 11).attr('fill', cssVar('--muted')).text('children 5-17, change since ' + sy(c.st.base) + ' →');
    svg.append('text').attr('x', Mg.l + 6).attr('y', Mg.t + 12).attr('font-size', 11).attr('fill', cssVar('--muted')).text('↑ public enrollment, change since ' + sy(c.st.base));
    svg.append('text').attr('x', W - Mg.r - 6).attr('y', y(0) + 16).attr('text-anchor', 'end').attr('font-size', 11).attr('font-weight', 600).attr('fill', cssVar('--s2')).text('more kids, fewer students');
    const r = d3.scaleSqrt().domain([0, d3.max(pts, d => d.size)]).range([3, 16]);
    const g = svg.append('g');
    const fixed = c.focus();
    hoverable(g.selectAll('circle.o').data(pts.filter(d => !c.isSel(d.id))).join('circle').attr('cx', d => x(d.dp)).attr('cy', d => y(d.da)).attr('r', d => r(d.size)).attr('fill', d => QUAD[quadOf(d.dp, d.da)].color()).attr('opacity', 0.55).attr('stroke', cssVar('--surface')).style('cursor', 'pointer').on('click', (ev, d) => c.toggleSelect(d.id)), d => scatterTip(c, d));
    hoverable(g.selectAll('circle.s').data(pts.filter(d => c.isSel(d.id))).join('circle').attr('cx', d => x(d.dp)).attr('cy', d => y(d.da)).attr('r', d => r(d.size) + 1).attr('fill', d => c.slotColor(c.slotOf(d.id))).attr('stroke', cssVar('--ink')).attr('stroke-width', 1.5).style('cursor', 'pointer').on('click', (ev, d) => c.toggleSelect(d.id)), d => scatterTip(c, d));
    const labPts = pts.filter(d => fixed.includes(d.id) || c.isSel(d.id)).map(d => ({ ...d, lx: x(d.dp) + r(d.size) + 4, ly: y(d.da) })).sort((a, b) => a.ly - b.ly);
    for (let k = 1; k < labPts.length; k++) for (let j = 0; j < k; j++) if (Math.abs(labPts[k].lx - labPts[j].lx) < 70 && Math.abs(labPts[k].ly - labPts[j].ly) < 13) labPts[k].ly = labPts[j].ly + 13;
    g.selectAll('text.l').data(labPts).join('text').attr('class', 'series-label').attr('x', d => d.lx).attr('y', d => d.ly).attr('dy', '0.35em').attr('fill', cssVar('--ink')).text(d => c.sname(d.id));
    svg.append('text').attr('x', W - Mg.r).attr('y', Mg.t + 12).attr('text-anchor', 'end').attr('font-size', 11).attr('fill', cssVar('--ink-2')).text('dot size = public enrollment');
  }
  function niceAbs(v) { if (!isNum(v) || v <= 0) return 5; const s = [5, 10, 15, 20, 30, 40, 50, 75, 100, 150, 200]; return s.find(k => k >= v) || Math.ceil(v / 100) * 100; }
  function scatterTip(c, d) { const lv = c.st.level; return [el('div', 't', c.name(d.id)), el('div', 'big', QUAD[quadOf(d.dp, d.da)].label), row('Children 5-17 since ' + sy(c.st.base), signed(d.dp, 1) + '%'), row('Public ADM since ' + sy(c.st.base), signed(d.da, 1) + '%'), row('Gap', signed(d.da - d.dp, 1) + ' pts'), row('Public ADM ' + sy(c.yr()), fmtInt(admOf(lv, d.id)[c.st.yi])), row('Children 5-17 ' + sy(c.yr()), fmtInt(popOf(lv, d.id)[c.st.yi])), el('div', 'sub', 'Click to ' + (c.isSel(d.id) ? 'remove from' : 'add to') + ' the comparison')]; }
  function renderStateIndex(c) {
    const svg = d3.select(c.q('ctx1')), W = 760, H = 320; svg.selectAll('*').remove();
    const Mg = { t: 30, r: 150, b: 32, l: 56 }, bi = Y1.indexOf(c.st.base);
    const npTotal = Y1.map(y => { const i = NPY.indexOf(y); return npState.private[i] + npState.home[i]; });
    const lines = [{ name: 'Children 5-17', color: cssVar('--ink'), vals: statePop.map(v => isNum(v) ? v / statePop[bi] * 100 : null) }, { name: 'Public ADM (all)', color: cssVar('--s1'), vals: stateAdm.map(v => v / stateAdm[bi] * 100) }, { name: 'District ADM', color: cssVar('--s1'), dash: true, vals: D1.state.lea.map(v => v / D1.state.lea[bi] * 100) }, { name: 'Private + home school', color: cssVar('--s3'), vals: npTotal.map(v => v / npTotal[bi] * 100) }];
    const x = xCtx3, allv = lines.flatMap(l => l.vals).filter(isNum), y = d3.scaleLinear().domain([Math.min(d3.min(allv), 100) - 2, Math.max(d3.max(allv), 100) + 2]).nice().range([H - Mg.b, Mg.t]);
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(' + Mg.l + ',0)').call(d3.axisLeft(y).ticks(6).tickSize(-(W - Mg.r - Mg.l))).call(g => { g.select('.domain').remove(); g.selectAll('line').attr('class', 'gridline'); });
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(0,' + (H - Mg.b) + ')').call(d3.axisBottom(x).ticks(10).tickFormat(v => sy(v)).tickSize(4));
    svg.append('line').attr('x1', Mg.l).attr('x2', W - Mg.r).attr('y1', y(100)).attr('y2', y(100)).attr('stroke', cssVar('--axis'));
    c.drawEvents(svg, x, Mg.t - 14, H - Mg.b);
    svg.append('line').attr('class', 'cursor-line').attr('x1', x(c.yr())).attr('x2', x(c.yr())).attr('y1', Mg.t).attr('y2', H - Mg.b);
    const line = d3.line().x((d, i) => x(Y1[i])).y(d => y(d)).defined(isNum);
    for (const l of lines) svg.append('path').attr('class', 'series-line').attr('d', line(l.vals)).attr('stroke', l.color).attr('stroke-dasharray', l.dash ? '5 4' : null);
    const lastOf = v => { for (let k = NY1 - 1; k >= 0; k--) if (isNum(v[k])) return k; return 0; };
    const labs = lines.map(l => ({ l, li: lastOf(l.vals), y: y(l.vals[lastOf(l.vals)]) })).sort((a, b) => a.y - b.y); for (let i = 1; i < labs.length; i++) if (labs[i].y - labs[i - 1].y < 13) labs[i].y = labs[i - 1].y + 13;
    svg.selectAll('text.sl').data(labs).join('text').attr('class', 'series-label').attr('x', x(Y1[NY1 - 1]) + 8).attr('y', d => d.y).attr('dy', '0.35em').attr('fill', cssVar('--ink')).text(d => d.l.name + ' ' + d.l.vals[d.li].toFixed(1) + (d.li < NY1 - 1 ? ' (' + sy(Y1[d.li]) + ')' : ''));
    svg.append('text').attr('x', Mg.l).attr('y', 14).attr('font-size', 11).attr('fill', cssVar('--muted')).text('Index, ' + sy(c.st.base) + ' = 100, statewide');
    const hover = svg.append('g').style('display', 'none'); const hl = hover.append('line').attr('stroke', cssVar('--ink')).attr('y1', Mg.t).attr('y2', H - Mg.b).attr('opacity', .5);
    svg.append('rect').attr('x', Mg.l).attr('y', Mg.t).attr('width', W - Mg.r - Mg.l).attr('height', H - Mg.b - Mg.t).attr('fill', 'transparent').style('cursor', 'crosshair')
      .on('pointerenter', () => hover.style('display', null)).on('pointerleave', () => { hover.style('display', 'none'); hideTip(); })
      .on('pointermove', ev => { const [mx] = d3.pointer(ev); const i = Y1.indexOf(Math.max(Y1[0], Math.min(Y1[NY1 - 1], Math.round(x.invert(mx))))); hl.attr('x1', x(Y1[i])).attr('x2', x(Y1[i])); showTip([el('div', 't', sy(Y1[i]))].concat(lines.map(l => row(l.name, isNum(l.vals[i]) ? l.vals[i].toFixed(1) : 'n/a'))).concat([row('Children 5-17', isNum(statePop[i]) ? fmtInt(statePop[i]) : 'no estimate yet'), row('Public ADM', fmtInt(stateAdm[i])), row('Private + home', fmtInt(npTotal[i]))]), ev); })
      .on('click', ev => { const [mx] = d3.pointer(ev); c.setYear(Y1.indexOf(Math.max(Y1[0], Math.min(Y1[NY1 - 1], Math.round(x.invert(mx)))))); });
  }
  function renderQuadBars(c) {
    const svg = d3.select(c.q('ctx2')), W = 520, H = 320; svg.selectAll('*').remove();
    const Mg = { t: 36, r: 16, b: 32, l: 40 }, bi = Y1.indexOf(c.st.base), lv = c.st.level, n = c.ids().length;
    const yrs = Y1.filter((y, i) => i > bi);
    if (!yrs.length) return;
    const counts = yrs.map(y => { const i = Y1.indexOf(y); const o = { y, k: [0, 0, 0, 0] }; for (const id of c.ids()) { const k = quadOf(cumPct(popOf(lv, id), bi, i), cumPct(admOf(lv, id), bi, i)); if (k !== null) o.k[k]++; } return o; });
    const x = d3.scaleBand().domain(yrs).range([Mg.l, W - Mg.r]).paddingInner(0.25), y = d3.scaleLinear().domain([0, n]).range([H - Mg.b, Mg.t]);
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(' + Mg.l + ',0)').call(d3.axisLeft(y).ticks(5).tickSize(-(W - Mg.r - Mg.l))).call(g => { g.select('.domain').remove(); g.selectAll('line').attr('class', 'gridline'); });
    svg.append('g').attr('class', 'axis').attr('transform', 'translate(0,' + (H - Mg.b) + ')').call(d3.axisBottom(x).tickFormat(v => String(v).slice(2)).tickSize(0)).call(g => g.select('.domain').remove());
    const order = [1, 2, 0, 3];
    for (const cnt of counts) { let acc = 0; for (const k of order) { const v = cnt.k[k]; if (!v) continue; svg.append('rect').attr('x', x(cnt.y)).attr('width', x.bandwidth()).attr('y', y(acc + v)).attr('height', Math.max(0, y(acc) - y(acc + v) - 1)).attr('fill', QUAD[k].color()).attr('rx', 1); acc += v; } }
    hoverable(svg.append('g').selectAll('rect').data(counts).join('rect').attr('x', d => x(d.y)).attr('width', x.bandwidth()).attr('y', Mg.t).attr('height', H - Mg.b - Mg.t).attr('fill', 'transparent').on('click', (ev, d) => c.setYear(Y1.indexOf(d.y))), d => [el('div', 't', sy(d.y) + ' vs. ' + sy(c.st.base))].concat(QUAD.map((qd, k) => row(qd.label, String(d.k[k])))));
    if (yrs.includes(c.yr())) svg.append('rect').attr('x', x(c.yr()) - 2).attr('y', Mg.t).attr('width', x.bandwidth() + 4).attr('height', H - Mg.b - Mg.t).attr('fill', 'none').attr('stroke', cssVar('--ink')).attr('rx', 2).attr('pointer-events', 'none');
    const lgRow = svg.append('g').attr('transform', 'translate(' + Mg.l + ',4)');
    QUAD.forEach((qd, k) => { const gx = (k % 2) * 200, gy = Math.floor(k / 2) * 13; lgRow.append('rect').attr('x', gx).attr('y', gy).attr('width', 10).attr('height', 10).attr('rx', 2).attr('fill', qd.color()); lgRow.append('text').attr('x', gx + 13).attr('y', gy + 9).attr('font-size', 10).attr('fill', cssVar('--ink-2')).text(qd.label); });
    c.q('ctx2Title').textContent = 'How ' + (lv === 'lea' ? 'districts' : 'counties') + ' sort into the four quadrants, each year vs. ' + sy(c.st.base);
  }

  // ================================================================== tabs + boot
  const pages = { tab0, tab2, tab3 };
  const inited = new Set();
  function showTab(id, push = true) {
    document.querySelectorAll('.page').forEach(s => { s.hidden = s.id !== id; });
    document.querySelectorAll('.tabbar button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.tab === id)));
    if (pages[id] && !inited.has(id)) { inited.add(id); pages[id].init(); }
    if (push) { const h = new URLSearchParams(location.hash.replace(/^#/, '')); h.set('tab', id); history.replaceState(null, '', '#' + h.toString()); }
    window.scrollTo({ top: 0 });
  }
  document.querySelectorAll('.tabbar button').forEach(b => b.addEventListener('click', () => showTab(b.dataset.tab)));
  document.addEventListener('themechange', () => { for (const id of inited) pages[id].renderAll(); });
  document.addEventListener('keydown', ev => { if (ev.target.matches('input, select, textarea')) return; if (ev.key === ' ') { const vis = document.querySelector('.page:not([hidden])'); if (vis && vis.id !== 'tab1') { ev.preventDefault(); } } });
  const initial = new URLSearchParams(location.hash.replace(/^#/, '')).get('tab');
  showTab(['tab0', 'tab1', 'tab2', 'tab3'].includes(initial) ? initial : 'tab1', false);
})();
