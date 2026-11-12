"""Shared types for the shortest-path algorithms (pure Python, no I/O)."""
from dataclasses import dataclass, field
from typing import Optional

INF = float("inf")


class NegativeWeightError(ValueError):
    """Raised when Dijkstra is asked to run on a graph with negative edges."""

    def __init__(self, negative_edges):
        self.negative_edges = negative_edges
        super().__init__(
            f"Dijkstra's algorithm requires non-negative weights; "
            f"found {len(negative_edges)} negative edge(s)."
        )


@dataclass
class ShortestPathResult:
    algorithm: str
    source: Optional[str]
    dist: dict
    prev: dict
    stats: dict
    negative_cycle: Optional[list] = None
    negative_cycle_weight: Optional[float] = None
    affected: set = field(default_factory=set)  # nodes whose distance is -inf

    def path_to(self, target):
        """Reconstruct source -> target as a node list, or None if unusable."""
        if target in self.affected or self.dist.get(target, INF) == INF:
            return None
        path, cur, guard = [], target, len(self.dist) + 1
        while cur is not None and guard:
            path.append(cur)
            cur = self.prev[cur]
            guard -= 1
        path.reverse()
        return path if path and path[0] == self.source else None


def build_adjacency(nodes, edges):
    adj = {n: [] for n in nodes}
    for u, v, w in edges:
        adj[u].append((v, w))
    return adj
