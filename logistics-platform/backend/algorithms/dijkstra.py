"""Dijkstra's algorithm: binary-heap variant and O(V^2) array variant."""
import heapq
from time import perf_counter

from .common import INF, NegativeWeightError, ShortestPathResult, build_adjacency


def dijkstra(nodes, edges, source, variant="heap", validate=True):
    """Single-source shortest paths.

    variant="heap"  -> priority queue, O((V + E) log V)
    variant="array" -> linear minimum scan, O(V^2)
    validate=False is only used by the comparison lab to demonstrate why
    Dijkstra is invalid on negative edges; every node is still settled once.
    """
    if source not in set(nodes):
        raise KeyError(f"Unknown source node: {source}")
    if validate:
        negative = [(u, v, w) for u, v, w in edges if w < 0]
        if negative:
            raise NegativeWeightError(negative)

    adj = build_adjacency(nodes, edges)
    dist = {n: INF for n in nodes}
    prev = {n: None for n in nodes}
    dist[source] = 0
    stats = {"relaxations": 0, "edge_checks": 0, "iterations": 0,
             "heap_pushes": 0, "stale_pops": 0, "min_scans": 0}
    settled = set()

    t0 = perf_counter()
    if variant == "heap":
        heap = [(0, source)]
        stats["heap_pushes"] = 1
        while heap:
            d, u = heapq.heappop(heap)
            stats["iterations"] += 1               # one pop = one iteration
            if u in settled:
                stats["stale_pops"] += 1           # lazy deletion
                continue
            settled.add(u)
            for v, w in adj[u]:
                stats["edge_checks"] += 1
                if v in settled:
                    continue
                nd = d + w
                if nd < dist[v]:
                    dist[v], prev[v] = nd, u
                    heapq.heappush(heap, (nd, v))
                    stats["relaxations"] += 1
                    stats["heap_pushes"] += 1
    elif variant == "array":
        remaining = set(nodes)
        while remaining:
            u = min(remaining, key=dist.__getitem__)
            stats["min_scans"] += len(remaining)   # the O(V) scan per round
            if dist[u] == INF:
                break
            remaining.discard(u)
            settled.add(u)
            stats["iterations"] += 1
            for v, w in adj[u]:
                stats["edge_checks"] += 1
                if v in settled:
                    continue
                nd = dist[u] + w
                if nd < dist[v]:
                    dist[v], prev[v] = nd, u
                    stats["relaxations"] += 1
    else:
        raise ValueError("variant must be 'heap' or 'array'")
    stats["time_ms"] = (perf_counter() - t0) * 1000

    name = "dijkstra_heap" if variant == "heap" else "dijkstra_array"
    return ShortestPathResult(name, source, dist, prev, stats)
