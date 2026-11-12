/* Geographic network map (equirectangular, stylised land). Operates on backend graph data only. */
const MAP = {W: 1000, H: 520, LAT_TOP: 80, LAT_BOT: -58};
const px = lon => (lon + 180) / 360 * MAP.W;
const py = lat => (MAP.LAT_TOP - lat) / (MAP.LAT_TOP - MAP.LAT_BOT) * MAP.H;
const LAND = [
  [[-168,66],[-140,70],[-95,72],[-80,68],[-62,60],[-55,50],[-67,44],[-76,35],[-81,25],[-97,26],[-97,18],[-88,15],[-80,8],[-92,14],[-105,20],[-117,32],[-124,40],[-125,49],[-140,60]],
  [[-80,8],[-62,10],[-50,0],[-35,-6],[-40,-22],[-48,-28],[-58,-38],[-66,-46],[-72,-54],[-75,-40],[-71,-18],[-81,-5]],
  [[-10,36],[-9,43],[-2,48],[-5,52],[5,58],[10,63],[25,70],[40,68],[40,55],[30,46],[28,41],[20,38],[12,38],[3,43]],
  [[-17,21],[-10,35],[10,37],[32,31],[43,12],[51,11],[40,-15],[33,-27],[20,-35],[12,-18],[9,4],[-8,5],[-17,14]],
  [[28,41],[40,55],[40,68],[100,77],[140,72],[180,68],[160,55],[142,46],[130,35],[122,30],[120,22],[108,16],[105,9],[100,2],[98,12],[92,22],[80,8],[73,20],[66,25],[57,25],[52,15],[43,13],[35,30]],
  [[114,-22],[130,-12],[142,-11],[153,-26],[147,-38],[135,-35],[115,-34]],
  [[130,31],[141,36],[142,43],[138,38]], [[-10,50],[-5,58],[2,53],[-4,51]]];
const KIND = {distribution_center: ['Distribution center', '#0d2b45'], warehouse: ['Warehouse', '#2f7f8f'], destination: ['Destination', '#d98200'], city: ['City', '#6b7f8e']};

function wrapSegments(a, b) {
  let [x1, y1] = a, [x2, y2] = b;
  if (Math.abs(x1 - x2) <= MAP.W / 2) return [[x1, y1, x2, y2]];
  if (x1 > x2) [x1, y1, x2, y2] = [x2, y2, x1, y1];
  const t = x1 / (x1 + MAP.W - x2), ye = y1 + (y2 - y1) * t;
  return [[x1, y1, 0, ye], [MAP.W, ye, x2, y2]];
}
const segPath = segs => segs.map(s => `M${s[0].toFixed(1)} ${s[1].toFixed(1)}L${s[2].toFixed(1)} ${s[3].toFixed(1)}`).join('');

function mapShape(kind, x, y, r, extra) {
  const c = KIND[kind][1];
  if (kind === 'distribution_center') return `<rect x="${x - r}" y="${y - r}" width="${2 * r}" height="${2 * r}" transform="rotate(45 ${x} ${y})" fill="${c}" ${extra}/>`;
  if (kind === 'warehouse') return `<rect x="${x - r}" y="${y - r}" width="${2 * r}" height="${2 * r}" fill="${c}" ${extra}/>`;
  if (kind === 'destination') return `<circle cx="${x}" cy="${y}" r="${r}" fill="#fff" stroke="${c}" stroke-width="2.5" ${extra}/>`;
  return `<circle cx="${x}" cy="${y}" r="${r}" fill="${c}" ${extra}/>`;
}

/* opts: {sel:{source,target}, route:resultObj|null, showWeights, metric, onPick(code)} */
function drawMap(el, graph, opts = {}) {
  const locs = graph.locations, by = Object.fromEntries(locs.map(l => [l.code, l]));
  const pos = c => [px(by[c].lon), py(by[c].lat)], big = locs.length > 80, col = {cost: 'cost_usd', time: 'time_hours', distance: 'distance_km'}[opts.metric || 'cost'];
  const pairs = new Map();
  graph.routes.forEach(r => { const k = [r.src, r.dst].sort().join('|'); (pairs.get(k) || pairs.set(k, []).get(k)).push(r); });
  const routeEdges = new Set((opts.route?.path || []).slice(1).map((c, i) => opts.route.path[i] + '>' + c));
  const altEdges = new Set((opts.route?.alternatives || []).flatMap(a => a.path.slice(1).map((c, i) => a.path[i] + '>' + c)));
  const onRoute = new Set(opts.route?.path || []);
  let svg = `<rect width="${MAP.W}" height="${MAP.H}" fill="var(--sea)"/>`;
  for (let lon = -150; lon <= 150; lon += 30) svg += `<line x1="${px(lon)}" x2="${px(lon)}" y2="${MAP.H}" stroke="#bcd2e0" stroke-width=".6"/>`;
  for (let lat = -40; lat <= 60; lat += 20) svg += `<line y1="${py(lat)}" y2="${py(lat)}" x2="${MAP.W}" stroke="#bcd2e0" stroke-width=".6"/>`;
  LAND.forEach(p => svg += `<polygon points="${p.map(q => px(q[0]).toFixed(1) + ',' + py(q[1]).toFixed(1)).join(' ')}" fill="var(--land)" stroke="#c9c6b8" stroke-width=".8"/>`);
  let base = '', labels = '', hi = '';
  pairs.forEach(rs => {
    const a = pos(rs[0].src), b = pos(rs[0].dst), neg = rs.some(r => r[col] < 0), segs = wrapSegments(a, b);
    base += `<path d="${segPath(segs)}" stroke="${neg ? '#c0392b' : '#6f8799'}" stroke-width="${big ? .5 : 1.3}" ${neg ? 'stroke-dasharray="5 3"' : ''} opacity="${big ? .55 : .8}" fill="none"><title>${rs.map(r => `${r.src}\u2192${r.dst} (${r.mode}): ${fmt(r[col], 1)}`).join(' | ')}</title></path>`;
    if (opts.showWeights && !big) {
      const s0 = segs[0], mx = (s0[0] + s0[2]) / 2, my = (s0[1] + s0[3]) / 2;
      labels += `<text x="${mx}" y="${my - 3}" text-anchor="middle" font-size="9" fill="${neg ? '#c0392b' : '#33495a'}" stroke="#fff" stroke-width="2.5" paint-order="stroke">${rs.map(r => niceNum(r[col])).join('/')}</text>`;
    }
  });
  const drawSet = (set, color, width, dash) => graph.routes.filter(r => set.has(r.src + '>' + r.dst)).map(r =>
    `<path d="${segPath(wrapSegments(pos(r.src), pos(r.dst)))}" stroke="${color}" stroke-width="${width}" ${dash ? 'stroke-dasharray="8 5"' : ''} fill="none" stroke-linecap="round"/>`).join('');
  hi += drawSet(altEdges, '#6f9bd1', 2.4, true) + drawSet(routeEdges, opts.route?.algorithm === 'bellman_ford' ? '#b0306e' : '#2563b8', 4.2, false);
  let nodes = '';
  locs.forEach(l => {
    const [x, y] = pos(l.code), isS = opts.sel?.source === l.code, isT = opts.sel?.target === l.code, active = isS || isT || onRoute.has(l.code);
    const r = big ? 3 : (active ? 8 : 6.5);
    nodes += `<g class="node" data-code="${esc(l.code)}">${mapShape(l.kind, x, y, r, active ? 'stroke="#fff" stroke-width="2"' : (big ? '' : 'stroke="#fff" stroke-width="1.2"'))}
      ${isS || isT ? `<circle cx="${x}" cy="${y}" r="${r + 5}" fill="none" stroke="${isS ? '#12805c' : '#c0392b'}" stroke-width="2.5"/>` : ''}
      ${(!big || active) ? `<text x="${x}" y="${y - r - 4}" text-anchor="middle" font-size="${active ? 11 : 9.5}" font-weight="${active ? 700 : 500}" fill="#14212b" stroke="#f4f2ea" stroke-width="2.5" paint-order="stroke">${esc(isS ? 'A ' : isT ? 'B ' : '')}${esc(l.code)}</text>` : ''}
      <title>${esc(l.name)}, ${esc(l.country)} \u2014 ${KIND[l.kind][0]} \u2014 ${fmt(l.packages)} packages</title></g>`;
  });
  el.innerHTML = `<div class="mapbox"><svg viewBox="0 0 ${MAP.W} ${MAP.H}" id="mapsvg" role="img" aria-label="Logistics network map">${svg}${base}${hi}${labels}${nodes}</svg>
    <div class="maptools"><button class="ghost" data-z="in" aria-label="Zoom in">+</button><button class="ghost" data-z="out" aria-label="Zoom out">\u2212</button><button class="ghost" data-z="reset">Reset</button></div></div>
    <div class="legend">${Object.values(KIND).map(k => `<span><i style="border-color:${k[1]}"></i>${k[0]}</span>`).join('')}
    <span><i style="border-color:#6f8799"></i>Route</span><span><i style="border-color:#c0392b;border-top-style:dashed"></i>Negative weight</span>
    ${opts.route?.path ? `<span><i style="border-color:${opts.route.algorithm === 'bellman_ford' ? '#b0306e' : '#2563b8'}"></i>Selected route</span><span><i style="border-color:#6f9bd1;border-top-style:dashed"></i>Alternative</span>` : ''}</div>`;
  const svgEl = el.querySelector('svg'); let vb = [0, 0, MAP.W, MAP.H], drag = null, moved = false;
  const setVB = () => svgEl.setAttribute('viewBox', vb.join(' '));
  const zoom = (f, cx = vb[0] + vb[2] / 2, cy = vb[1] + vb[3] / 2) => {
    const nw = Math.min(MAP.W, Math.max(60, vb[2] * f)), nh = nw * MAP.H / MAP.W;
    vb = [Math.max(0, Math.min(MAP.W - nw, cx - (cx - vb[0]) * nw / vb[2])), Math.max(0, Math.min(MAP.H - nh, cy - (cy - vb[1]) * nh / vb[3])), nw, nh]; setVB();
  };
  const toMap = e => { const r = svgEl.getBoundingClientRect(); return [vb[0] + (e.clientX - r.left) / r.width * vb[2], vb[1] + (e.clientY - r.top) / r.height * vb[3]]; };
  svgEl.addEventListener('wheel', e => { e.preventDefault(); const [cx, cy] = toMap(e); zoom(e.deltaY < 0 ? .8 : 1.25, cx, cy); }, {passive: false});
  svgEl.addEventListener('pointerdown', e => { drag = {x: e.clientX, y: e.clientY, vb: [...vb]}; moved = false; });
  window.addEventListener('pointermove', e => { if (!drag || !el.isConnected) return; const r = svgEl.getBoundingClientRect(), dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
    vb = [Math.max(0, Math.min(MAP.W - vb[2], drag.vb[0] - dx / r.width * vb[2])), Math.max(0, Math.min(MAP.H - vb[3], drag.vb[1] - dy / r.height * vb[3])), vb[2], vb[3]]; setVB(); });
  window.addEventListener('pointerup', () => { drag = null; });
  el.querySelectorAll('[data-z]').forEach(b => b.onclick = () => b.dataset.z === 'reset' ? (vb = [0, 0, MAP.W, MAP.H], setVB()) : zoom(b.dataset.z === 'in' ? .7 : 1.4));
  el.querySelectorAll('.node').forEach(n => n.addEventListener('click', () => { if (!moved) opts.onPick?.(n.dataset.code); }));
}
