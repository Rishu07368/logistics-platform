# Repository analysis

## Scope and integrity

Inspected the authoritative working tree at `../logistics-platform/` (nested application folder). Its Git worktree was clean; the only untracked item in the parent folder was the user-provided `Report_Format.pdf`. Application source and its existing `logistics.db` were not edited. A separate evidence database was initialized under this report-output directory.

## Application structure

- `run.py` invokes the Flask application factory.
- `backend/app.py` (`create_app`) initializes SQLite schema/seeds missing built-in networks, registers the API blueprint, maps API errors to JSON, serves the static front end, and logs unexpected exceptions.
- `backend/routes/api.py` defines JSON endpoints and obtains request-scoped SQLite connections.
- `backend/services/` contains graph loading/dispatch, route/benchmark workflows, network CRUD and analytics.
- `backend/algorithms/` contains pure shortest-path functions and graph property/recommendation logic.
- `backend/db/` owns schema/connection setup and SQL repository operations.
- `backend/data/` provides deterministic scenarios and geographic/benchmark generators.
- `frontend/index.html`, `frontend/css/style.css`, and `frontend/js/{app,map,charts}.js` implement a single-page UI with hand-written SVG visualizations; there is no separate front-end build.
- `tests/` contains algorithm and API tests plus an optional Playwright UI script.

The dependency direction documented and observed is HTTP route → service → algorithm/repository; algorithms do not perform I/O.

## Verified implementation details

### Graph and data persistence

`backend/services/graph.py` defines `GraphData`, turns persisted rows into a node list, `by_code` dictionary and ordered-pair `route_map`, and selects one of three edge weights. `GraphData.edges(metric)` yields an edge list. `backend/algorithms/common.py::build_adjacency` creates a dictionary from each vertex to a list of outgoing `(neighbour, weight)` pairs for traversal. Thus the active shortest-path representation combines a repository-derived edge list with an adjacency-list dictionary; it is not an adjacency matrix.

`backend/db/database.py` creates `networks`, `locations`, `routes`, and `runs`; route/location indexes are defined. A route is directed. Uniqueness on `(network_id, src, dst)` limits each ordered pair to one edge; a bidirectional form is two rows. Distance must be non-negative at the SQL layer, while cost/time can be negative for test cases. Location coordinates/kinds/package counts have SQL checks. `backend/db/repository.py` parameterizes values for CRUD and run summaries.

### Algorithms and selection

- `backend/algorithms/dijkstra.py::dijkstra` validates the source and, by default, rejects negative selected weights. Heap mode uses Python `heapq`, a lazy priority queue, a settled set, stale-pop checks, adjacency traversal, distances and predecessors. Array mode repeatedly selects `min(remaining, key=dist.__getitem__)`; it stops once remaining vertices are unreachable.
- `backend/algorithms/bellman_ford.py::bellman_ford` scans the edge list for up to `V−1` source-based passes (or `V` passes for virtual-source global cycle detection), exits if a pass has no change, and conditionally runs an additional cycle check. It extracts cycle details, identifies reachable affected vertices and marks their distances negative infinity.
- `ShortestPathResult.path_to` in `common.py` reconstructs predecessor chains and rejects unreachable/negative-infinity destinations.
- `backend/algorithms/analysis.py::graph_properties` computes directed density `E/[V(V−1)]`, average out-degree `E/V`, negative edges, weak components (disjoint-set treatment of edges as undirected) and strong components (iterative Kosaraju). `recommend` chooses Bellman–Ford for negative edges, reports no finite shortest path when a negative cycle exists, and otherwise recommends heap Dijkstra for sparse networks or array Dijkstra above its coded density threshold.
- `backend/services/graph.py::run_algorithm` maps API identifiers to implementations and converts negative-weight rejection to an HTTP 422 API error. `backend/services/routing.py::calculate_route` reports the chosen metric, route totals for all three dimensions, hop details and optional single-link-failure alternatives. `compare_algorithms` compares both Dijkstra variants and Bellman–Ford on the same input.

The commonly cited heap bound `O((V+E) log V)` assumes a binary heap with lazy duplicate entries and a simple directed graph; the array form is worst-case `O(V²+E)`; Bellman–Ford is worst-case `O(VE)`, with an extra edge pass for cycle detection. The code stores graph, distances and predecessors in `O(V+E)` aggregate space. The array implementation's selection scans are `O(V²)`; it still stores the adjacency list.

### API and error handling

`backend/routes/api.py` exposes health/theory, scenario listing/generation/reset/deletion, graph/summary/analysis/analytics, route calculation, algorithm comparison, benchmark, and location/route CRUD endpoints. JSON bodies are checked by `body()`. Domain errors carry structured codes/status; the app handles 404/405 and logs unexpected exceptions before returning a generic 500 response. Network CRUD validates formats, enumerations, coordinate ranges, numeric ranges and duplicates.

### Generators and meaning of the data

`backend/data/seed.py` defines four built-in scenarios: Standard (25 locations, 102 directed rows), Negative edges (four negative test credits), Negative cycle (Singapore–Mumbai cycle), and Large (300 generated vertices). `backend/data/generators.py` derives example distances from haversine great-circle distance and mode factors, then calculates synthetic cost/time/trip weights. Negative cost values are explicitly test credits, not physical transport costs. Benchmark `random_edges` builds a connected positive-weight digraph at requested average degree; `worst_case_chain` orders chain edges in reverse to require repeated Bellman–Ford passes.

### Analytics and visual interface

`backend/services/analytics.py` computes weekly spend as `cost × weekly_trips`, per-mode arithmetic mean route time, aggregate cost divided by aggregate distance, route-efficiency comparisons and degree-based hubs. It samples up to 25/40 deterministic sources for shortest-path summaries/efficiency; the reported mean is model-derived, not observed shipment telemetry. `frontend/js/map.js` renders a stylized coordinate-based SVG projection; routing is computed from stored graph data, not from the map. `charts.js` draws charts without external chart dependencies. `app.js` implements view navigation, controls and API calls.

## Local verification

The existing project virtual environment ran `python -m pytest -q`: **25 passed**. A separate test-client database reproduced the Standard metrics and Cairo–Mexico City result. Detailed measured observations are in `TECHNICAL_EVIDENCE.md`.
