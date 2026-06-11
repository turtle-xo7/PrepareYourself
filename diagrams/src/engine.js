/* ════════════════════════════════════════════════════════════
   Prepare Yourself — diagram engine
   Draws SVG connector arrows between absolutely-positioned nodes
   and lays out sequence diagrams from a declarative spec.
   ════════════════════════════════════════════════════════════ */

const NS = 'http://www.w3.org/2000/svg';

function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}

function ensureWires(stage) {
  let svg = stage.querySelector('svg.wires');
  if (!svg) {
    svg = el('svg', { class: 'wires' });
    svg.classList.add('wires');
    stage.appendChild(svg);
    const defs = el('defs', {}, svg);
    for (const [id, color] of [['arr', '#475569'], ['arrTeal', '#0d9488'], ['arrRed', '#dc2626']]) {
      const m = el('marker', { id, viewBox: '0 0 10 10', refX: 8.5, refY: 5, markerWidth: 7.5, markerHeight: 7.5, orient: 'auto-start-reverse' }, defs);
      el('path', { d: 'M 0 1 L 9 5 L 0 9 Z', fill: color }, m);
    }
  }
  return svg;
}

function anchor(stage, node, side, frac = 0.5) {
  const s = stage.getBoundingClientRect();
  const r = node.getBoundingClientRect();
  const x = r.left - s.left, y = r.top - s.top, w = r.width, h = r.height;
  switch (side) {
    case 'left':   return { x, y: y + h * frac, dx: -1, dy: 0 };
    case 'right':  return { x: x + w, y: y + h * frac, dx: 1, dy: 0 };
    case 'top':    return { x: x + w * frac, y, dx: 0, dy: -1 };
    case 'bottom': return { x: x + w * frac, y: y + h, dx: 0, dy: 1 };
  }
}

function bezPoint(p0, c1, c2, p1, t) {
  const u = 1 - t;
  return {
    x: u*u*u*p0.x + 3*u*u*t*c1.x + 3*u*t*t*c2.x + t*t*t*p1.x,
    y: u*u*u*p0.y + 3*u*u*t*c1.y + 3*u*t*t*c2.y + t*t*t*p1.y,
  };
}

/* edges(stage, [ {from:'id', to:'id', fromSide, toSide, fromFrac, toFrac,
                   label, label2, at (0..1), dashed, tone, bend, chipClass} ]) */
function edges(stage, list) {
  const svg = ensureWires(stage);
  for (const e of list) {
    const a = anchor(stage, document.getElementById(e.from), e.fromSide || 'right', e.fromFrac ?? 0.5);
    const b = anchor(stage, document.getElementById(e.to), e.toSide || 'left', e.toFrac ?? 0.5);
    const dist = Math.hypot(b.x - a.x, b.y - a.y);
    const k = e.bend ?? Math.max(36, Math.min(110, dist * 0.38));
    const c1 = { x: a.x + a.dx * k, y: a.y + a.dy * k };
    const c2 = { x: b.x + b.dx * k, y: b.y + b.dy * k };
    const stroke = e.tone === 'teal' ? '#0d9488' : e.tone === 'red' ? '#dc2626' : '#475569';
    const marker = e.tone === 'teal' ? 'arrTeal' : e.tone === 'red' ? 'arrRed' : 'arr';
    el('path', {
      d: `M ${a.x} ${a.y} C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${b.x} ${b.y}`,
      fill: 'none', stroke, 'stroke-width': 2,
      'marker-end': `url(#${marker})`,
      ...(e.dashed ? { 'stroke-dasharray': '6 5' } : {}),
      'stroke-linecap': 'round', opacity: .9,
    }, svg);
    if (e.label) {
      const p = bezPoint(a, c1, c2, b, e.at ?? 0.5);
      const chip = document.createElement('div');
      chip.className = 'chip' + (e.chipClass ? ' ' + e.chipClass : '');
      chip.innerHTML = e.label2 ? `${e.label}<br>${e.label2}` : e.label;
      chip.style.left = (p.x + (e.dxLabel || 0)) + 'px';
      chip.style.top  = (p.y + (e.dyLabel || 0)) + 'px';
      stage.appendChild(chip);
    }
  }
}

/* ════════ Sequence diagrams ════════
   sequence(container, {
     actors: [{ id, label, sub, tone }],
     headH, rowH, top,
     phases: [{ label, fromRow, toRow }],
     steps:  [{ from, to, label, code, ret, gap }],   // self message: from === to
     activations: [{ actor, fromRow, toRow }],
   }) */
function sequence(box, spec) {
  const W = box.clientWidth;
  const n = spec.actors.length;
  const pad = 90;
  const xs = spec.actors.map((_, i) => pad + (W - 2 * pad) * (n === 1 ? .5 : i / (n - 1)));
  const headH = spec.headH ?? 56;
  const rowH = spec.rowH ?? 52;
  const top = spec.top ?? headH + 26;

  const rowY = r => top + r * rowH;

  /* phases (background bands) */
  for (const ph of (spec.phases || [])) {
    const d = document.createElement('div');
    d.className = 'phase';
    d.style.top = (rowY(ph.fromRow) - 30) + 'px';
    d.style.height = (rowY(ph.toRow) - rowY(ph.fromRow) + 44) + 'px';
    d.innerHTML = `<b>${ph.label}</b>`;
    box.appendChild(d);
  }

  /* lifelines + heads */
  const rows = spec.steps.reduce((acc, s) => acc + 1 + (s.gap || 0), 0);
  const bottom = rowY(rows) + 16;
  spec.actors.forEach((a, i) => {
    const line = document.createElement('div');
    line.className = 'lifeline';
    line.style.left = xs[i] + 'px';
    line.style.top = headH + 6 + 'px';
    line.style.height = (bottom - headH - 6) + 'px';
    box.appendChild(line);

    const h = document.createElement('div');
    h.className = 'lane-head tone-' + (a.tone || 'view');
    h.style.left = xs[i] + 'px';
    h.innerHTML = a.label + (a.sub ? `<small>${a.sub}</small>` : '');
    box.appendChild(h);
  });

  /* activations */
  for (const ac of (spec.activations || [])) {
    const i = spec.actors.findIndex(a => a.id === ac.actor);
    const d = document.createElement('div');
    d.className = 'activation';
    d.style.left = xs[i] + 'px';
    d.style.top = (rowY(ac.fromRow) - 14) + 'px';
    d.style.height = (rowY(ac.toRow) - rowY(ac.fromRow) + 28) + 'px';
    box.appendChild(d);
  }

  /* messages */
  const svg = ensureWires(box);
  let r = 0;
  for (const s of spec.steps) {
    const y = rowY(r);
    const i = spec.actors.findIndex(a => a.id === s.from);
    const j = spec.actors.findIndex(a => a.id === s.to);
    const x1 = xs[i], x2 = xs[j];
    if (i === j) { /* self message */
      const loop = 46;
      el('path', {
        d: `M ${x1 + 5} ${y - 12} C ${x1 + loop} ${y - 12}, ${x1 + loop} ${y + 12}, ${x1 + 5} ${y + 12}`,
        fill: 'none', stroke: '#475569', 'stroke-width': 2,
        'marker-end': 'url(#arr)', 'stroke-linecap': 'round',
        ...(s.ret ? { 'stroke-dasharray': '6 5' } : {}),
      }, svg);
    } else {
      const off = 6 * Math.sign(x2 - x1);
      el('line', {
        x1: x1 + off, y1: y, x2: x2 - off, y2: y,
        stroke: '#475569', 'stroke-width': 2,
        'marker-end': 'url(#arr)', 'stroke-linecap': 'round',
        ...(s.ret ? { 'stroke-dasharray': '6 5' } : {}),
      }, svg);
    }
    const chip = document.createElement('div');
    chip.className = 'msg' + (s.code ? ' code' : '') + (s.ret ? ' ret' : '');
    chip.textContent = s.label;
    chip.style.left = (i === j ? x1 + 64 : (x1 + x2) / 2) + 'px';
    chip.style.top = (y - 7) + 'px';
    if (i === j) chip.style.transform = 'translate(0,-50%)';
    box.appendChild(chip);
    r += 1 + (s.gap || 0);
  }
}

window.addEventListener('load', () => {
  if (window.draw) setTimeout(window.draw, 120); /* after fonts settle */
});
