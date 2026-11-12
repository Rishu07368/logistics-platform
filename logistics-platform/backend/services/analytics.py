"""Dashboard summary and logistics analytics (all figures computed from stored data)."""
import random
from collections import defaultdict

from ..db import repository as repo
from .graph import best_effort, load_graph


def _avg_shortest(graph, metric, sample=25):
    rng = random.Random(0)
    sources = graph.nodes if len(graph.nodes) <= sample else rng.sample(graph.nodes, sample)
    vals, per_source = [], {}
    for s in sources:
        res = best_effort(graph, metric, s)
        if res is None:
            return None, {}
        per_source[s] = res
        vals += [d for t, d in res.dist.items() if t != s and abs(d) != float("inf")]
    return (round(sum(vals) / len(vals), 2) if vals else None), per_source


def summary(conn, nid):
    g = load_graph(conn, nid)
    props = g.properties("cost")
    kinds = defaultdict(int)
    for l in g.locations:
        kinds[l["kind"]] += 1
    corridors = {frozenset((r["src"], r["dst"])) for r in g.routes}
    avg_time, _ = _avg_shortest(g, "time")
    spend = sum(r["cost_usd"] * r["weekly_trips"] for r in g.routes)
    return {
        "network": g.network,
        "locations": len(g.locations),
        "countries": len({l["country"] for l in g.locations}),
        "warehouses": kinds["warehouse"], "distribution_centers": kinds["distribution_center"],
        "destinations": kinds["destination"], "cities": kinds["city"],
        "directed_routes": len(g.routes), "corridors": len(corridors),
        "packages": sum(l["packages"] for l in g.locations),
        "avg_delivery_hours": avg_time,
        "weekly_spend_usd": round(spend),
        "connectivity": {k: props[k] for k in ("density", "avg_out_degree", "weak_components", "strong_components")}
        | {"strongly_connected": props["strong_components"] == 1 and props["vertices"] > 0},
        "negative_edge_count": props["negative_edge_count"], "has_negative_cycle": props["has_negative_cycle"],
    }


def analytics(conn, nid, metric="cost"):
    g = load_graph(conn, nid)
    by_mode = defaultdict(lambda: {"routes": 0, "cost": 0.0, "weekly_spend": 0.0, "time": 0.0, "dist": 0.0})
    for r in g.routes:
        m = by_mode[r["mode"]]
        m["routes"] += 1
        m["cost"] += r["cost_usd"]
        m["time"] += r["time_hours"]
        m["dist"] += r["distance_km"]
        m["weekly_spend"] += r["cost_usd"] * r["weekly_trips"]
    modes = [{"mode": k, "routes": v["routes"], "avg_cost": round(v["cost"] / v["routes"], 1),
              "avg_time": round(v["time"] / v["routes"], 1), "weekly_spend": round(v["weekly_spend"]),
              "cost_per_km": round(v["cost"] / v["dist"], 3) if v["dist"] else None}
             for k, v in sorted(by_mode.items())]

    efficiency, note = [], None
    avg, per_source = _avg_shortest(g, metric, sample=40)
    if not per_source:
        note = "Efficiency analysis skipped: the selected metric has a negative-weight cycle."
    else:
        col = {"cost": "cost_usd", "distance": "distance_km", "time": "time_hours"}[metric]
        for r in g.routes:
            res = per_source.get(r["src"])
            if res and r[col] > 0 and res.dist[r["dst"]] != float("inf"):
                efficiency.append({"src": r["src"], "dst": r["dst"], "direct": r[col],
                                   "best": round(res.dist[r["dst"]], 2),
                                   "efficiency": round(res.dist[r["dst"]] / r[col], 3),
                                   "via": res.path_to(r["dst"])})
        efficiency.sort(key=lambda x: x["efficiency"])
    deg_in, deg_out = defaultdict(int), defaultdict(int)
    for r in g.routes:
        deg_out[r["src"]] += 1
        deg_in[r["dst"]] += 1
    hubs = sorted(({"code": c, "name": g.by_code[c]["name"], "in": deg_in[c], "out": deg_out[c],
                    "packages": g.by_code[c]["packages"]} for c in g.nodes),
                  key=lambda h: (-(h["in"] + h["out"]), h["code"]))[:10]
    per_algo, recent = repo.run_summary(conn, nid)
    return {"metric": metric, "modes": modes, "inefficient_direct_routes": efficiency[:10],
            "efficiency_note": note, "avg_shortest": avg, "hubs": hubs,
            "properties": g.properties(metric), "algorithm_report": per_algo, "recent_runs": recent}
