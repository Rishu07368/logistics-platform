# Technical evidence log

## Verified Standard scenario (new isolated test database)

Using `create_app()` with a database under `project_report_output`, GET `/api/networks` and GET `/api/networks/<standard>/summary` returned 200. Seeded scenarios and sizes were Standard (25 locations, 102 route rows), Negative edges (25, 102), Negative cycle (25, 102), and Large (300, 1,150).

| Metric | Locally reproduced value | Interpretation |
|---|---:|---|
| Locations | 25 | Vertices |
| Countries | 19 | Unique country codes |
| Warehouses | 7 | Location kind `warehouse` |
| Distribution centres | 7 | Separate kind; not included in the warehouse count |
| Directed routes | 102 | Edges, not unique two-way corridors |
| Corridors | 51 | Unordered route pairs |
| Packages | 1,300,000 | Sum of static location package counts |
| Mean shortest delivery time | 108.27 h | Derived all-pairs mean for this 25-vertex network, not shipment telemetry |
| Weekly spend | $10,107,986 | Sum of synthetic route cost × weekly trips |
| Density | 0.17000 | 102/[25×24] |
| Average out-degree | 4.08 | 102/25 |
| Weak components | 1 | Edges treated as undirected for component membership |
| Strong components | 1 | Directed strongly connected |
| Negative edges | 0 | Standard metric is positive |

The locally reproduced analytics responses matched rounded supplied values: weekly spending $8,686,620 air, $164,290 rail, $826,000 road, and $431,076 sea; mean route times 14.5, 33.6, 25.6 and 276.4 hours; aggregate cost/km 6.87, 1.293, 1.907 and 0.467. The API computes mode mean time as an arithmetic mean of route rows, and cost/km as total cost / total distance. Rounded mode spending need not add to a rounded UI total.

## CAI to MEX route

The local API call `POST /api/networks/1/route` with `{source: CAI, target: MEX, algorithm: dijkstra_heap, metric: cost}` reproduced:

`CAI → MIL → FRA → HAM → NYC → HOU → MEX`

Total selected cost: **$15,616**; aggregated route distance: **16,770 km**; summed edge-time estimate: **540.6 h**; six directed hops. All six per-edge mode/distance/cost/time values matched the table in the project brief. These are synthetic route estimates generated from the sample network; distance, cost and time are distinct additive weights/totals.

## Algorithm comparison and timing provenance

The local test-client comparison returned the same $15,616 total and route for all three algorithms and 102 edge checks for each Dijkstra variant versus 510 for Bellman–Ford. A representative run returned median times 0.0209 ms (heap), 0.0280 ms (array) and 0.0633 ms (Bellman–Ford); a separate route call measured 0.0328 ms heap. These values are machine/runtime dependent and are recorded only as a local reproduction, not substituted for the prompt's screenshot-reported 0.086/0.116/0.264 ms.

The scaling numbers supplied in the project brief were not attached as local screenshot files, so they could not be visually transcribed/verified against the original images. The repository confirms that its benchmark sweeps V = 25, 50, 100, 200, 400, 800 on both deterministic positive random graphs and reverse-ordered Bellman–Ford worst-case chains, and records medians in milliseconds. In the report, user-supplied values are labelled as reported benchmark evidence and explicitly separated from independently reproduced run times.

## Automated validation

Project test run: `python -m pytest -q` in the application virtual environment: **25 passed in 5.70 seconds**. Tests cover known shortest-path examples, both Dijkstra variants, Bellman–Ford with negative edges/cycles, unreachable vertices, early termination, 40 generated cross-check graphs, route/analytics APIs, CRUD validation and benchmark endpoints.

## Limitations in evidence

- No hardware model, operating-system build, CPU, interpreter version for the supplied screen measurements, or controlled benchmark protocol was present in the screenshot evidence brief. No machine specifications are invented.
- The sample is synthetic and deterministic; it is not a live carrier feed or real shipment history.
- Testing did not mutate the existing application database or deployed production network records.
