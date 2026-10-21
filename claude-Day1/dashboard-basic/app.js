(() => {
  'use strict';

  // Fallback copy so the page also works when opened via file:// (fetch is blocked there).
  const FALLBACK_CSV = `order_id,order_date,category,region,revenue
ORD001,2026-01-05,Electronics,North,45000
ORD002,2026-01-12,Fashion,South,12000
ORD003,2026-01-18,Grocery,West,8000
ORD004,2026-02-03,Electronics,East,52000
ORD005,2026-02-11,Fashion,North,15000
ORD006,2026-02-19,Grocery,South,9500
ORD007,2026-03-02,Electronics,West,61000
ORD008,2026-03-13,Fashion,East,18000
ORD009,2026-03-25,Grocery,North,11000
ORD010,2026-04-07,Electronics,South,55000
ORD011,2026-04-14,Fashion,West,21000
ORD012,2026-04-28,Grocery,East,12500
ORD013,2026-05-05,Electronics,North,70000
ORD014,2026-05-17,Fashion,South,24000
ORD015,2026-05-23,Grocery,West,14000
ORD016,2026-06-09,Electronics,East,65000
ORD017,2026-06-18,Fashion,North,27000
ORD018,2026-06-26,Grocery,South,16000`;

  const NS = 'http://www.w3.org/2000/svg';
  const $ = (s) => document.querySelector(s);
  const COLS = [
    { key: 'order_id', label: 'Order' },
    { key: 'order_date', label: 'Date' },
    { key: 'category', label: 'Category' },
    { key: 'region', label: 'Region' },
    { key: 'revenue', label: 'Revenue', num: true },
  ];

  let data = [];
  let categories = []; // fixed order -> fixed color
  let bounds = { min: '', max: '' };
  const state = { from: '', to: '', category: 'All', region: 'All', q: '', sort: { key: 'order_date', dir: 1 } };

  // ---------- helpers ----------
  const fmtFull = (n) => n.toLocaleString('en-US');
  const fmtCompact = (n) => {
    const a = Math.abs(n);
    if (a >= 1e6) return +(n / 1e6).toFixed(1) + 'M';
    if (a >= 1e3) return +(n / 1e3).toFixed(a >= 1e5 ? 0 : 1) + 'K';
    return String(n);
  };
  const pct = (n) => (n * 100).toFixed(1) + '%';
  const monthKey = (d) => d.slice(0, 7);
  const monthLabel = (k, withYear) => {
    const [y, m] = k.split('-').map(Number);
    const s = new Date(y, m - 1, 1).toLocaleString('en', { month: 'short' });
    return withYear ? `${s} ${y}` : s;
  };
  const catColor = (c) => {
    const i = categories.indexOf(c);
    return i >= 0 && i < 8 ? `var(--cat-${i + 1})` : 'var(--ink-3)';
  };
  function el(tag, attrs = {}, parent) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (parent) parent.appendChild(e);
    return e;
  }
  function h(tag, props = {}, children = []) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === 'text') e.textContent = v;
      else if (k === 'class') e.className = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v);
    }
    for (const c of [].concat(children)) if (c) e.appendChild(c);
    return e;
  }
  function niceStep(x) {
    const p = Math.pow(10, Math.floor(Math.log10(x)));
    const f = x / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p;
  }

  // ---------- data ----------
  function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/).filter(Boolean);
    const head = lines.shift().split(',').map((s) => s.trim());
    const need = COLS.map((c) => c.key);
    const miss = need.filter((k) => !head.includes(k));
    if (miss.length) throw new Error('CSV is missing column(s): ' + miss.join(', '));
    const rows = [];
    for (const line of lines) {
      const cells = line.split(',').map((s) => s.trim());
      const r = {};
      head.forEach((k, i) => (r[k] = cells[i]));
      r.revenue = Number(r.revenue);
      if (/^\d{4}-\d{2}-\d{2}$/.test(r.order_date) && Number.isFinite(r.revenue)) rows.push(r);
    }
    if (!rows.length) throw new Error('No valid rows found in CSV');
    return rows;
  }

  function setData(rows, sourceText) {
    data = rows;
    categories = [...new Set(rows.map((r) => r.category))].sort();
    const dates = rows.map((r) => r.order_date).sort();
    bounds = { min: dates[0], max: dates[dates.length - 1] };
    Object.assign(state, { from: bounds.min, to: bounds.max, category: 'All', region: 'All', q: '' });
    $('#search').value = '';
    $('#source').textContent = `${sourceText} · ${rows.length} orders · ${bounds.min} to ${bounds.max}`;
    fillSelect($('#categorySel'), categories);
    fillSelect($('#regionSel'), [...new Set(rows.map((r) => r.region))].sort());
    for (const id of ['fromDate', 'toDate']) {
      $('#' + id).min = bounds.min;
      $('#' + id).max = bounds.max;
    }
    syncControls();
    render();
  }

  function fillSelect(sel, values) {
    sel.replaceChildren(h('option', { value: 'All', text: 'All' }), ...values.map((v) => h('option', { value: v, text: v })));
  }

  function filtered(skip) {
    return data.filter(
      (r) =>
        r.order_date >= state.from && r.order_date <= state.to &&
        (skip === 'category' || state.category === 'All' || r.category === state.category) &&
        (skip === 'region' || state.region === 'All' || r.region === state.region)
    );
  }
  const sum = (rows) => rows.reduce((a, r) => a + r.revenue, 0);
  function groupSum(rows, key) {
    const m = new Map();
    for (const r of rows) {
      const g = m.get(r[key]) || { name: r[key], value: 0, orders: 0 };
      g.value += r.revenue; g.orders++;
      m.set(r[key], g);
    }
    return [...m.values()].sort((a, b) => b.value - a.value);
  }

  // ---------- controls ----------
  function presetRanges() {
    const [y, m] = bounds.max.split('-').map(Number);
    const first = (yy, mm) => `${yy}-${String(mm).padStart(2, '0')}-01`;
    const back = (n) => { const d = new Date(y, m - 1 - n, 1); return first(d.getFullYear(), d.getMonth() + 1); };
    const clamp = (d) => (d < bounds.min ? bounds.min : d);
    return [
      { label: 'All time', from: bounds.min, to: bounds.max },
      { label: 'Last 3 months', from: clamp(back(2)), to: bounds.max },
      { label: 'Last month', from: clamp(back(0)), to: bounds.max },
    ];
  }

  function syncControls() {
    $('#fromDate').value = state.from;
    $('#toDate').value = state.to;
    $('#categorySel').value = state.category;
    $('#regionSel').value = state.region;
    $('#presets').replaceChildren(
      ...presetRanges().map((p) =>
        h('button', {
          type: 'button', text: p.label,
          'aria-pressed': String(p.from === state.from && p.to === state.to),
          onclick: () => { state.from = p.from; state.to = p.to; syncControls(); render(); },
        })
      )
    );
  }

  function wireControls() {
    $('#fromDate').addEventListener('change', (e) => {
      state.from = e.target.value || bounds.min;
      if (state.from > state.to) state.to = state.from;
      syncControls(); render();
    });
    $('#toDate').addEventListener('change', (e) => {
      state.to = e.target.value || bounds.max;
      if (state.to < state.from) state.from = state.to;
      syncControls(); render();
    });
    $('#categorySel').addEventListener('change', (e) => { state.category = e.target.value; render(); });
    $('#regionSel').addEventListener('change', (e) => { state.region = e.target.value; render(); });
    $('#search').addEventListener('input', (e) => { state.q = e.target.value.trim().toLowerCase(); renderTable(); });
    $('#resetBtn').addEventListener('click', () => {
      Object.assign(state, { from: bounds.min, to: bounds.max, category: 'All', region: 'All', q: '' });
      $('#search').value = '';
      syncControls(); render();
    });
    $('#csvFile').addEventListener('change', async (e) => {
      const f = e.target.files[0];
      if (!f) return;
      try { setData(parseCSV(await f.text()), f.name); }
      catch (err) { $('#source').textContent = 'Could not load ' + f.name + ': ' + err.message; }
      e.target.value = '';
    });
    $('#themeBtn').addEventListener('click', () => {
      const root = document.documentElement;
      const dark = root.dataset.theme
        ? root.dataset.theme === 'dark'
        : matchMedia('(prefers-color-scheme: dark)').matches;
      root.dataset.theme = dark ? 'light' : 'dark';
      try { localStorage.setItem('theme', root.dataset.theme); } catch {}
    });
    try { const t = localStorage.getItem('theme'); if (t) document.documentElement.dataset.theme = t; } catch {}
    new ResizeObserver(() => renderMonthly()).observe($('#monthly'));
  }

  const toggle = (key, value) => { state[key] = state[key] === value ? 'All' : value; syncControls(); render(); };

  // ---------- tooltip ----------
  const tip = $('#tip');
  function showTip(title, rows, total, x, y) {
    tip.replaceChildren(h('div', { class: 't-title', text: title }));
    for (const r of rows) {
      tip.appendChild(h('div', { class: 't-row' }, [
        r.color ? h('span', { class: 't-key', style: `background:${r.color}` }) : null,
        h('span', { class: 't-name', text: r.name }),
        h('span', { class: 't-val', text: r.value }),
      ]));
    }
    if (total) tip.appendChild(h('div', { class: 't-row t-total' }, [
      h('span', { class: 't-name', text: 'Total' }), h('span', { class: 't-val', text: total }),
    ]));
    tip.hidden = false;
    const w = tip.offsetWidth, hh = tip.offsetHeight;
    tip.style.left = Math.max(8, Math.min(x + 14, innerWidth - w - 8)) + 'px';
    tip.style.top = Math.max(8, Math.min(y + 14, innerHeight - hh - 8)) + 'px';
  }
  const hideTip = () => { tip.hidden = true; };

  // ---------- render ----------
  function render() {
    syncActiveFilters();
    renderKPIs();
    renderMonthly();
    renderBars('#byCategory', 'category', (n) => catColor(n));
    renderBars('#byRegion', 'region', () => 'var(--neutral-bar)');
    renderTable();
  }
  function syncActiveFilters() {
    $('#categorySel').value = state.category;
    $('#regionSel').value = state.region;
  }

  function monthSeries(rows) {
    const keys = [...new Set(rows.map((r) => monthKey(r.order_date)))].sort();
    if (!keys.length) return [];
    // fill gaps so the time axis is continuous
    const out = [];
    let [y, m] = keys[0].split('-').map(Number);
    const [ly, lm] = keys[keys.length - 1].split('-').map(Number);
    while (y < ly || (y === ly && m <= lm)) {
      const k = `${y}-${String(m).padStart(2, '0')}`;
      const mr = rows.filter((r) => monthKey(r.order_date) === k);
      const by = {};
      for (const c of categories) by[c] = sum(mr.filter((r) => r.category === c));
      out.push({ key: k, by, total: sum(mr), orders: mr.length });
      if (++m > 12) { m = 1; y++; }
    }
    return out;
  }

  function renderKPIs() {
    const rows = filtered();
    const total = sum(rows);
    const months = monthSeries(rows);
    const cats = groupSum(rows, 'category');
    const tile = (cls, label, value, extra) =>
      h('div', { class: 'tile ' + cls }, [h('div', { class: 'label', text: label }), h('div', { class: 'value', text: value }), ...extra]);

    let delta = h('div', { class: 'delta', text: ' ' });
    if (months.length >= 2) {
      const a = months[months.length - 1], b = months[months.length - 2];
      if (b.total > 0) {
        const ch = (a.total - b.total) / b.total;
        delta = h('div', { class: 'delta' }, [
          ch === 0
            ? h('span', { text: '— No change' })
            : h('span', { class: ch > 0 ? 'up' : 'down', text: `${ch > 0 ? '▲' : '▼'} ${pct(Math.abs(ch))}` }),
          document.createTextNode(` ${monthLabel(a.key)} vs ${monthLabel(b.key)}`),
        ]);
      }
    }

    const spark = h('div', { class: 'spark' });
    if (months.length >= 2) {
      const W = 160, H = 32, max = Math.max(...months.map((m) => m.total)) || 1;
      const pts = months.map((m, i) => [4 + (i * (W - 8)) / (months.length - 1), H - 4 - (m.total / max) * (H - 8)]);
      const s = el('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, 'aria-hidden': 'true' });
      el('polyline', { points: pts.map((p) => p.join(',')).join(' '), fill: 'none', stroke: 'var(--ink-3)', 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, s);
      const last = pts[pts.length - 1];
      el('circle', { cx: last[0], cy: last[1], r: 4, fill: 'var(--cat-1)', stroke: 'var(--surface)', 'stroke-width': 2 }, s);
      spark.appendChild(s);
    }

    $('#kpis').replaceChildren(
      tile('hero', 'Total revenue', rows.length ? fmtFull(total) : '–', [delta, spark]),
      tile('', 'Orders', fmtFull(rows.length), []),
      tile('', 'Average order value', rows.length ? fmtFull(Math.round(total / rows.length)) : '–', []),
      tile('', 'Top category', cats[0] ? cats[0].name : '–', cats[0] ? [h('div', { class: 'delta', text: `${pct(cats[0].value / total)} of revenue` })] : [])
    );
  }

  function renderMonthly() {
    const host = $('#monthly');
    const rows = filtered();
    const months = monthSeries(rows);
    const present = categories.filter((c) => rows.some((r) => r.category === c));

    $('#monthlySub').textContent = rows.length
      ? `${fmtFull(sum(rows))} across ${months.length} month${months.length === 1 ? '' : 's'}`
      : '';
    $('#legend').replaceChildren(
      ...categories.map((c) =>
        h('button', {
          type: 'button', 'aria-pressed': String(state.category === c), title: 'Filter to ' + c,
          onclick: () => toggle('category', c),
        }, [h('span', { class: 'swatch', style: `background:${catColor(c)}` }), document.createTextNode(c)])
      )
    );

    if (!months.length) { host.replaceChildren(h('div', { class: 'empty', text: 'No orders match the current filters.' })); return; }

    const W = Math.max(host.clientWidth, 300), H = 300;
    const m = { l: 44, r: 12, t: 16, b: 28 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const maxTotal = Math.max(...months.map((x) => x.total));
    const step = niceStep(maxTotal / 4);
    const top = Math.ceil(maxTotal / step) * step;
    const y = (v) => m.t + ih - (v / top) * ih;
    const band = iw / months.length;
    const bw = Math.min(24, band * 0.6);
    const multiYear = months[0].key.slice(0, 4) !== months[months.length - 1].key.slice(0, 4);
    const peak = months.reduce((a, b) => (b.total > a.total ? b : a));

    const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Stacked column chart of monthly revenue by category' });
    for (let v = 0; v <= top + 1e-9; v += step) {
      el('line', { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: v === 0 ? 'var(--axis)' : 'var(--grid)', 'stroke-width': 1 }, svg);
      const t = el('text', { x: m.l - 8, y: y(v) + 4, 'text-anchor': 'end' }, svg);
      t.textContent = fmtCompact(v);
    }

    months.forEach((mo, i) => {
      const cx = m.l + band * i + band / 2, x = cx - bw / 2;
      const wash = el('rect', { x: m.l + band * i, y: m.t, width: band, height: ih, fill: 'var(--wash)', opacity: 0 }, svg);
      let cum = 0;
      const segs = present.filter((c) => mo.by[c] > 0);
      segs.forEach((c, j) => {
        const yt = y(cum + mo.by[c]);
        const yb = y(cum) - (j > 0 ? 2 : 0);
        const hgt = Math.max(1, yb - yt);
        if (j === segs.length - 1) {
          const r = Math.min(4, hgt);
          el('path', { d: `M${x},${yt + hgt} V${yt + r} Q${x},${yt} ${x + r},${yt} H${x + bw - r} Q${x + bw},${yt} ${x + bw},${yt + r} V${yt + hgt} Z`, fill: catColor(c) }, svg);
        } else {
          el('rect', { x, y: yt, width: bw, height: hgt, fill: catColor(c) }, svg);
        }
        cum += mo.by[c];
      });
      if (mo === peak) {
        const t = el('text', { x: cx, y: y(mo.total) - 6, 'text-anchor': 'middle', style: 'fill:var(--ink);font-weight:600' }, svg);
        t.textContent = fmtCompact(mo.total);
      }
      const lab = el('text', { x: cx, y: H - 8, 'text-anchor': 'middle' }, svg);
      lab.textContent = monthLabel(mo.key, multiYear);

      const band_ = el('rect', { class: 'band', x: m.l + band * i, y: m.t, width: band, height: ih + m.b - 4, tabindex: 0, 'aria-label': `${monthLabel(mo.key, true)}: ${fmtFull(mo.total)} revenue, ${mo.orders} orders` }, svg);
      const show = (px, py) => {
        wash.setAttribute('opacity', 1);
        showTip(monthLabel(mo.key, true), segs.map((c) => ({ name: c, value: fmtFull(mo.by[c]), color: catColor(c) })), fmtFull(mo.total), px, py);
      };
      const leave = () => { wash.setAttribute('opacity', 0); hideTip(); };
      band_.addEventListener('pointermove', (e) => show(e.clientX, e.clientY));
      band_.addEventListener('pointerleave', leave);
      band_.addEventListener('focus', () => { const b = band_.getBoundingClientRect(); show(b.left + b.width / 2, b.top + 40); });
      band_.addEventListener('blur', leave);
    });
    host.replaceChildren(svg);
  }

  function renderBars(sel, key, colorFn) {
    const host = $(sel);
    const rows = filtered(key); // cross-filter: ignore own dimension so alternatives stay visible
    const groups = groupSum(rows, key);
    if (!groups.length) { host.replaceChildren(h('div', { class: 'empty', text: 'No data for this range.' })); return; }
    const max = groups[0].value, total = sum(rows), selected = state[key];
    host.replaceChildren(
      ...groups.map((g) => {
        const w = (g.value / max) * 82;
        const row = h('button', {
          type: 'button', class: 'bar-row' + (selected !== 'All' ? (selected === g.name ? ' sel' : ' dim') : ''),
          'aria-pressed': String(selected === g.name),
          'aria-label': `${g.name}: ${fmtFull(g.value)} revenue, ${pct(g.value / total)} share. Click to filter.`,
          onclick: () => toggle(key, g.name),
        }, [
          h('span', { class: 'name', text: g.name }),
          h('span', { class: 'bar-track' }, [
            h('span', { class: 'bar', style: `width:${w}%;background:${colorFn(g.name)}` }),
            h('span', { class: 'bar-val', style: `left:calc(${w}% + 8px)`, text: fmtCompact(g.value) }),
          ]),
        ]);
        const show = (x, y) => showTip(g.name, [
          { name: 'Revenue', value: fmtFull(g.value) },
          { name: 'Share', value: pct(g.value / total) },
          { name: 'Orders', value: String(g.orders) },
        ], null, x, y);
        row.addEventListener('pointermove', (e) => show(e.clientX, e.clientY));
        row.addEventListener('pointerleave', hideTip);
        row.addEventListener('focus', () => { const b = row.getBoundingClientRect(); show(b.left + b.width / 2, b.top); });
        row.addEventListener('blur', hideTip);
        return row;
      })
    );
  }

  function renderTable() {
    let rows = filtered();
    if (state.q) rows = rows.filter((r) => COLS.some((c) => String(r[c.key]).toLowerCase().includes(state.q)));
    const { key, dir } = state.sort;
    rows = [...rows].sort((a, b) => (a[key] < b[key] ? -dir : a[key] > b[key] ? dir : 0));

    $('#tableSub').textContent = `${rows.length} order${rows.length === 1 ? '' : 's'}`;
    $('#thead').replaceChildren(
      ...COLS.map((c) =>
        h('th', { class: c.num ? 'num' : '', 'aria-sort': state.sort.key === c.key ? (dir === 1 ? 'ascending' : 'descending') : 'none' }, [
          h('button', {
            type: 'button', text: c.label + (state.sort.key === c.key ? (dir === 1 ? ' ↑' : ' ↓') : ''),
            onclick: () => { state.sort = { key: c.key, dir: state.sort.key === c.key ? -dir : 1 }; renderTable(); },
          }),
        ])
      )
    );
    $('#tbody').replaceChildren(
      ...rows.map((r) =>
        h('tr', {}, [
          h('td', { text: r.order_id }),
          h('td', { text: r.order_date }),
          h('td', {}, [h('span', { class: 'swatch', style: `background:${catColor(r.category)};margin-right:8px` }), document.createTextNode(r.category)]),
          h('td', { text: r.region }),
          h('td', { class: 'num', text: fmtFull(r.revenue) }),
        ])
      )
    );
    $('#tfoot').replaceChildren(
      h('td', { colspan: 4, text: 'Total' }),
      h('td', { class: 'num', text: fmtFull(sum(rows)) })
    );
  }

  // ---------- boot ----------
  async function boot() {
    wireControls();
    try {
      const res = await fetch('sales.csv', { cache: 'no-store' });
      if (!res.ok) throw new Error(res.status);
      setData(parseCSV(await res.text()), 'sales.csv');
    } catch {
      setData(parseCSV(FALLBACK_CSV), 'sales.csv (embedded copy; use Load CSV or serve over http to read the live file)');
    }
  }
  boot();
})();
