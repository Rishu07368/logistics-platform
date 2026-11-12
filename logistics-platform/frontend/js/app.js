const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const S = {nets: [], nid: null, graph: null, summary: null, analysis: null, metric: 'cost', sel: {source: null, target: null},
  algo: 'auto', alts: true, route: null, routeErr: null, cmp: null, bench: null, ana: null, view: 'overview'};
const UNIT = {cost: 'USD', time: 'h', distance: 'km'}, ALGO = {dijkstra_heap: 'Dijkstra (heap)', dijkstra_array: 'Dijkstra (array)', bellman_ford: 'Bellman-Ford', auto: 'Auto (recommended)'};
const COL = {dijkstra_heap: '#2563b8', dijkstra_array: '#6f9bd1', bellman_ford: '#b0306e'};

async function api(path, opts = {}) {
  const res = await fetch('/api' + path, {headers: {'Content-Type': 'application/json'}, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined});
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({error: 'Invalid server response'}));
  if (!res.ok) throw Object.assign(new Error(data.error || 'Request failed'), {data, status: res.status});
  return data;
}
let toastT;
function toast(msg, err) { const t = $('#toast'); t.textContent = msg; t.className = 'show' + (err ? ' err' : ''); clearTimeout(toastT); toastT = setTimeout(() => t.className = '', 3800); }
async function guard(btn, fn) {
  if (btn) btn.disabled = true;
  try { return await fn(); } catch (e) { toast(e.message, true); } finally { if (btn) btn.disabled = false; }
}
const locOpts = (sel, skip) => S.graph.locations.map(l => `<option value="${esc(l.code)}" ${l.code === sel ? 'selected' : ''}>${esc(l.code)} \u2014 ${esc(l.name)}</option>`).join('');
const pathChips = p => p ? `<div class="path">${p.map(c => `<span class="n" title="${esc(S.graph.locations.find(l => l.code === c)?.name)}">${esc(c)}</span>`).join('<i>\u2192</i>')}</div>` : '<span class="muted">\u2014</span>';
const mval = (v, m) => m === 'cost' ? '$' + fmt(v, 0) : m === 'time' ? fmt(v, 1) + ' h' : fmt(v, 0) + ' km';

/* ---------- data loading ---------- */
async function loadNetwork() {
  const id = S.nid;
  const [graph, summary, analysis] = await Promise.all([api(`/networks/${id}/graph`), api(`/networks/${id}/summary`), api(`/networks/${id}/analysis?metric=${S.metric}`)]);
  S.graph = graph; S.summary = summary; S.analysis = analysis; S.route = S.routeErr = S.cmp = S.ana = null;
  const codes = graph.locations.map(l => l.code);
  if (!codes.includes(S.sel.source)) S.sel = {source: codes[0] || null, target: codes[Math.min(codes.length - 1, Math.floor(codes.length / 2))] || null};
  $('#netDesc').textContent = graph.network.description;
  $('#title').textContent = graph.network.name;
  renderBadges();
}
async function refreshAnalysis() { S.analysis = await api(`/networks/${S.nid}/analysis?metric=${S.metric}`); S.route = S.routeErr = S.cmp = S.ana = null; renderBadges(); }
async function reloadAfterEdit() { await loadNetwork(); S.nets = (await api('/networks')).networks; fillNetSel(); }
function renderBadges() {
  const p = S.analysis.properties, rec = S.analysis.recommendation;
  $('#badges').innerHTML = `<span class="badge">${p.vertices} locations</span><span class="badge">${p.edges} routes</span>
    ${p.has_negative_cycle ? '<span class="badge bad">negative cycle</span>' : p.negative_edge_count ? `<span class="badge warn">${p.negative_edge_count} negative edge(s)</span>` : '<span class="badge ok">non-negative weights</span>'}
    <span class="badge">${rec.algorithm ? 'Recommended: ' + ALGO[rec.algorithm] : 'No valid algorithm'}</span>`;
}
function fillNetSel() { $('#netSel').innerHTML = S.nets.map(n => `<option value="${n.id}" ${n.id === S.nid ? 'selected' : ''}>${esc(n.name)}</option>`).join(''); }

/* ---------- shared pieces ---------- */
function recBanner() {
  const r = S.analysis.recommendation, cls = r.status === 'invalid' ? 'bad' : r.algorithm === 'bellman_ford' ? 'warn' : '';
  return `<div class="banner ${cls}"><b>${esc(r.headline)}</b> <span class="muted">for the ${S.metric} metric</span><ul>${r.reasons.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>`;
}
const kpi = (label, val, sub) => `<div class="card kpi"><small>${label}</small><b>${val}</b><em>${sub || '&nbsp;'}</em></div>`;
function pick(code) {
  const s = S.sel; if (!s.source || (s.source && s.target)) S.sel = {source: code, target: null}; else s.target = code;
  S.route = S.routeErr = null; render();
}

/* ---------- views ---------- */
function vOverview() {
  const s = S.summary, c = s.connectivity;
  $('#view').innerHTML = `<div class="grid g4">
    ${kpi('Locations connected', fmt(s.locations), `${s.countries} countries`)}
    ${kpi('Warehouses', fmt(s.warehouses), `${s.distribution_centers} distribution centers`)}
    ${kpi('Active routes', fmt(s.directed_routes), `${fmt(s.corridors)} two-way corridors`)}
    ${kpi('Packages in network', fmt(s.packages), `${s.destinations} destinations`)}
    ${kpi('Avg delivery time', s.avg_delivery_hours == null ? '\u2014' : fmt(s.avg_delivery_hours, 1) + ' h', 'mean shortest time between hubs')}
    ${kpi('Weekly transport spend', '$' + fmt(s.weekly_spend_usd), 'route cost \u00d7 weekly trips')}
    ${kpi('Connectivity', c.strongly_connected ? 'Strong' : c.strong_components + ' parts', `${c.weak_components} weak component(s)`)}
    ${kpi('Graph density', fmt(c.density, 4), `avg out-degree ${c.avg_out_degree}`)}</div>
  <div class="grid g21"><div class="card"><h2>Global network</h2><p class="muted" style="margin-top:-6px">Click two locations to choose source and destination, then open the route optimizer. Scroll to zoom, drag to pan.</p>
    <div id="map"></div><div class="row" style="margin-top:10px"><label><span>Show edge weights (${S.metric})</span><input type="checkbox" id="wt" ${S.weights ? 'checked' : ''}></label>
    <span class="muted">${S.sel.source ? 'A: ' + esc(S.sel.source) : ''} ${S.sel.target ? ' B: ' + esc(S.sel.target) : ''}</span><button id="goopt" ${S.sel.source && S.sel.target ? '' : 'disabled'}>Optimize this route</button></div></div>
  <div><div class="card"><h2>Algorithm recommendation</h2>${recBanner()}<p class="muted">Derived from the live graph: negative edges and cycles are detected by running Bellman-Ford over the stored routes.</p></div></div></div>`;
  const draw = () => drawMap($('#map'), S.graph, {sel: S.sel, metric: S.metric, showWeights: S.weights, onPick: pick});
  draw(); $('#wt').onchange = e => { S.weights = e.target.checked; draw(); }; $('#goopt').onclick = () => go('optimizer');
}

function vOptimizer() {
  $('#view').innerHTML = `<div class="card"><div class="row">
    <label>Source<select id="src">${locOpts(S.sel.source)}</select></label><label>Destination<select id="dst">${locOpts(S.sel.target)}</select></label>
    <label>Algorithm<div class="seg" id="algoSeg">${Object.keys(ALGO).map(a => `<button data-a="${a}" class="${S.algo === a ? 'on' : ''}">${ALGO[a]}</button>`).join('')}</div></label>
    <label>Alternatives<input type="checkbox" id="alts" ${S.alts ? 'checked' : ''}></label><button id="calc">Calculate route</button></div>
    <p class="muted" style="margin:8px 0 0">Optimizing <b>${S.metric}</b> (${UNIT[S.metric]}). Change the metric in the sidebar.</p></div>
  <div class="grid g21"><div class="card"><div id="map"></div></div><div id="res"></div></div>`;
  const draw = () => drawMap($('#map'), S.graph, {sel: S.sel, route: S.route, metric: S.metric, showWeights: S.weights, onPick: pick});
  draw(); renderRoute();
  $('#src').onchange = e => { S.sel.source = e.target.value; S.route = S.routeErr = null; render(); };
  $('#dst').onchange = e => { S.sel.target = e.target.value; S.route = S.routeErr = null; render(); };
  $('#alts').onchange = e => S.alts = e.target.checked;
  $$('#algoSeg button').forEach(b => b.onclick = () => { S.algo = b.dataset.a; $$('#algoSeg button').forEach(x => x.classList.toggle('on', x === b)); });
  $('#calc').onclick = () => calcRoute($('#calc'));
}
async function calcRoute(btn) {
  if (!S.sel.source || !S.sel.target) return toast('Choose a source and destination first', true);
  S.route = S.routeErr = null;
  await guard(btn, async () => {
    try { S.route = await api(`/networks/${S.nid}/route`, {method: 'POST', body: {source: S.sel.source, target: S.sel.target, algorithm: S.algo, metric: S.metric, alternatives: S.alts}}); }
    catch (e) { if (e.data?.code === 'NEGATIVE_WEIGHTS') S.routeErr = e.data; else throw e; }
    render();
  });
}
function renderRoute() {
  const el = $('#res'), r = S.route, m = S.metric; if (!el) return;
  if (S.routeErr) { const e = S.routeErr; el.innerHTML = `<div class="card"><div class="banner bad"><b>Dijkstra blocked</b><p style="margin:4px 0">${esc(e.error)}</p></div>
    <p>Negative edges: ${e.negative_edges.map(x => `<span class="mono">${esc(x.from)}\u2192${esc(x.to)} (${x.weight})</span>`).join(', ')}</p>
    <button id="useBf">Run Bellman-Ford instead</button></div>`; $('#useBf').onclick = () => { S.algo = 'bellman_ford'; render(); calcRoute($('#calc')); }; return; }
  if (!r) { el.innerHTML = `<div class="card"><h2>Route result</h2><p class="muted">Pick a source and destination on the map or from the lists, then calculate. Results use the backend graph and the selected algorithm.</p>${recBanner()}</div>`; return; }
  const bad = r.status === 'negative_cycle' || r.status === 'unreachable';
  el.innerHTML = `<div class="card ${r.algorithm === 'bellman_ford' ? 'bar-bf' : 'bar-dij'}"><h2>${ALGO[r.algorithm]} <span class="badge ${bad ? 'bad' : 'ok'}">${r.status.replace('_', ' ')}</span></h2>
    ${r.message ? `<div class="banner ${bad ? 'bad' : 'warn'}">${esc(r.message)}${r.negative_cycle ? `<br><span class="mono">Cycle: ${r.negative_cycle.nodes.join(' \u2192 ')} \u2192 ${r.negative_cycle.nodes[0]} (weight ${fmt(r.negative_cycle.weight, 1)})</span>` : ''}</div>` : ''}
    ${r.path ? `<div class="grid g2"><div class="kpi"><small>Optimal ${m}</small><b>${mval(r.total, m)}</b></div><div class="kpi"><small>Estimated travel time</small><b>${fmt(r.totals.time_hours, 1)} h</b></div>
      <div class="kpi"><small>Distance</small><b>${fmt(r.totals.distance_km)} km</b></div><div class="kpi"><small>Cost</small><b>$${fmt(r.totals.cost_usd)}</b></div></div>
      <h3>Route</h3>${pathChips(r.path)}<div class="scroll" style="max-height:230px"><table class="tight"><tr><th>Hop</th><th>Mode</th><th class="n">km</th><th class="n">USD</th><th class="n">h</th></tr>
      ${r.hops.map(h => `<tr><td>${esc(h.from)}\u2192${esc(h.to)}</td><td>${h.mode}</td><td class="n">${fmt(h.distance_km)}</td><td class="n">${fmt(h.cost_usd)}</td><td class="n">${fmt(h.time_hours, 1)}</td></tr>`).join('')}</table></div>` : ''}
    <h3>Execution</h3><table class="tight"><tr><td>Time</td><td class="n">${fmt(r.stats.time_ms, 3)} ms</td></tr><tr><td>Relaxations</td><td class="n">${fmt(r.stats.relaxations)}</td></tr>
      <tr><td>${r.algorithm === 'bellman_ford' ? 'Passes over all edges' : 'Iterations (extractions)'}</td><td class="n">${fmt(r.stats.iterations)}</td></tr><tr><td>Edge checks</td><td class="n">${fmt(r.stats.edge_checks)}</td></tr>
      ${r.stats.early_termination != null ? `<tr><td>Early termination</td><td class="n">${r.stats.early_termination ? 'yes' : 'no'}</td></tr>` : ''}</table>
    ${r.alternatives.length ? `<h3>Alternative routes <span class="muted">(best route with one link removed)</span></h3><table class="tight"><tr><th>Path</th><th class="n">${m}</th><th class="n">Extra</th></tr>
      ${r.alternatives.map(a => `<tr><td>${a.path.join('\u2192')}<div class="muted">avoids ${esc(a.avoids)}</div></td><td class="n">${mval(a.total, m)}</td><td class="n">+${fmt(a.extra, 1)}</td></tr>`).join('')}</table>` : ''}</div>`;
}

function cmpTable(c) {
  const rows = c.rows, cell = (r, f) => r.applicable || r.forced ? f(r) : '<span class="muted">not applicable</span>';
  const line = (label, f, cls = '') => `<tr><th>${label}</th>${rows.map(r => `<td class="${cls}">${f(r)}</td>`).join('')}</tr>`;
  return `<div class="scroll" style="max-height:none"><table><tr><th></th>${rows.map(r => `<th style="color:${COL[r.algorithm]}">${esc(r.label)}${r.forced ? ' <span class="badge bad">forced \u2014 invalid</span>' : ''}</th>`).join('')}</tr>
    ${line('Time complexity', r => `<span class="mono">${esc(r.time)}</span>`)}${line('Space complexity', r => `<span class="mono">${esc(r.space)}</span>`)}
    ${line('Negative edge support', r => r.negative_edges ? 'Yes' : 'No')}${line('Negative cycle detection', r => r.negative_cycle_detection ? 'Yes' : 'No')}
    ${line('Applicable to this graph', r => r.applicable ? '<span class="badge ok">yes</span>' : `<span class="badge bad">no</span><div class="muted">${esc(r.reason)}</div>`)}
    ${line('Optimal ' + c.metric, r => cell(r, x => x.negative_cycle ? '\u2212\u221e' : x.total == null ? 'unreachable' : mval(x.total, c.metric)))}
    ${line('Route length', r => cell(r, x => x.path ? (x.path.length - 1) + ' hops' : '\u2014'))}
    ${line('Median time (' + (rows.find(r => r.repeats)?.repeats || 0) + ' runs)', r => cell(r, x => fmt(x.median_ms, 3) + ' ms'), 'n')}
    ${line('Relaxations', r => cell(r, x => fmt(x.stats.relaxations)), 'n')}${line('Iterations', r => cell(r, x => fmt(x.stats.iterations)), 'n')}
    ${line('Edge checks', r => cell(r, x => fmt(x.stats.edge_checks)), 'n')}${line('Early termination', r => cell(r, x => x.early_termination == null ? 'n/a' : x.early_termination ? 'yes' : 'no'))}</table></div>`;
}

function vLab() {
  $('#view').innerHTML = `<div class="card"><h2>Head-to-head comparison</h2><div class="row"><label>Source<select id="src">${locOpts(S.sel.source)}</select></label><label>Destination<select id="dst">${locOpts(S.sel.target)}</select></label>
    <label>Timing repeats<input id="rep" type="number" min="1" max="50" value="5" style="width:80px"></label>
    <label>Force Dijkstra on negative edges<input type="checkbox" id="force"></label><button id="run">Run comparison</button></div>
    <p class="muted">Every algorithm receives the identical edge list for the <b>${S.metric}</b> metric. "Force" runs Dijkstra without its safety check to show what goes wrong.</p></div>
  ${recBanner()}<div id="cmp"></div>
  <div class="card"><h2>Scaling benchmark</h2><div class="row"><label>Graph sizes (V)<input id="sizes" value="25,50,100,200,400,800" style="width:210px"></label>
    <label>Avg out-degree<input id="deg" type="number" min="1" max="12" value="4" style="width:80px"></label><label>Repeats<input id="brep" type="number" min="1" max="10" value="3" style="width:70px"></label><button id="bench">Run benchmark</button></div>
    <p class="muted">Generated graphs with positive weights (so every algorithm is valid). Results are measured on this machine; nothing is pre-computed.</p><div id="benchOut"></div></div>
  <div class="card"><h2>Why the complexities differ</h2><div class="grid g3">
    <div><h3 class="dij">O(V\u00b2) \u2014 Dijkstra, array</h3><p>Each of V rounds scans all unsettled vertices for the minimum: V \u00d7 V. Edge relaxation adds only O(E). Competitive when the graph is dense (E \u2248 V\u00b2).</p></div>
    <div><h3 class="dij">O((V + E) log V) \u2014 Dijkstra, heap</h3><p>A binary heap makes each minimum extraction and each decrease-key cost log V. Best for sparse networks such as road, rail and shipping graphs where E \u2248 4V.</p></div>
    <div><h3 class="bf">O(V \u00b7 E) \u2014 Bellman-Ford</h3><p>Up to V\u22121 passes, each scanning all E edges. Far slower on large graphs, but it tolerates negative weights and detects negative cycles. Early termination often ends sooner on friendly inputs.</p></div></div></div>`;
  $('#src').onchange = e => S.sel.source = e.target.value; $('#dst').onchange = e => S.sel.target = e.target.value;
  if (S.cmp) $('#cmp').innerHTML = cmpHtml(S.cmp); if (S.bench) $('#benchOut').innerHTML = benchHtml(S.bench);
  $('#run').onclick = e => guard(e.target, async () => {
    S.cmp = await api(`/networks/${S.nid}/compare`, {method: 'POST', body: {source: S.sel.source, target: S.sel.target, metric: S.metric, repeats: +$('#rep').value, force_dijkstra: $('#force').checked}});
    $('#cmp').innerHTML = cmpHtml(S.cmp);
  });
  $('#bench').onclick = e => guard(e.target, async () => {
    const sizes = $('#sizes').value.split(',').map(x => parseInt(x)).filter(Boolean);
    toast('Benchmarking\u2026 larger sizes take a few seconds');
    S.bench = await api('/benchmark', {method: 'POST', body: {sizes, repeats: +$('#brep').value, avg_degree: +$('#deg').value}});
    $('#benchOut').innerHTML = benchHtml(S.bench);
  });
}
function cmpHtml(c) {
  const bf = c.rows.find(r => r.algorithm === 'bellman_ford' && r.stats), dj = c.rows.find(r => r.algorithm === 'dijkstra_heap' && r.stats && !r.forced);
  let verdict = c.recommendation.status === 'invalid' ? 'This graph has a negative cycle reachable from the network, so a finite shortest path is not guaranteed; Bellman-Ford reports the cycle instead of a wrong answer.'
    : dj && bf ? `Both valid algorithms agree${c.agreement ? ' on the optimal value' : ' (check totals)'}. Dijkstra (heap) ran in ${fmt(dj.median_ms, 3)} ms vs ${fmt(bf.median_ms, 3)} ms for Bellman-Ford (${fmt(bf.median_ms / dj.median_ms, 1)}\u00d7), with ${fmt(dj.stats.edge_checks)} vs ${fmt(bf.stats.edge_checks)} edge checks.`
    : 'Dijkstra is not valid for this metric because negative edges exist; Bellman-Ford is the correct choice.';
  return `<div class="card"><h2>Results: ${esc(c.source)} \u2192 ${esc(c.target)} <span class="muted">(${c.metric})</span></h2>
    <div class="banner ${c.forced_dijkstra_wrong ? 'bad' : ''}">${esc(verdict)}${c.forced_dijkstra_wrong ? ' <b>Forced Dijkstra returned a different (wrong) total than Bellman-Ford</b> \u2014 proof that its greedy assumption fails with negative edges.' : ''}</div>
    ${cmpTable(c)}<p class="muted">${esc(c.note)}</p>
    <div class="grid g2">${c.rows.filter(r => r.stats).map(r => `<div style="border-left:3px solid ${COL[r.algorithm]};padding-left:10px"><b>${esc(r.label)}</b>${pathChips(r.path)}</div>`).join('')}</div></div>`;
}
function benchHtml(b) {
  const get = (g, a) => b.points.filter(p => p.graph === g && p.algorithm === a).map(p => [p.vertices, p.median_ms]);
  const mk = g => ['dijkstra_heap', 'dijkstra_array', 'bellman_ford'].map(a => ({name: ALGO[a], color: COL[a], points: get(g, a)}));
  const th = b.theory.filter(t => t.graph === 'random');
  const theory = [{name: 'V\u00b2', color: '#6f9bd1', dash: 1, points: th.map(t => [t.vertices, t.v_squared])}, {name: '(V+E) log V', color: '#2563b8', points: th.map(t => [t.vertices, t.v_plus_e_log_v])}, {name: 'V\u00b7E', color: '#b0306e', points: th.map(t => [t.vertices, t.v_times_e])}];
  const bfp = g => b.points.filter(p => p.graph === g && p.algorithm === 'bellman_ford');
  return `<div class="grid g2"><div>${lineChart(mk('random'), {title: 'Measured time \u2014 random sparse graphs', xLabel: 'vertices V', yLabel: 'ms (log)', logY: true, logX: true})}</div>
    <div>${lineChart(mk('bf_worst_case'), {title: 'Measured time \u2014 Bellman-Ford worst case', xLabel: 'vertices V', yLabel: 'ms (log)', logY: true, logX: true})}</div>
    <div>${lineChart(theory, {title: 'Theoretical operation counts', xLabel: 'vertices V', yLabel: 'operations (log)', logY: true, logX: true})}</div>
    <div><table class="tight"><tr><th>V</th><th>E</th><th>Graph</th><th class="n">BF passes</th><th class="n">BF relaxations</th></tr>${b.points.filter(p => p.algorithm === 'bellman_ford').map(p => `<tr><td>${p.vertices}</td><td>${p.edges}</td><td>${p.graph === 'random' ? 'random' : 'worst case'}</td><td class="n">${p.iterations}</td><td class="n">${fmt(p.relaxations)}</td></tr>`).join('')}</table></div></div>
    <h3>Measured times (ms, median of ${b.repeats})</h3><div class="scroll"><table class="tight"><tr><th>V</th><th>Graph</th><th class="n dij">Dijkstra heap</th><th class="n dij">Dijkstra array</th><th class="n bf">Bellman-Ford</th></tr>
    ${[...new Set(b.points.map(p => p.vertices + '|' + p.graph))].map(k => { const [v, g] = k.split('|'), f = a => b.points.find(p => p.vertices == v && p.graph === g && p.algorithm === a);
      return `<tr><td>${v}</td><td>${g === 'random' ? 'random' : 'worst case'}</td><td class="n">${fmt(f('dijkstra_heap').median_ms, 3)}</td><td class="n">${fmt(f('dijkstra_array').median_ms, 3)}</td><td class="n">${fmt(f('bellman_ford').median_ms, 3)}</td></tr>`; }).join('')}</table></div>
    <p class="muted">${esc(b.note)}</p>`;
}

/* ---------- manager ---------- */
function vManage() {
  const g = S.graph, net = g.network, q = (S.rfilter || '').toLowerCase();
  const routes = g.routes.filter(r => !q || (r.src + r.dst + r.mode).toLowerCase().includes(q));
  $('#view').innerHTML = `<div class="grid g2"><div class="card"><h2>Network</h2><p class="muted">${esc(net.description)}</p><div class="row">
      ${net.scenario !== 'generated' ? '<button class="ghost" id="reset">Reset to original scenario</button>' : '<button class="danger" id="delnet">Delete this network</button>'}</div>
    <h3>Generate a sample network</h3><div class="formgrid"><label>Locations<input id="gn" type="number" value="60" min="5" max="500"></label><label>Seed<input id="gs" type="number" value="1"></label>
      <label>Negative test edges<input id="gneg" type="number" value="0" min="0" max="50"></label><button id="gen">Generate</button></div>
    <p class="muted">Negative costs model backhaul credits and exist to exercise Bellman-Ford; ordinary physical transport costs are not negative. Generation never creates a negative cycle.</p></div>
  <div class="card"><h2>Add a location</h2><div class="formgrid"><label>Code<input id="lc" placeholder="PRG" maxlength="6"></label><label>Name<input id="ln" placeholder="Prague"></label><label>Country<input id="lco" placeholder="CZ" maxlength="3"></label>
    <label>Type<select id="lk"><option value="warehouse">Warehouse</option><option value="distribution_center">Distribution center</option><option value="destination">Destination</option><option value="city">City</option></select></label>
    <label>Latitude<input id="la" type="number" step="any" placeholder="50.08"></label><label>Longitude<input id="lo" type="number" step="any" placeholder="14.43"></label><label>Packages<input id="lp" type="number" value="10000"></label><button id="addl">Add location</button></div></div></div>
  <div class="card"><h2>Connect locations</h2><div class="formgrid"><label>From<select id="rs">${locOpts(S.sel.source)}</select></label><label>To<select id="rd">${locOpts(S.sel.target)}</select></label>
    <label>Mode<select id="rm"><option>road</option><option>rail</option><option>sea</option><option>air</option></select></label><label>Distance km<input id="rkm" type="number" step="any" placeholder="auto"></label>
    <label>Cost USD<input id="rc" type="number" step="any" placeholder="auto (negative = test)"></label><label>Time h<input id="rt" type="number" step="any" placeholder="auto"></label>
    <label>Two-way<input type="checkbox" id="rb" checked></label><button id="addr">Add route</button></div><p class="muted">Blank values are derived from coordinates and transport mode.</p></div>
  <div class="card"><h2>Routes <span class="muted">(${routes.length} of ${g.routes.length})</span></h2><div class="row" style="margin-bottom:8px"><label>Filter<input id="rf" value="${esc(S.rfilter || '')}" placeholder="e.g. SHA or sea"></label></div>
    <div class="scroll"><table class="tight"><tr><th>From</th><th>To</th><th>Mode</th><th>Distance km</th><th>Cost USD</th><th>Time h</th><th>Trips/wk</th><th></th></tr>
    ${routes.slice(0, 80).map(r => `<tr data-id="${r.id}"><td>${esc(r.src)}</td><td>${esc(r.dst)}</td><td>${r.mode}</td><td><input data-k="distance_km" type="number" step="any" min="0" value="${r.distance_km}"></td>
      <td><input data-k="cost_usd" type="number" step="any" value="${r.cost_usd}" ${r.cost_usd < 0 ? 'style="color:var(--bad)"' : ''}></td><td><input data-k="time_hours" type="number" step="any" value="${r.time_hours}"></td>
      <td><input data-k="weekly_trips" type="number" min="0" value="${r.weekly_trips}"></td><td><button class="ghost sv">Save</button> <button class="danger rm">Remove</button></td></tr>`).join('')}</table></div>
    ${routes.length > 80 ? '<p class="muted">Showing the first 80 \u2014 use the filter to narrow down.</p>' : ''}</div>
  <div class="card"><h2>Locations</h2><div class="scroll"><table class="tight"><tr><th>Code</th><th>Name</th><th>Country</th><th>Type</th><th class="n">Packages</th><th></th></tr>
    ${g.locations.slice(0, 100).map(l => `<tr data-lid="${l.id}"><td>${esc(l.code)}</td><td>${esc(l.name)}</td><td>${esc(l.country)}</td><td>${l.kind.replace('_', ' ')}</td><td class="n">${fmt(l.packages)}</td><td><button class="danger dl">Remove</button></td></tr>`).join('')}</table></div></div>`;
  const act = (sel, fn, msg) => { const b = $(sel); if (b) b.onclick = () => guard(b, async () => { await fn(); await reloadAfterEdit(); toast(msg); render(); }); };
  const val = id => $(id).value;
  act('#reset', () => api(`/networks/${S.nid}/reset`, {method: 'POST'}), 'Scenario reset');
  act('#delnet', async () => { await api(`/networks/${S.nid}`, {method: 'DELETE'}); S.nets = (await api('/networks')).networks; S.nid = S.nets[0].id; fillNetSel(); }, 'Network deleted');
  $('#gen')?.addEventListener('click', e => guard(e.target, async () => {
    const n = await api('/networks/generate', {method: 'POST', body: {nodes: +val('#gn'), seed: +val('#gs'), negative_edges: +val('#gneg')}});
    S.nets = (await api('/networks')).networks; S.nid = n.id; fillNetSel(); await loadNetwork(); toast('Generated ' + n.name); render();
  }));
  act('#addl', () => api(`/networks/${S.nid}/locations`, {method: 'POST', body: {code: val('#lc'), name: val('#ln'), country: val('#lco'), kind: val('#lk'), lat: val('#la'), lon: val('#lo'), packages: val('#lp')}}), 'Location added');
  act('#addr', () => api(`/networks/${S.nid}/routes`, {method: 'POST', body: {src: val('#rs'), dst: val('#rd'), mode: val('#rm'), distance_km: val('#rkm'), cost_usd: val('#rc'), time_hours: val('#rt'), bidirectional: $('#rb').checked}}), 'Route added');
  $('#rf').oninput = e => { S.rfilter = e.target.value; const pos = e.target.selectionStart; vManage(); const f = $('#rf'); f.focus(); f.setSelectionRange(pos, pos); };
  $$('tr[data-id]').forEach(tr => {
    $('.sv', tr).onclick = e => guard(e.target, async () => { const body = {}; $$('input', tr).forEach(i => body[i.dataset.k] = i.value); await api('/routes/' + tr.dataset.id, {method: 'PUT', body}); await reloadAfterEdit(); toast('Route updated'); render(); });
    $('.rm', tr).onclick = e => guard(e.target, async () => { await api('/routes/' + tr.dataset.id, {method: 'DELETE'}); await reloadAfterEdit(); toast('Route removed'); render(); });
  });
  $$('tr[data-lid]').forEach(tr => $('.dl', tr).onclick = e => guard(e.target, async () => {
    if (!confirm('Remove this location and all routes touching it?')) return;
    await api('/locations/' + tr.dataset.lid, {method: 'DELETE'}); await reloadAfterEdit(); toast('Location removed'); render(); }));
}

/* ---------- analytics ---------- */
async function vAnalytics() {
  $('#view').innerHTML = '<p class="spin">Computing analytics\u2026</p>';
  if (!S.ana) S.ana = await api(`/networks/${S.nid}/analytics?metric=${S.metric}`);
  const a = S.ana, p = a.properties, bars = (k, c) => a.modes.map(m => ({label: m.mode, value: m[k], color: c}));
  $('#view').innerHTML = `<div class="grid g3"><div class="card">${barChart(bars('weekly_spend', '#2563b8'), {title: 'Weekly spend by mode', unit: 'USD'})}</div>
    <div class="card">${barChart(bars('avg_time', '#d98200'), {title: 'Average delivery time per route', unit: 'hours'})}</div>
    <div class="card">${barChart(bars('cost_per_km', '#2f7f8f'), {title: 'Cost per km by mode', unit: 'USD/km'})}</div></div>
  <div class="grid g2"><div class="card"><h2>Route efficiency <span class="muted">(${S.metric})</span></h2>${a.efficiency_note ? `<p class="muted">${esc(a.efficiency_note)}</p>` : `<p class="muted">Direct links that an indirect path beats. Efficiency = best path \u00f7 direct weight (lower means the direct link is wasteful).${a.avg_shortest != null ? ` Mean shortest ${S.metric}: ${fmt(a.avg_shortest, 1)} ${UNIT[S.metric]}.` : ''}</p>
      <table class="tight"><tr><th>Direct link</th><th class="n">Direct</th><th class="n">Best</th><th class="n">Eff.</th><th>Better path</th></tr>${a.inefficient_direct_routes.map(r => `<tr><td>${esc(r.src)}\u2192${esc(r.dst)}</td><td class="n">${fmt(r.direct)}</td><td class="n">${fmt(r.best)}</td><td class="n">${r.efficiency}</td><td>${r.efficiency < 1 ? r.via.join('\u2192') : 'direct is optimal'}</td></tr>`).join('')}</table>`}</div>
    <div class="card"><h2>Network connectivity</h2><table class="tight"><tr><td>Vertices / edges</td><td class="n">${p.vertices} / ${p.edges}</td></tr><tr><td>Density</td><td class="n">${p.density}</td></tr><tr><td>Average out-degree</td><td class="n">${p.avg_out_degree}</td></tr>
      <tr><td>Weak components</td><td class="n">${p.weak_components}</td></tr><tr><td>Strong components</td><td class="n">${p.strong_components}</td></tr><tr><td>Negative edges</td><td class="n">${p.negative_edge_count}</td></tr><tr><td>Negative cycle</td><td class="n">${p.has_negative_cycle ? 'yes' : 'no'}</td></tr></table>
      <h3>Busiest hubs</h3><table class="tight"><tr><th>Hub</th><th class="n">In</th><th class="n">Out</th><th class="n">Packages</th></tr>${a.hubs.slice(0, 6).map(h => `<tr><td>${esc(h.code)} ${esc(h.name)}</td><td class="n">${h.in}</td><td class="n">${h.out}</td><td class="n">${fmt(h.packages)}</td></tr>`).join('')}</table></div></div>
  <div class="card"><h2>Algorithm performance report</h2><p class="muted">Aggregated from every route calculation you ran on this network (stored in the database).</p>
    ${a.algorithm_report.length ? `<table class="tight"><tr><th>Algorithm</th><th class="n">Runs</th><th class="n">Avg time (ms)</th><th class="n">Avg relaxations</th><th class="n">Avg iterations</th><th class="n">Cycle detections</th></tr>
    ${a.algorithm_report.map(r => `<tr><td>${ALGO[r.algorithm]}</td><td class="n">${r.runs}</td><td class="n">${fmt(r.avg_time_ms, 3)}</td><td class="n">${fmt(r.avg_relaxations, 1)}</td><td class="n">${fmt(r.avg_iterations, 1)}</td><td class="n">${r.cycle_detections || 0}</td></tr>`).join('')}</table>
    <h3>Recent runs</h3><table class="tight"><tr><th>Algorithm</th><th>Route</th><th>Metric</th><th>Status</th><th class="n">Total</th><th class="n">ms</th></tr>${a.recent_runs.map(r => `<tr><td>${ALGO[r.algorithm]}</td><td>${esc(r.source)}\u2192${esc(r.target)}</td><td>${r.metric}</td><td>${r.status}</td><td class="n">${r.total == null ? '\u2014' : fmt(r.total, 1)}</td><td class="n">${fmt(r.time_ms, 3)}</td></tr>`).join('')}</table>` : '<p>No runs yet \u2014 calculate a route in the optimizer.</p>'}</div>`;
}

/* ---------- education ---------- */
function vLearn() {
  $('#view').innerHTML = `<div class="card edu"><h2>Modelling logistics as a graph</h2>
  <p>Locations are <b>vertices</b>; transport links are <b>directed weighted edges</b>. Directed edges matter: shipping NYC\u2192Rotterdam can cost differently from Rotterdam\u2192NYC, and negative weights are only meaningful when direction is tracked. This platform stores an adjacency list (edge list per vertex), which uses O(V + E) space and suits sparse transport networks. An adjacency matrix would need O(V\u00b2).</p>
  <p>Each edge carries three weights: cost (USD per shipment batch), distance (km) and time (hours). The <b>optimization metric</b> picks which one the algorithms minimize. Switching the metric changes the graph the algorithms see, and so can change which algorithm is valid.</p></div>
  <div class="grid g2"><div class="card edu bar-dij"><h2 class="dij">Dijkstra's algorithm</h2><p>Greedy: always settle the closest unsettled vertex, then relax its outgoing edges. Once a vertex is settled its distance is final, which is true only if no edge is negative.</p>
  <pre>dist[source] = 0; heap = [(0, source)]
while heap:
    d, u = pop_min(heap)
    if u settled: continue
    settle(u)
    for (v, w) in adj[u]:
        if d + w &lt; dist[v]:
            dist[v] = d + w; prev[v] = u; push(heap, (dist[v], v))</pre>
  <p><b>Time:</b> O((V + E) log V) with a binary heap, O(V\u00b2) with an array. <b>Space:</b> O(V + E). <b>Limits:</b> invalid with negative edges (this app blocks it and explains why); no cycle detection.</p></div>
  <div class="card edu bar-bf"><h2 class="bf">Bellman-Ford algorithm</h2><p>Relax every edge, repeat. A shortest path has at most V\u22121 edges, so V\u22121 passes suffice. If an extra pass still improves a distance, a negative cycle is reachable.</p>
  <pre>dist[source] = 0
repeat V-1 times:
    changed = false
    for (u, v, w) in edges:
        if dist[u] + w &lt; dist[v]: dist[v] = dist[u] + w; prev[v] = u; changed = true
    if not changed: break            # early termination
for (u, v, w) in edges:               # extra pass
    if dist[u] + w &lt; dist[v]: negative cycle!</pre>
  <p><b>Time:</b> O(V \u00b7 E) worst case. <b>Space:</b> O(V + E). <b>Strengths:</b> negative edges, negative-cycle detection, simple to distribute and to run on streaming edge lists.</p></div></div>
  <div class="card edu"><h2>Negative edges and negative cycles</h2><p>A negative edge in logistics could model a subsidy, a backhaul credit or a rebate. <b>This is mainly an algorithm-testing scenario</b>: ordinary physical transport costs, distances and times are not negative, so the sample scenarios label such weights as test weights.</p>
  <p>If edges form a cycle whose total is negative, looping around it lowers the cost without limit, so the shortest distance to anything reachable from the cycle is \u2212\u221e. No finite optimal route is guaranteed. Bellman-Ford finds and reports the cycle; the right fix is to repair the data.</p>
  <table><tr><th>Network condition</th><th>Use</th><th>Why</th></tr><tr><td>Large, non-negative weights</td><td class="dij">Dijkstra (heap)</td><td>(V + E) log V grows far slower than V\u00b7E; it is the standard choice for large-scale transport networks.</td></tr>
  <tr><td>Small or dense, non-negative</td><td class="dij">Dijkstra (array)</td><td>O(V\u00b2) avoids heap overhead when E is close to V\u00b2.</td></tr><tr><td>Valid negative edges, no negative cycle</td><td class="bf">Bellman-Ford</td><td>The only one of the two that stays correct.</td></tr>
  <tr><td>Negative cycle</td><td>Neither returns a finite path</td><td>Bellman-Ford detects it; the data must change.</td></tr></table></div>
  <div class="card edu"><h2>Beyond these two algorithms</h2><p>Production logistics systems rarely re-run either algorithm after every small change. They use precomputation such as contraction hierarchies and landmarks, goal-directed search (A*), time-dependent edge weights, and incremental or dynamic shortest-path updates that repair only the affected part of a previous solution. Johnson's algorithm combines Bellman-Ford with Dijkstra for all-pairs shortest paths with negative edges. Treat the timings here as a teaching comparison of two classic algorithms in a Python implementation, not as a production benchmark.</p></div>`;
}

/* ---------- router ---------- */
const VIEWS = {overview: vOverview, optimizer: vOptimizer, lab: vLab, manage: vManage, analytics: vAnalytics, learn: vLearn};
const TITLES = {learn: 'Algorithms explained'};
function render() {
  $$('#nav a').forEach(a => a.classList.toggle('on', a.hash === '#' + S.view));
  if (!S.graph) return;
  try { VIEWS[S.view](); } catch (e) { console.error(e); toast(e.message, true); }
}
function go(v) { location.hash = v; }
window.addEventListener('hashchange', () => { S.view = VIEWS[location.hash.slice(1)] ? location.hash.slice(1) : 'overview'; render(); });
async function boot() {
  try {
    S.nets = (await api('/networks')).networks; S.nid = S.nets[0].id; fillNetSel();
    $('#netSel').onchange = e => guard(null, async () => { S.nid = +e.target.value; S.metric = S.nets.find(n => n.id === S.nid).default_metric; $('#metricSel').value = S.metric; await loadNetwork(); render(); });
    $('#metricSel').onchange = e => guard(null, async () => { S.metric = e.target.value; await refreshAnalysis(); render(); });
    await loadNetwork(); S.view = VIEWS[location.hash.slice(1)] ? location.hash.slice(1) : 'overview'; render();
  } catch (e) { $('#view').innerHTML = `<div class="banner bad"><b>Cannot reach the API.</b> ${esc(e.message)} Start the backend with <code>python run.py</code>.</div>`; }
}
boot();
