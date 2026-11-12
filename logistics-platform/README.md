# Meridian: Multinational Logistics Route Optimization Platform

Assignment 3, Chapter 3.3. A full-stack platform that models a global logistics network as a weighted directed graph and
compares **Dijkstra's** and **Bellman-Ford** shortest-path algorithms on it, with a real API, SQLite database and an
interactive dashboard.

## Quick start (Windows / macOS / Linux, Python 3.10+)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                      # backend + frontend, open http://127.0.0.1:5000
```

The first start creates `logistics.db` and seeds four scenarios automatically. Delete the file to start over.
Optional settings: copy `.env.example` to `.env` (`HOST`, `PORT`, `DEBUG`, `DATABASE_PATH`).
The frontend is plain HTML/CSS/JS served by Flask, so there is no separate frontend build or startup step.
Charts and the map are hand-written SVG; no internet connection is needed.

## Tests

```bash
python -m pytest -q                # 25 tests: algorithms + full API
python tests/e2e_ui.py             # optional browser test; needs the server running and
                                   # pip install playwright && playwright install chromium
```

Algorithm tests use textbook examples (CLRS Fig. 24.4 and 24.6) with known distances, negative-cycle detection (reachable and
unreachable cycles), early termination, 40 random graphs cross-checked across all three implementations, and a check that
Dijkstra refuses negative edges. API tests cover all four scenarios, validation, CRUD, generation and error codes.

## Project structure

```
backend/
  algorithms/   dijkstra.py (heap + array), bellman_ford.py, analysis.py (properties, recommender), common.py
  services/     graph.py (load + dispatch), routing.py (routes, compare, benchmark), network.py (CRUD), analytics.py
  routes/       api.py            HTTP layer only
  db/           database.py (schema), repository.py (all SQL)
  data/         seed.py (4 scenarios), generators.py (network + benchmark graph generators)
frontend/       index.html, css/style.css, js/{app,map,charts}.js
tests/          test_algorithms.py, test_api.py, e2e_ui.py
run.py          entry point
```
Layers only call downward: routes -> services -> algorithms / repository. Algorithms are pure functions with no I/O.

## Data model

- Vertices are locations (city, warehouse, distribution center, destination) with coordinates and package counts.
- Edges are **directed** routes with three weights: `cost_usd` (per shipment batch), `distance_km`, `time_hours`.
  Two-way corridors are stored as two directed rows, because negative weights are only meaningful with direction.
- **The optimization metric is explicit**: choose cost, time or distance in the sidebar. It selects which weight the
  algorithms see, so the same network can be valid for Dijkstra on distance and invalid on cost.
- Sample weights come from great-circle distance, a mode path factor and per-mode speed, rate and handling constants
  (`data/generators.py`), so all values are reproducible.

## Scenarios

| Scenario | Contents |
|---|---|
| Standard | 25 hubs, 102 directed routes, all positive |
| Negative edges | 4 routes with backhaul credits (negative cost), no negative cycle |
| Negative cycle | Singapore<->Mumbai carry large negative test costs, forming a cycle |
| Large | 300 generated nodes, 1,150 directed routes (seeded) |

Negative transportation costs are an **algorithm-testing scenario**, not a realistic model of ordinary physical costs.

## Algorithms

| | Time | Space | Negative edges | Negative cycle detection |
|---|---|---|---|---|
| Dijkstra, binary heap | O((V+E) log V) | O(V+E) | no (validated, HTTP 422) | no |
| Dijkstra, array scan | O(V^2) | O(V+E) | no (validated, HTTP 422) | no |
| Bellman-Ford | O(V*E), early exit | O(V+E) | yes | yes (cycle returned) |

Both report relaxations, iterations, edge checks and wall-clock time. Bellman-Ford marks every node reachable from a negative
cycle as -infinity and refuses to return a path to it. Alternative routes are computed by removing each link of the best
route in turn and re-solving.

**Recommender** (`algorithms/analysis.py`) derives its answer from measured graph properties: it runs a virtual-source
Bellman-Ford over the whole graph to find any negative cycle, counts negative edges, and checks density. Result: negative cycle
-> no finite shortest path guaranteed; negative edges -> Bellman-Ford; otherwise Dijkstra (heap, or array when dense).

## API summary

| Method and path | Purpose |
|---|---|
| `GET /api/networks` / `POST /api/networks/generate` / `DELETE /api/networks/<id>` / `POST .../reset` | scenarios |
| `GET /api/networks/<id>/graph` `/summary` `/analysis?metric=` `/analytics?metric=` | data and dashboards |
| `POST /api/networks/<id>/route` | `{source,target,algorithm,metric,alternatives}`; algorithm is `dijkstra_heap`, `dijkstra_array`, `bellman_ford` or `auto` |
| `POST /api/networks/<id>/compare` | identical input to all algorithms; `force_dijkstra` demonstrates failure on negative edges |
| `POST /api/benchmark` | scaling experiment on generated graphs (`sizes`, `repeats`, `avg_degree`) |
| `POST /api/networks/<id>/locations`, `PUT/DELETE /api/locations/<id>` | locations |
| `POST /api/networks/<id>/routes`, `PUT/DELETE /api/routes/<id>` | routes (`bidirectional`, auto-filled weights) |

Errors return JSON `{error, code, ...}` with 400/404/409/422 as appropriate.

## Using the app

1. **Overview**: KPIs, global map, live recommendation. Click two locations to set source and destination.
2. **Route optimizer**: pick algorithm and metric, view the route, hop table, execution counters and alternatives.
3. **Comparison lab**: head-to-head table on one route, plus a scaling benchmark with measured charts and theory curves.
   The benchmark includes a Bellman-Ford worst case (reverse-ordered chain) so O(V*E) growth is visible; on random graphs
   early termination makes Bellman-Ford look much better than its bound, and the lab shows both honestly.
4. **Network manager**: add/remove locations and routes, edit weights (try negative costs), generate networks, reset scenarios.
5. **Analytics**: spend and time by mode, route efficiency, hubs, connectivity, and an algorithm performance report built from stored runs.
6. **Algorithms explained**: theory, limitations, and when to use which.

## Notes and limitations

- Timings are from a Python implementation on your machine. Compare ratios and growth, not absolute milliseconds.
- For large non-negative networks Dijkstra with a priority queue is preferable; Bellman-Ford is appropriate when negative
  weights must be supported. Real-time logistics systems typically use precomputation (contraction hierarchies), A*, and
  incremental updates instead of re-running either algorithm for each small change.
- The map is a stylised equirectangular projection. Routing always runs on the stored backend graph, never on the picture.
- Multiple routes between the same ordered pair of locations are not supported (one route per direction).
