/* Dependency-free SVG charts. */
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = (n, d = 0) => n == null ? '\u2014' : Number(n).toLocaleString('en-US', {maximumFractionDigits: d, minimumFractionDigits: d});
const niceNum = n => n >= 1e9 ? (n / 1e9).toFixed(1) + 'B' : n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(n >= 1e4 ? 0 : 1) + 'k' : String(Math.round(n * 100) / 100);

function barChart(data, {title = '', color = '#2563b8', unit = '', w = 420, h = 230} = {}) {
  const m = {l: 54, r: 12, t: 30, b: 34}, max = Math.max(...data.map(d => d.value), 1) * 1.1;
  const bw = (w - m.l - m.r) / data.length;
  let s = `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(title)}"><text class="ttl" x="4" y="16">${esc(title)}</text>`;
  for (let i = 0; i <= 4; i++) {
    const y = h - m.b - (h - m.t - m.b) * i / 4;
    s += `<line x1="${m.l}" x2="${w - m.r}" y1="${y}" y2="${y}" stroke="#e3eaef"/><text x="${m.l - 6}" y="${y + 4}" text-anchor="end">${niceNum(max * i / 4)}</text>`;
  }
  data.forEach((d, i) => {
    const bh = (h - m.t - m.b) * d.value / max, x = m.l + i * bw + bw * .18, y = h - m.b - bh;
    s += `<rect x="${x}" y="${y}" width="${bw * .64}" height="${bh}" rx="2" fill="${d.color || color}"><title>${esc(d.label)}: ${fmt(d.value, 1)} ${unit}</title></rect>
      <text x="${x + bw * .32}" y="${h - m.b + 15}" text-anchor="middle">${esc(d.label)}</text>
      <text x="${x + bw * .32}" y="${y - 4}" text-anchor="middle">${niceNum(d.value)}</text>`;
  });
  return s + (unit ? `<text x="${w - m.r}" y="16" text-anchor="end">${esc(unit)}</text>` : '') + '</svg>';
}

/* series: [{name,color,dash,points:[[x,y],...]}] ; logY / logX optional */
function lineChart(series, {title = '', xLabel = '', yLabel = '', logY = false, logX = false, w = 560, h = 290} = {}) {
  const m = {l: 58, r: 14, t: 34, b: 44};
  const pts = series.flatMap(s => s.points).filter(p => p[1] > 0 || !logY);
  if (!pts.length) return '<p class="muted">No data.</p>';
  const tx = v => logX ? Math.log10(v) : v, ty = v => logY ? Math.log10(Math.max(v, 1e-9)) : v;
  const xs = pts.map(p => tx(p[0])), ys = pts.map(p => ty(p[1]));
  let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = logY ? Math.floor(Math.min(...ys)) : 0, y1 = logY ? Math.ceil(Math.max(...ys)) : Math.max(...ys) * 1.08;
  if (x0 === x1) x1 = x0 + 1; if (y0 === y1) y1 = y0 + 1;
  const X = v => m.l + (tx(v) - x0) / (x1 - x0) * (w - m.l - m.r), Y = v => h - m.b - (ty(v) - y0) / (y1 - y0) * (h - m.t - m.b);
  let s = `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(title)}"><text class="ttl" x="4" y="16">${esc(title)}</text>`;
  for (let i = 0; i <= 4; i++) {
    const v = y0 + (y1 - y0) * i / 4, y = h - m.b - (h - m.t - m.b) * i / 4;
    s += `<line x1="${m.l}" x2="${w - m.r}" y1="${y}" y2="${y}" stroke="#e3eaef"/><text x="${m.l - 6}" y="${y + 4}" text-anchor="end">${niceNum(logY ? 10 ** v : v)}</text>`;
  }
  [...new Set(series.flatMap(s => s.points.map(p => p[0])))].sort((a, b) => a - b).forEach(v =>
    s += `<text x="${X(v)}" y="${h - m.b + 15}" text-anchor="middle">${v}</text>`);
  s += `<text x="${(w + m.l) / 2}" y="${h - 6}" text-anchor="middle">${esc(xLabel)}</text><text x="12" y="${(h + m.t) / 2}" transform="rotate(-90 12 ${(h + m.t) / 2})" text-anchor="middle">${esc(yLabel)}</text>`;
  series.forEach((sr, i) => {
    const p = sr.points.filter(p => p[1] > 0 || !logY);
    s += `<path d="${p.map((q, j) => (j ? 'L' : 'M') + X(q[0]).toFixed(1) + ' ' + Y(q[1]).toFixed(1)).join('')}" fill="none" stroke="${sr.color}" stroke-width="2.2" ${sr.dash ? 'stroke-dasharray="6 4"' : ''}/>`;
    p.forEach(q => s += `<circle cx="${X(q[0])}" cy="${Y(q[1])}" r="3" fill="${sr.color}"><title>${esc(sr.name)}: V=${q[0]}, ${niceNum(q[1])}</title></circle>`);
    s += `<g transform="translate(${m.l + 8 + i * 150},${m.t - 8})"><line x2="16" stroke="${sr.color}" stroke-width="3" ${sr.dash ? 'stroke-dasharray="5 3"' : ''}/><text x="21" y="4">${esc(sr.name)}</text></g>`;
  });
  return s + '</svg>';
}
