# CHAPTER 5. CONCLUSION AND FUTURE WORK

## 5.1 Conclusion

Meridian demonstrates how a logistics network can be modelled as a directed weighted graph and explored through complementary shortest-path data structures. The active representation combines database-derived edge tuples with dictionary-backed adjacency lists. Heap Dijkstra uses a priority queue and is appropriate for sparse, non-negative selected weights; the array variant shows the cost of linear minimum selection; Bellman–Ford supports negative edges and reports negative cycles. Predecessor tracking turns distances into explainable paths.

The Flask/SQLite application integrates these algorithms with metric-specific routing, graph analysis, API validation, scenario management, benchmarking and analytics. Source inspection and local tests reproduced the 25-vertex, 102-edge Standard network, its density/connectivity metrics, mode aggregates and CAI-to-MEX cost-optimal path. The repository's 25 automated tests passed. The result is a working instructional platform and a concrete basis for discussing algorithmic assumptions, not an operational logistics system.

The main limitations are synthetic inputs, single-metric optimization, static weights, no live carrier or traffic feeds, no time-dependent paths, no authentication, and machine-sensitive timing results. The reported graph properties describe a generated sample; average delivery values are computed path summaries, not observed service levels. No client, survey, real-user test or production performance finding is asserted.

## 5.2 Future Work

1. **Dynamic routing:** update weights after closures, incidents or schedules and invalidate/recompute affected paths.
2. **Larger graphs:** profile memory and latency, avoid full graph reconstruction where justified, and evaluate indexed priority queues or specialized preprocessing.
3. **Additional algorithms:** compare A* with an admissible geographic heuristic, Johnson's algorithm for many-source queries with negative edges but no negative cycles, and bidirectional search for suitable non-negative graphs.
4. **Real data integration:** add licensed network, timetable and tariff sources with provenance, freshness timestamps and explicit uncertainty. Do not mix synthetic backhaul credits with physical costs.
5. **Multi-objective planning:** expose Pareto trade-offs or an explicitly normalized weighted objective for cost, distance and time rather than silently combining them.
6. **Time-dependent routing:** represent travel-time functions and departure schedules instead of one static edge time.
7. **Quality and security:** add authentication/authorization, server-side operational controls, privacy review, API abuse limits and threat-informed testing before any deployment with sensitive data.
8. **Experimental rigor:** repeat benchmarks on documented hardware/runtime, add warm-up and variability summaries, and separate algorithm work from API/serialization overhead.

These are proposals, not features currently present in the repository.
