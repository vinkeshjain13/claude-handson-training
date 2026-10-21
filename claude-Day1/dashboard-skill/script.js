'use strict';

/* ==========================================================================
   Sales analytics dashboard — vanilla JS, no dependencies.
   sales.csv is only ever read. Parsed records are frozen; filtering and
   sorting always work on derived copies.
   ========================================================================== */

const CSV_URL = 'sales.csv';
const REQUIRED_COLUMNS = ['order_id', 'order_date', 'category', 'region', 'revenue'];
const MONTH_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const PAGE_SIZE = 100;
const SVG_NS = 'http://www.w3.org/2000/svg';

const $ = (id) => document.getElementById(id);

const els = {
  summary: $('data-summary'),
  region: $('region-filter'),
  category: $('category-filter'),
  reset: $('reset-filters'),
  status: $('filter-status'),
  notice: $('notice'),
  kpiRevenue: $('kpi-revenue'),
  kpiRevenueSub: $('kpi-revenue-sub'),
  kpiOrders: $('kpi-orders'),
  kpiAov: $('kpi-aov'),
  kpiTop: $('kpi-top'),
  kpiTopSub: $('kpi-top-sub'),
  trend: $('trend-chart'),
  trendSub: $('trend-sub'),
  categoryChart: $('category-chart'),
  categorySub: $('category-sub'),
  ordersSub: $('orders-sub'),
  table: $('orders-table'),
  body: $('orders-body'),
  foot: $('orders-foot'),
  empty: $('orders-empty'),
  emptyTitle: $('empty-title'),
  emptyText: $('empty-text'),
  emptyActions: $('empty-actions'),
  more: $('orders-more'),
  showMore: $('show-more'),
};

/* ---------- App state ---------- */
let orders = [];          // frozen, validated source records
let months = [];          // contiguous month keys spanning the whole dataset
let categories = [];      // every category in the dataset, sorted
let introPlayed = false;  // the trend line draws in once, on first paint
let refocusCategory = null; // keeps keyboard focus on a bar after a filter redraw
let multiYear = false;
let fractional = false;   // does any revenue value carry paise?
let currentRows = [];
const state = { region: '', category: '', sortKey: 'date', sortDir: 'desc', limit: PAGE_SIZE };

/* ---------- Formatting (INR, Indian digit grouping) ---------- */
let inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
const fmtINR = (v) => inr.format(v);
const fmtInt = (v) => new Intl.NumberFormat('en-IN').format(v);

function trimNum(n) { return String(Number(n.toFixed(2))); }
function compactINR(v) {
  const a = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (a >= 1e7) return `${sign}₹${trimNum(a / 1e7)}Cr`;
  if (a >= 1e5) return `${sign}₹${trimNum(a / 1e5)}L`;
  if (a >= 1e3) return `${sign}₹${trimNum(a / 1e3)}K`;
  return `${sign}₹${trimNum(a)}`;
}

const pad2 = (n) => String(n).padStart(2, '0');
function monthLabel(key, long) {
  const [y, m] = key.split('-').map(Number);
  const name = MONTH_SHORT[m - 1];
  if (long) return `${name} ${y}`;
  return multiYear ? `${name} ’${pad2(y % 100)}` : name;
}
function dateLabel(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return `${pad2(d)} ${MONTH_SHORT[m - 1]} ${y}`;
}

/* ---------- CSV parsing & validation ---------- */
function parseCSV(text) {
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else quoted = false;
      } else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      rows.push(row); row = [];
    } else field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => !(r.length === 1 && r[0].trim() === ''));
}

function isRealDate(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return false;
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const dt = new Date(Date.UTC(y, mo - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === mo - 1 && dt.getUTCDate() === d;
}

function buildOrders(rows) {
  if (!rows.length) throw new Error('sales.csv is empty.');
  const header = rows[0].map((h) => h.trim().toLowerCase());
  const missing = REQUIRED_COLUMNS.filter((c) => !header.includes(c));
  if (missing.length) throw new Error(`sales.csv is missing column(s): ${missing.join(', ')}.`);
  const col = Object.fromEntries(REQUIRED_COLUMNS.map((c) => [c, header.indexOf(c)]));

  const valid = [];
  const skipped = [];
  const seen = new Set();
  rows.slice(1).forEach((r, i) => {
    const line = i + 2;
    const get = (c) => (r[col[c]] ?? '').trim();
    const id = get('order_id');
    const date = get('order_date');
    const category = get('category');
    const region = get('region');
    const revenueText = get('revenue');
    let reason = null;
    if (!id) reason = 'missing order_id';
    else if (seen.has(id)) reason = `duplicate order_id ${id}`;
    else if (!isRealDate(date)) reason = `invalid order_date "${date}"`;
    else if (!category) reason = 'missing category';
    else if (!region) reason = 'missing region';
    else if (!/^-?\d+(\.\d+)?$/.test(revenueText)) reason = `invalid revenue "${revenueText}"`;
    if (reason) { skipped.push({ line, reason }); return; }
    seen.add(id);
    valid.push(Object.freeze({
      id, date, month: date.slice(0, 7), category, region, revenue: Number(revenueText),
    }));
  });
  return { valid, skipped };
}

/* ---------- Aggregation ---------- */
function aggregateBy(rows, keyFn) {
  const map = new Map();
  for (const o of rows) {
    const k = keyFn(o);
    const a = map.get(k) || { revenue: 0, orders: 0 };
    a.revenue += o.revenue;
    a.orders += 1;
    map.set(k, a);
  }
  return map;
}

function monthRange(rows) {
  const keys = rows.map((o) => o.month).sort();
  const [y0, m0] = keys[0].split('-').map(Number);
  const [y1, m1] = keys[keys.length - 1].split('-').map(Number);
  const out = [];
  for (let y = y0, m = m0; y < y1 || (y === y1 && m <= m1); m === 12 ? (y++, m = 1) : m++) {
    out.push(`${y}-${pad2(m)}`);
  }
  return out;
}

function niceScale(maxVal) {
  if (!(maxVal > 0)) return { max: 1000, step: 250 };
  const raw = maxVal / 4;
  const pow = 10 ** Math.floor(Math.log10(raw));
  const n = raw / pow;
  const nice = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10;
  const step = nice * pow;
  return { max: Math.ceil(maxVal / step - 1e-9) * step, step };
}

function filteredRows() {
  return orders.filter((o) =>
    (!state.region || o.region === state.region) && (!state.category || o.category === state.category));
}

function regionRows() {
  return orders.filter((o) => !state.region || o.region === state.region);
}

function scopeText() {
  const { region, category } = state;
  if (region && category) return `${category} in ${region} region`;
  if (region) return `${region} region`;
  return category || 'All regions and categories';
}

/* ---------- SVG + tooltip helpers ---------- */
function svgEl(tag, attrs = {}, parent) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}

const measureCtx = document.createElement('canvas').getContext('2d');
function textWidth(text, size, weight = 400) {
  measureCtx.font = `${weight} ${size}px ${getComputedStyle(document.body).fontFamily}`;
  return measureCtx.measureText(text).width;
}

function makeTooltip(host) {
  const wrap = host.parentElement;
  const tip = document.createElement('div');
  tip.className = 'tooltip';
  tip.hidden = true;
  wrap.appendChild(tip);
  const api = {
    reset: null,
    show(ax, ay, title, rows) {
      tip.replaceChildren();
      const t = document.createElement('div');
      t.className = 'tt-title';
      t.textContent = title;
      tip.appendChild(t);
      for (const r of rows) {
        const row = document.createElement('div');
        row.className = 'tt-row';
        const key = document.createElement('span');
        key.className = r.key ? 'tt-key' : 'tt-key none';
        const label = document.createElement('span');
        label.className = 'tt-label';
        label.textContent = r.label;
        const value = document.createElement('span');
        value.className = 'tt-value';
        value.textContent = r.value;
        row.append(key, label, value);
        tip.appendChild(row);
      }
      tip.hidden = false;
      const w = wrap.clientWidth;
      const tw = tip.offsetWidth;
      const th = tip.offsetHeight;
      let left = ax + 14;
      if (left + tw > w) left = ax - tw - 14;
      left = Math.max(0, Math.min(left, w - tw));
      const top = Math.max(0, Math.min(ay - th / 2, wrap.clientHeight - th));
      tip.style.left = `${left}px`;
      tip.style.top = `${top}px`;
    },
    hide() {
      tip.hidden = true;
      if (api.reset) api.reset();
    },
  };
  return api;
}

const tips = { trend: makeTooltip(els.trend), category: makeTooltip(els.categoryChart) };

document.addEventListener('pointerdown', (e) => {
  if (!e.target.closest || !e.target.closest('.hit-col, .bar-row')) {
    tips.trend.hide();
    tips.category.hide();
  }
});

function emptyChart(host, message) {
  const box = document.createElement('div');
  box.className = 'empty';
  const title = document.createElement('p');
  title.className = 'empty-title';
  title.textContent = 'No data to chart';
  const sub = document.createElement('p');
  sub.className = 'subtle';
  sub.textContent = message;
  box.append(title, sub);
  host.replaceChildren(box);
}

/* ---------- Monthly revenue (line + area) ---------- */
function drawTrend(rows) {
  const host = els.trend;
  tips.trend.hide();
  if (!rows.length) {
    emptyChart(host, 'No orders match the selected filters.');
    return;
  }
  const byMonth = aggregateBy(rows, (o) => o.month);
  const series = months.map((k) => ({ key: k, ...(byMonth.get(k) || { revenue: 0, orders: 0 }) }));

  const W = Math.max(260, Math.round(host.clientWidth));
  const small = W < 520;
  const H = small ? 240 : 300;
  const M = { top: 30, right: small ? 16 : 24, bottom: 30, left: small ? 50 : 60 };
  const iw = W - M.left - M.right;
  const ih = H - M.top - M.bottom;
  const band = iw / series.length;
  const { max, step } = niceScale(Math.max(...series.map((s) => s.revenue)));
  const x = (i) => M.left + (i + 0.5) * band;
  const y = (v) => M.top + ih - (v / max) * ih;

  const svg = svgEl('svg', {
    viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'group',
    'aria-label': 'Monthly revenue line chart',
  });
  if (!introPlayed) { svg.classList.add('intro'); introPlayed = true; }

  for (let t = 0; t <= max + step / 2; t += step) {
    svgEl('line', { class: t === 0 ? 'baseline' : 'gridline', x1: M.left, x2: W - M.right, y1: y(t), y2: y(t) }, svg);
    const label = svgEl('text', { class: 'tick-label', x: M.left - 8, y: y(t), 'text-anchor': 'end', dy: '0.32em' }, svg);
    label.textContent = compactINR(t);
  }

  const widest = Math.max(...series.map((s) => textWidth(monthLabel(s.key), 12)));
  const every = Math.max(1, Math.ceil((widest + 12) / band));
  series.forEach((s, i) => {
    if ((series.length - 1 - i) % every) return;
    const label = svgEl('text', { class: 'tick-label', x: x(i), y: H - 8, 'text-anchor': 'middle' }, svg);
    label.textContent = monthLabel(s.key);
  });

  const pts = series.map((s, i) => [x(i), y(s.revenue)]);
  const base = y(0);
  svgEl('path', {
    class: 'area',
    d: `M${pts[0][0]},${base} ${pts.map((p) => `L${p[0]},${p[1]}`).join(' ')} L${pts[pts.length - 1][0]},${base} Z`,
  }, svg);

  const crosshair = svgEl('line', { class: 'crosshair', y1: M.top, y2: M.top + ih, visibility: 'hidden' }, svg);
  const halo = svgEl('circle', { class: 'halo', r: 11, visibility: 'hidden' }, svg);

  svgEl('path', { class: 'line', pathLength: 1, d: pts.map((p, i) => `${i ? 'L' : 'M'}${p[0]},${p[1]}`).join(' ') }, svg);
  pts.forEach((p) => {
    svgEl('circle', { class: 'dot-ring', cx: p[0], cy: p[1], r: 6 }, svg);
    svgEl('circle', { class: 'dot', cx: p[0], cy: p[1], r: 4 }, svg);
  });

  // Direct label on the latest month only; every other value lives in the tooltip.
  const last = series[series.length - 1];
  const prev = series[series.length - 2];
  const [lx, ly] = pts[pts.length - 1];
  const below = prev && last.revenue < prev.revenue && ly + 22 < base;
  const endLabel = svgEl('text', {
    class: 'data-label', x: Math.min(lx + 6, W - 4), y: below ? ly + 20 : ly - 12, 'text-anchor': 'end',
  }, svg);
  endLabel.textContent = fmtINR(last.revenue);

  const activate = (i) => {
    const s = series[i];
    crosshair.setAttribute('x1', x(i));
    crosshair.setAttribute('x2', x(i));
    crosshair.setAttribute('visibility', 'visible');
    halo.setAttribute('cx', x(i));
    halo.setAttribute('cy', y(s.revenue));
    halo.setAttribute('visibility', 'visible');
    const rowsOut = s.orders
      ? [{ key: true, label: 'Revenue', value: fmtINR(s.revenue) }, { label: 'Orders', value: fmtInt(s.orders) }]
      : [{ label: 'No orders this month', value: '' }];
    tips.trend.show(x(i), y(s.revenue), monthLabel(s.key, true), rowsOut);
  };
  tips.trend.reset = () => {
    crosshair.setAttribute('visibility', 'hidden');
    halo.setAttribute('visibility', 'hidden');
  };

  series.forEach((s, i) => {
    const g = svgEl('g', {
      class: 'hit-col', tabindex: 0, role: 'img',
      'aria-label': `${monthLabel(s.key, true)}: ${s.orders ? `${fmtINR(s.revenue)} from ${s.orders} orders` : 'no orders'}`,
    }, svg);
    svgEl('rect', { class: 'hit', x: M.left + i * band, y: M.top - 8, width: band, height: ih + 8 }, g);
    g.addEventListener('pointerenter', () => activate(i));
    g.addEventListener('pointermove', () => activate(i));
    g.addEventListener('pointerleave', (e) => { if (e.pointerType !== 'touch') tips.trend.hide(); });
    g.addEventListener('focus', () => activate(i));
    g.addEventListener('blur', () => tips.trend.hide());
  });

  host.replaceChildren(svg);
  host.dataset.drawnWidth = String(Math.round(host.clientWidth));
}

/* ---------- Revenue by category (horizontal bars) ---------- */
function drawCategories(rows) {
  const host = els.categoryChart;
  tips.category.hide();
  if (!rows.length) {
    emptyChart(host, 'No orders match the selected filters.');
    return;
  }
  const byCategory = aggregateBy(rows, (o) => o.category);
  const groups = categories
    .map((name) => ({ name, ...(byCategory.get(name) || { revenue: 0, orders: 0 }) }))
    .sort((a, b) => b.revenue - a.revenue || a.name.localeCompare(b.name));
  const total = groups.reduce((s, g) => s + g.revenue, 0);
  const maxVal = Math.max(...groups.map((g) => g.revenue));

  const W = Math.max(260, Math.round(host.clientWidth));
  const rowH = 48;
  const barH = 20;
  const H = groups.length * rowH + 4;
  const labelW = Math.min(
    Math.ceil(Math.max(...groups.map((g) => textWidth(g.name, 14)))) + 16,
    Math.round(W * 0.42));
  const valueW = Math.ceil(Math.max(...groups.map((g) => textWidth(fmtINR(g.revenue), 13, 650)))) + 16;
  const barArea = Math.max(40, W - labelW - valueW);

  const svg = svgEl('svg', {
    viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'group', 'aria-label': 'Revenue by category bar chart',
  });
  svgEl('line', { class: 'baseline', x1: labelW, x2: labelW, y1: 0, y2: H - 4 }, svg);

  groups.forEach((g, i) => {
    const top = i * rowH;
    const cy = top + (rowH - 4) / 2;
    const share = total > 0 ? (g.revenue / total) * 100 : 0;
    const selected = state.category === g.name;
    const filterable = g.orders > 0;
    const facts = `${g.name}: ${fmtINR(g.revenue)} from ${g.orders} orders, ${share.toFixed(1)}% of revenue`;
    const classes = ['bar-row'];
    if (selected) classes.push('is-selected');
    else if (state.category) classes.push('is-dim');
    if (!filterable) classes.push('is-empty');
    const row = svgEl('g', {
      class: classes.join(' '), tabindex: 0,
      ...(filterable
        ? { role: 'button', 'aria-pressed': String(selected), 'aria-label': `${facts}. ${selected ? 'Selected. Activate to clear the category filter' : 'Activate to filter by this category'}` }
        : { role: 'img', 'aria-label': facts }),
    }, svg);
    row.dataset.name = g.name;
    svgEl('rect', { class: 'row-wash', x: 0, y: top, width: W, height: rowH - 4, rx: 6 }, row);

    const name = svgEl('text', { class: 'cat-label', x: 4, y: cy, dy: '0.32em' }, row);
    name.textContent = g.name;

    const w = maxVal > 0 ? (g.revenue / maxVal) * barArea : 0;
    const x0 = labelW;
    const by = cy - barH / 2;
    if (w > 0) {
      const r = Math.min(4, w, barH / 2);
      svgEl('path', {
        class: 'bar',
        d: `M${x0},${by} H${x0 + w - r} a${r},${r} 0 0 1 ${r},${r} V${by + barH - r} a${r},${r} 0 0 1 ${-r},${r} H${x0} Z`,
      }, row);
    }
    const val = svgEl('text', { class: 'data-label', x: x0 + w + 8, y: cy, dy: '0.32em' }, row);
    val.textContent = fmtINR(g.revenue);

    const show = () => tips.category.show(x0 + w, cy, g.name, [
      { key: true, label: 'Revenue', value: fmtINR(g.revenue) },
      { label: 'Orders', value: fmtInt(g.orders) },
      { label: 'Share of revenue', value: `${share.toFixed(1)}%` },
    ]);
    row.addEventListener('pointerenter', show);
    row.addEventListener('pointermove', show);
    row.addEventListener('pointerleave', (e) => { if (e.pointerType !== 'touch') tips.category.hide(); });
    row.addEventListener('focus', show);
    row.addEventListener('blur', () => tips.category.hide());
    if (filterable) {
      const toggle = () => setCategory(selected ? '' : g.name);
      row.addEventListener('click', toggle);
      row.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        e.preventDefault();
        refocusCategory = g.name;
        toggle();
      });
    }
  });

  host.replaceChildren(svg);
  host.dataset.drawnWidth = String(Math.round(host.clientWidth));
  if (refocusCategory) {
    const again = [...svg.querySelectorAll('.bar-row')].find((r) => r.dataset.name === refocusCategory);
    refocusCategory = null;
    if (again) again.focus();
  }
}

/* ---------- KPIs ---------- */
function renderKpis(rows) {
  const revenue = rows.reduce((s, o) => s + o.revenue, 0);
  els.kpiRevenue.textContent = fmtINR(revenue);
  els.kpiRevenueSub.textContent = scopeText();
  els.kpiOrders.textContent = fmtInt(rows.length);
  els.kpiAov.textContent = rows.length ? fmtINR(revenue / rows.length) : '—';

  if (!rows.length) {
    els.kpiTop.textContent = '—';
    els.kpiTopSub.textContent = 'No orders in this selection';
    return;
  }
  const top = [...aggregateBy(rows, (o) => o.category)]
    .sort((a, b) => b[1].revenue - a[1].revenue || a[0].localeCompare(b[0]))[0];
  els.kpiTop.textContent = top[0];
  const share = revenue > 0 ? `, ${((top[1].revenue / revenue) * 100).toFixed(1)}% of revenue` : '';
  els.kpiTopSub.textContent = `${fmtINR(top[1].revenue)}${share}`;
}

/* ---------- Orders table ---------- */
function sortedRows(rows) {
  const dir = state.sortDir === 'asc' ? 1 : -1;
  const key = state.sortKey;
  return [...rows].sort((a, b) => {
    let c;
    if (key === 'revenue') c = a.revenue - b.revenue;
    else c = String(a[key]).localeCompare(String(b[key]), 'en', { numeric: true });
    return c * dir || a.id.localeCompare(b.id, 'en', { numeric: true });
  });
}

function cell(text, cls) {
  const td = document.createElement('td');
  td.textContent = text;
  if (cls) td.className = cls;
  return td;
}

function renderTable(rows) {
  const empty = rows.length === 0;
  els.empty.hidden = !empty;
  els.table.parentElement.hidden = empty;
  els.body.replaceChildren();
  els.foot.replaceChildren();
  els.more.hidden = true;
  els.ordersSub.textContent = `${scopeText()}: ${fmtInt(rows.length)} of ${fmtInt(orders.length)} orders`;
  if (empty) { renderEmptyState(); return; }

  const sorted = sortedRows(rows);
  const visible = sorted.slice(0, state.limit);
  const frag = document.createDocumentFragment();
  for (const o of visible) {
    const tr = document.createElement('tr');
    tr.append(cell(o.id), cell(dateLabel(o.date)), cell(o.category), cell(o.region), cell(fmtINR(o.revenue), 'num'));
    frag.appendChild(tr);
  }
  els.body.appendChild(frag);

  const total = rows.reduce((s, o) => s + o.revenue, 0);
  const tr = document.createElement('tr');
  const label = cell(`Total, ${fmtInt(rows.length)} order${rows.length === 1 ? '' : 's'}`);
  label.colSpan = 4;
  tr.append(label, cell(fmtINR(total), 'num'));
  els.foot.appendChild(tr);

  if (sorted.length > visible.length) {
    els.more.hidden = false;
    els.showMore.textContent = `Show more orders (${fmtInt(sorted.length - visible.length)} remaining)`;
  }
}

function renderEmptyState() {
  els.emptyTitle.textContent = `No orders for ${scopeText()}`;
  els.emptyText.textContent = 'No order in sales.csv matches this combination. Widen the selection to see orders again.';
  els.emptyActions.replaceChildren();
  const actions = [];
  if (state.region) actions.push(['Show all regions', () => setFilter('region', '')]);
  if (state.category) actions.push(['Show all categories', () => setFilter('category', '')]);
  for (const [text, run] of actions) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'btn';
    b.textContent = text;
    b.addEventListener('click', run);
    els.emptyActions.appendChild(b);
  }
}

function updateSortHeaders() {
  els.table.querySelectorAll('thead th').forEach((th) => {
    th.setAttribute('aria-sort', th.dataset.key === state.sortKey
      ? (state.sortDir === 'asc' ? 'ascending' : 'descending') : 'none');
  });
}

/* ---------- Render pipeline ---------- */
function drawCharts() {
  drawTrend(currentRows);
  drawCategories(regionRows());
}

function render() {
  const rows = filteredRows();
  currentRows = rows;
  els.trendSub.textContent = `${scopeText()}, revenue by month`;
  els.categorySub.textContent = `${state.region ? `${state.region} region` : 'All regions'}. Select a bar to filter by category.`;
  els.reset.disabled = !(state.region || state.category);
  els.status.textContent = rows.length
    ? `Showing ${fmtInt(rows.length)} of ${fmtInt(orders.length)} orders`
    : 'No orders match the selected filters';
  updateSegments();
  renderKpis(rows);
  drawCharts();
  renderTable(rows);
}

/* ---------- Filters ---------- */
function setFilter(key, value) {
  state[key] = value;
  state.limit = PAGE_SIZE;
  render();
  focusFilter(key);
}

function setCategory(value) {
  state.category = value;
  state.limit = PAGE_SIZE;
  render();
}

function focusFilter(key) {
  const host = key === 'region' ? els.region : els.category;
  const target = host.querySelector('[aria-pressed="true"]:not(:disabled)') || host.querySelector('button');
  if (target) target.focus();
}

function resetFilters() {
  state.region = '';
  state.category = '';
  state.limit = PAGE_SIZE;
  render();
  focusFilter('region');
}

function buildSegment(host, key, values) {
  host.replaceChildren();
  ['', ...values].forEach((value) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.dataset.value = value;
    const label = document.createElement('span');
    label.textContent = value || 'All';
    const count = document.createElement('span');
    count.className = 'seg-count';
    b.append(label, count);
    b.addEventListener('click', () => { state[key] = value; state.limit = PAGE_SIZE; render(); });
    host.appendChild(b);
  });
}

// Each option's count respects the other filter, so a zero means "this choice would show nothing".
function updateSegments() {
  for (const [key, host, other] of [['region', els.region, 'category'], ['category', els.category, 'region']]) {
    const base = orders.filter((o) => !state[other] || o[other] === state[other]);
    host.querySelectorAll('button').forEach((b) => {
      const value = b.dataset.value;
      const n = value ? base.filter((o) => o[key] === value).length : base.length;
      const on = state[key] === value;
      b.setAttribute('aria-pressed', String(on));
      b.disabled = n === 0 && !on;
      b.setAttribute('aria-label', `${value || 'All'}, ${fmtInt(n)} order${n === 1 ? '' : 's'}`);
      b.querySelector('.seg-count').textContent = fmtInt(n);
    });
  }
}

/* ---------- Wiring ---------- */

function showNotice(build) {
  els.notice.replaceChildren();
  build(els.notice);
  els.notice.hidden = false;
}

function wireEvents() {
  els.reset.addEventListener('click', resetFilters);
  els.showMore.addEventListener('click', () => { state.limit += PAGE_SIZE; renderTable(currentRows); });

  els.table.querySelectorAll('thead th').forEach((th) => {
    th.querySelector('button').addEventListener('click', () => {
      const key = th.dataset.key;
      if (state.sortKey === key) state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
      else { state.sortKey = key; state.sortDir = key === 'date' || key === 'revenue' ? 'desc' : 'asc'; }
      updateSortHeaders();
      renderTable(currentRows);
    });
  });

  let frame = 0;
  const observer = new ResizeObserver(() => {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => {
      const stale = [els.trend, els.categoryChart].some(
        (h) => h.dataset.drawnWidth && h.dataset.drawnWidth !== String(Math.round(h.clientWidth)));
      if (stale) drawCharts();
    });
  });
  observer.observe(els.trend);
  observer.observe(els.categoryChart);
}

async function init() {
  let text;
  try {
    const res = await fetch(CSV_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    text = await res.text();
  } catch (err) {
    els.summary.textContent = 'Sales data could not be loaded.';
    showNotice((n) => {
      n.append(`Could not load ${CSV_URL} (${err.message}). Browsers block file:// reads — serve this folder over HTTP, e.g. `);
      const code = document.createElement('code');
      code.textContent = 'python3 -m http.server 8000';
      n.append(code, ' and open http://localhost:8000.');
    });
    emptyChart(els.trend, 'Waiting for sales data.');
    emptyChart(els.categoryChart, 'Waiting for sales data.');
    return;
  }

  let parsed;
  try {
    parsed = buildOrders(parseCSV(text));
  } catch (err) {
    els.summary.textContent = 'Sales data could not be read.';
    showNotice((n) => { n.textContent = err.message; });
    emptyChart(els.trend, 'Waiting for sales data.');
    emptyChart(els.categoryChart, 'Waiting for sales data.');
    return;
  }

  orders = Object.freeze(parsed.valid);
  if (parsed.skipped.length) {
    showNotice((n) => {
      n.append(`${parsed.skipped.length} row${parsed.skipped.length === 1 ? '' : 's'} in ${CSV_URL} could not be used and ${parsed.skipped.length === 1 ? 'is' : 'are'} excluded from every figure (the file itself is untouched):`);
      const ul = document.createElement('ul');
      parsed.skipped.slice(0, 5).forEach((s) => {
        const li = document.createElement('li');
        li.textContent = `Line ${s.line}: ${s.reason}`;
        ul.appendChild(li);
      });
      if (parsed.skipped.length > 5) {
        const li = document.createElement('li');
        li.textContent = `…and ${parsed.skipped.length - 5} more`;
        ul.appendChild(li);
      }
      n.appendChild(ul);
    });
  }

  if (!orders.length) {
    els.summary.textContent = 'No valid orders found in sales.csv.';
    emptyChart(els.trend, 'sales.csv has no valid orders.');
    emptyChart(els.categoryChart, 'sales.csv has no valid orders.');
    return;
  }

  fractional = orders.some((o) => !Number.isInteger(o.revenue));
  if (fractional) {
    inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  months = monthRange(orders);
  multiYear = months[0].slice(0, 4) !== months[months.length - 1].slice(0, 4);

  const dates = orders.map((o) => o.date).sort();
  els.summary.textContent =
    `${fmtInt(orders.length)} orders from ${dateLabel(dates[0])} to ${dateLabel(dates[dates.length - 1])}. Amounts in INR.`;
  categories = [...new Set(orders.map((o) => o.category))].sort();
  buildSegment(els.region, 'region', [...new Set(orders.map((o) => o.region))].sort());
  buildSegment(els.category, 'category', categories);

  wireEvents();
  updateSortHeaders();
  render();
}

init();
