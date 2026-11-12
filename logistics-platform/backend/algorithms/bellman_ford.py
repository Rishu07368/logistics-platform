"""Bellman-Ford with early termination and negative-cycle extraction."""
from time import perf_counter

from .common import INF, ShortestPathResult, build_adjacency


def bellman_ford(nodes, edges, source=None):
    """Single-source shortest paths allowing negative weights.

    source=None uses a virtual super-source (all distances start at 0), which
    detects a negative cycle anywhere in the graph, reachable or not.
    """
    if source is not None and source not in set(nodes):
        raise KeyError(f"Unknown source node: {source}")
    n = len(nodes)
    dist = {x: (0 if source is None else INF) for x in nodes}
    prev = {x: None for x in nodes}
    if source is not None:
        dist[source] = 0
    stats = {"relaxations": 0, "edge_checks": 0, "iterations": 0,
             "early_termination": False, "max_iterations": 0}

    t0 = perf_counter()
    max_passes = n - 1 if source is not None else n
    stats["max_iterations"] = max_passes
    ran_all = True
    for _ in range(max_passes):
        changed = False
        stats["iterations"] += 1
        for u, v, w in edges:
            stats["edge_checks"] += 1
            if dist[u] != INF and dist[u] + w < dist[v]:
                dist[v], prev[v] = dist[u] + w, u
                stats["relaxations"] += 1
                changed = True
        if not changed:                          # early termination
            stats["early_termination"] = True
            ran_all = False
            break

    cycle = None
    if ran_all:                                  # extra pass: any relaxation => cycle
        for u, v, w in edges:
            stats["edge_checks"] += 1
            if dist[u] != INF and dist[u] + w < dist[v]:
                prev[v] = u
                cycle = _extract_cycle(prev, v, n)
                break
    stats["time_ms"] = (perf_counter() - t0) * 1000

    result = ShortestPathResult("bellman_ford", source, dist, prev, stats)
    if cycle:
        result.negative_cycle = cycle
        result.negative_cycle_weight = _cycle_weight(cycle, edges)
        result.affected = _reachable_from(cycle, build_adjacency(nodes, edges))
        for x in result.affected:
            result.dist[x] = -INF
    return result


def _extract_cycle(prev, start, n):
    x = start
    for _ in range(n):                           # n steps back lands inside the cycle
        if prev[x] is None:
            return [start]
        x = prev[x]
    cycle, cur = [x], prev[x]
    while cur != x and len(cycle) <= n:
        cycle.append(cur)
        cur = prev[cur]
    cycle.reverse()
    return cycle                                 # forward order; closes back to cycle[0]


def _cycle_weight(cycle, edges):
    best = {}
    for u, v, w in edges:
        best[(u, v)] = min(w, best.get((u, v), INF))
    return sum(best[(cycle[i], cycle[(i + 1) % len(cycle)])] for i in range(len(cycle)))


def _reachable_from(starts, adj):
    seen, stack = set(starts), list(starts)
    while stack:
        for v, _ in adj[stack.pop()]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return seen
