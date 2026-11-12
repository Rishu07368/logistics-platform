"""Graph property analysis and the rule-based algorithm recommender."""
from .bellman_ford import bellman_ford

COMPLEXITY = {
    "dijkstra_heap": {"label": "Dijkstra (binary heap)", "time": "O((V + E) log V)",
                      "space": "O(V + E)", "negative_edges": False, "negative_cycle_detection": False},
    "dijkstra_array": {"label": "Dijkstra (array scan)", "time": "O(V\u00b2)",
                       "space": "O(V + E)", "negative_edges": False, "negative_cycle_detection": False},
    "bellman_ford": {"label": "Bellman-Ford", "time": "O(V \u00b7 E)",
                     "space": "O(V + E)", "negative_edges": True, "negative_cycle_detection": True},
}


def weak_components(nodes, edges):
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for u, v, _ in edges:
        parent[find(u)] = find(v)
    return len({find(n) for n in nodes})


def strong_components(nodes, edges):
    """Kosaraju, iterative. Returns the number of strongly connected components."""
    adj = {n: [] for n in nodes}
    radj = {n: [] for n in nodes}
    for u, v, _ in edges:
        adj[u].append(v)
        radj[v].append(u)
    order, seen = [], set()
    for s in nodes:
        if s in seen:
            continue
        seen.add(s)
        stack = [(s, iter(adj[s]))]
        while stack:
            node, it = stack[-1]
            for nxt in it:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append((nxt, iter(adj[nxt])))
                    break
            else:
                order.append(node)
                stack.pop()
    comps, seen = 0, set()
    for s in reversed(order):
        if s in seen:
            continue
        comps += 1
        seen.add(s)
        stack = [s]
        while stack:
            for nxt in radj[stack.pop()]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    return comps


def graph_properties(nodes, edges):
    v, e = len(nodes), len(edges)
    negative = [(a, b, w) for a, b, w in edges if w < 0]
    cycle_result = bellman_ford(nodes, edges, source=None) if nodes else None
    cycle = cycle_result.negative_cycle if cycle_result else None
    return {
        "vertices": v, "edges": e,
        "density": round(e / (v * (v - 1)), 5) if v > 1 else 0,
        "avg_out_degree": round(e / v, 2) if v else 0,
        "negative_edge_count": len(negative),
        "min_weight": min((w for _, _, w in edges), default=None),
        "negative_edges": [{"from": a, "to": b, "weight": w} for a, b, w in negative[:25]],
        "has_negative_cycle": bool(cycle),
        "negative_cycle": cycle,
        "negative_cycle_weight": cycle_result.negative_cycle_weight if cycle else None,
        "weak_components": weak_components(nodes, edges) if v else 0,
        "strong_components": strong_components(nodes, edges) if v else 0,
    }


def recommend(props, large_threshold=100):
    """Derive a recommendation strictly from measured graph properties."""
    v, e = props["vertices"], props["edges"]
    if props["has_negative_cycle"]:
        cyc = " \u2192 ".join(props["negative_cycle"] + [props["negative_cycle"][0]])
        return {
            "status": "invalid", "algorithm": None,
            "headline": "No finite shortest path is guaranteed",
            "reasons": [
                f"A negative-weight cycle exists: {cyc} (total {props['negative_cycle_weight']:g}).",
                "Every trip around the cycle lowers the total, so the shortest distance tends to "
                "\u2212\u221e for any node reachable from the cycle.",
                "Bellman-Ford can detect the cycle, but no algorithm can return a finite shortest path through it.",
                "Fix: remove or raise the weights of the cycle's edges, then re-run.",
            ]}
    if props["negative_edge_count"]:
        return {"status": "ok", "algorithm": "bellman_ford", "headline": "Use Bellman-Ford",
                "reasons": [
                    f"{props['negative_edge_count']} negative edge(s) present and no negative cycle.",
                    "Dijkstra's greedy settling assumes a settled node can never be improved; negative "
                    "edges break that, so Dijkstra is invalid here.",
                    "Bellman-Ford relaxes every edge up to V\u22121 times and stays correct: O(V\u00b7E).",
                ]}
    reasons = ["All weights are non-negative, so Dijkstra's precondition holds."]
    if v and e > v * v / 4 and v <= 2000:
        reasons.append(f"Graph is dense (E = {e}, V\u00b2/4 = {v * v // 4}): the O(V\u00b2) array variant "
                       "matches or beats the heap here.")
        algo = "dijkstra_array"
    else:
        algo = "dijkstra_heap"
        reasons.append(f"Graph is sparse (avg out-degree {props['avg_out_degree']}): "
                       "O((V + E) log V) is far below O(V\u00b7E).")
    if v >= large_threshold:
        reasons.append(f"With {v} vertices, Bellman-Ford's V\u00b7E growth would become the bottleneck.")
    reasons.append("Bellman-Ford would also be correct but does unnecessary work without negative edges.")
    return {"status": "ok", "algorithm": algo,
            "headline": "Use Dijkstra" + (" (priority queue)" if algo == "dijkstra_heap" else " (array)"),
            "reasons": reasons}
