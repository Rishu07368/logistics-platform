"""Route calculation, alternative routes, algorithm comparison and scaling benchmarks."""
import statistics

from ..algorithms.analysis import COMPLEXITY
from ..algorithms.bellman_ford import bellman_ford
from ..algorithms.common import INF
from ..algorithms.dijkstra import dijkstra
from ..data.generators import random_edges, worst_case_chain
from ..db import repository as repo
from .errors import ApiError
from .graph import UNITS, describe_path, load_graph, metric_column, run_algorithm


def _clean(x):
    return None if x in (INF, -INF) else x


def _stats(res):
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.stats.items()}


def _find_alternatives(graph, algorithm, metric, source, target, best_path, best_total, limit=3):
    """Single-link-failure analysis: drop each hop of the best path and re-solve."""
    seen, alts = {tuple(best_path)}, []
    for a, b in zip(best_path, best_path[1:]):
        trimmed = graph.__class__(graph.network, graph.locations,
                                  [r for r in graph.routes if (r["src"], r["dst"]) != (a, b)])
        try:
            res = run_algorithm(trimmed, algorithm, metric, source)
        except ApiError:
            continue
        path = None if res.negative_cycle else res.path_to(target)
        if path and tuple(path) not in seen:
            seen.add(tuple(path))
            alts.append({"path": path, "total": round(res.dist[target], 2),
                         "extra": round(res.dist[target] - best_total, 2), "avoids": f"{a}\u2192{b}"})
    alts.sort(key=lambda x: x["total"])
    for alt in alts:
        alt["hops"], alt["totals"] = describe_path(graph, alt["path"])
    return alts[:limit]


def calculate_route(conn, network_id, source, target, algorithm, metric, alternatives=False):
    graph = load_graph(conn, network_id)
    metric_column(metric)
    graph.require_node(source, "source")
    graph.require_node(target, "destination")
    if algorithm == "auto":
        _, rec = graph.recommendation(metric)
        algorithm = rec["algorithm"] or "bellman_ford"      # invalid graphs: BF reports the cycle
    res = run_algorithm(graph, algorithm, metric, source)
    out = {"network_id": network_id, "algorithm": res.algorithm, "metric": metric, "unit": UNITS[metric],
           "source": source, "target": target, "stats": _stats(res), "alternatives": [],
           "path": None, "hops": [], "totals": None, "total": None, "message": None}
    if res.negative_cycle:
        out["status"] = "negative_cycle"
        out["negative_cycle"] = {"nodes": res.negative_cycle, "weight": res.negative_cycle_weight,
                                 "affected_count": len(res.affected)}
        if target in res.affected:
            out["message"] = ("A negative-weight cycle is reachable from the source and can reach the "
                              "destination, so the shortest distance is \u2212\u221e. No finite optimal route exists.")
        else:
            out["message"] = ("A negative cycle is reachable from the source, but it cannot reach this "
                              "destination, so the finite shortest path below is still valid.")
            path = res.path_to(target)
            if path:
                out["status"] = "ok_with_cycle"
    else:
        out["status"] = "ok"
    path = res.path_to(target) if out["status"] in ("ok", "ok_with_cycle") else None
    if path:
        out["path"], out["total"] = path, round(res.dist[target], 2)
        out["hops"], out["totals"] = describe_path(graph, path)
        if alternatives and len(path) > 1:
            out["alternatives"] = _find_alternatives(graph, algorithm, metric, source, target, path, out["total"])
    elif out["status"] in ("ok", "ok_with_cycle"):
        out["status"], out["message"] = "unreachable", "No route connects these two locations."
    repo.log_run(conn, network_id, res.algorithm, metric, source, target, out["status"], out["total"], res.stats)
    conn.commit()
    return out


def compare_algorithms(conn, network_id, source, target, metric, repeats=5, force_dijkstra=False):
    """Run Dijkstra (both variants) and Bellman-Ford on identical input."""
    graph = load_graph(conn, network_id)
    metric_column(metric)
    graph.require_node(source, "source")
    graph.require_node(target, "destination")
    props, rec = graph.recommendation(metric)
    repeats = max(1, min(int(repeats), 50))
    rows = []
    for algo in ("dijkstra_heap", "dijkstra_array", "bellman_ford"):
        row = {"algorithm": algo, **COMPLEXITY[algo], "applicable": True, "forced": False}
        try:
            res = run_algorithm(graph, algo, metric, source)
        except ApiError as exc:
            row.update(applicable=False, reason=exc.message)
            if not (force_dijkstra and exc.code == "NEGATIVE_WEIGHTS"):
                rows.append(row)
                continue
            res, row["forced"] = run_algorithm(graph, algo, metric, source, validate=False), True
        times = [res.stats["time_ms"]]
        for _ in range(repeats - 1):
            times.append(run_algorithm(graph, algo, metric, source, validate=not row["forced"]).stats["time_ms"])
        path = None if res.negative_cycle else res.path_to(target)
        row.update(path=path, total=_clean(round(res.dist[target], 2)) if res.dist[target] not in (INF, -INF) else None,
                   stats=_stats(res), median_ms=round(statistics.median(times), 4),
                   min_ms=round(min(times), 4), repeats=repeats,
                   negative_cycle=res.negative_cycle, early_termination=res.stats.get("early_termination"))
        rows.append(row)
    ran = [r for r in rows if r.get("stats") and not r["forced"]]
    valid_totals = {r["total"] for r in ran if r["total"] is not None}
    forced = next((r for r in rows if r["forced"]), None)
    bf = next((r for r in rows if r["algorithm"] == "bellman_ford" and r.get("stats")), None)
    return {
        "network_id": network_id, "source": source, "target": target, "metric": metric, "unit": UNITS[metric],
        "properties": props, "recommendation": rec, "rows": rows,
        "agreement": len(valid_totals) <= 1 and len(ran) > 1,
        "forced_dijkstra_wrong": bool(forced and bf and forced["total"] != bf["total"]),
        "note": "Timings are wall-clock medians of this Python implementation on this machine; "
                "compare ratios, not absolute values.",
    }


def benchmark(sizes=None, repeats=3, avg_degree=4, seed=1):
    """Scaling experiment on generated graphs: Dijkstra (heap, array) vs Bellman-Ford."""
    sizes = sorted({int(s) for s in (sizes or [25, 50, 100, 200, 400, 800])})
    if not sizes or sizes[0] < 3 or sizes[-1] > 2000:
        raise ApiError("sizes must be integers between 3 and 2000", 400, "INVALID_SIZES")
    repeats = max(1, min(int(repeats), 10))
    if not 1 <= int(avg_degree) <= 12:
        raise ApiError("avg_degree must be between 1 and 12", 400, "INVALID_DEGREE")
    points = []
    for n in sizes:
        for graph_type, (nodes, edges) in (("random", random_edges(n, int(avg_degree), seed)),
                                           ("bf_worst_case", worst_case_chain(n))):
            for algo in ("dijkstra_heap", "dijkstra_array", "bellman_ford"):
                runs = []
                for _ in range(repeats):
                    if algo == "bellman_ford":
                        runs.append(bellman_ford(nodes, edges, nodes[0]))
                    else:
                        runs.append(dijkstra(nodes, edges, nodes[0], "heap" if algo.endswith("heap") else "array"))
                r = runs[0]
                points.append({
                    "vertices": n, "edges": len(edges), "graph": graph_type, "algorithm": algo,
                    "median_ms": round(statistics.median(x.stats["time_ms"] for x in runs), 4),
                    "relaxations": r.stats["relaxations"], "iterations": r.stats["iterations"],
                    "edge_checks": r.stats["edge_checks"]})
    theory = [{"vertices": p["vertices"], "edges": p["edges"], "graph": p["graph"]} for p in points
              if p["algorithm"] == "bellman_ford"]
    import math
    for t in theory:
        v, e = t["vertices"], t["edges"]
        t.update(v_squared=v * v, v_plus_e_log_v=round((v + e) * math.log2(max(v, 2))), v_times_e=v * e)
    return {"points": points, "theory": theory, "repeats": repeats, "seed": seed,
            "note": "Random graphs let Bellman-Ford stop early (few passes). The worst-case chain forces "
                    "V\u22121 passes and shows the true O(V\u00b7E) growth."}
