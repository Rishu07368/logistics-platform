"""Loads a stored network into algorithm-ready form and dispatches algorithms."""
from ..algorithms.analysis import graph_properties, recommend
from ..algorithms.bellman_ford import bellman_ford
from ..algorithms.common import NegativeWeightError
from ..algorithms.dijkstra import dijkstra
from ..db import repository as repo
from .errors import ApiError

METRICS = {"cost": "cost_usd", "distance": "distance_km", "time": "time_hours"}
UNITS = {"cost": "USD", "distance": "km", "time": "h"}
ALGORITHMS = ("dijkstra_heap", "dijkstra_array", "bellman_ford")


def metric_column(metric):
    if metric not in METRICS:
        raise ApiError(f"metric must be one of {sorted(METRICS)}", 400, "INVALID_METRIC")
    return METRICS[metric]


class GraphData:
    def __init__(self, network, locations, routes):
        self.network, self.locations, self.routes = network, locations, routes
        self.nodes = [l["code"] for l in locations]
        self.by_code = {l["code"]: l for l in locations}
        self.route_map = {(r["src"], r["dst"]): r for r in routes}

    def edges(self, metric):
        col = metric_column(metric)
        return [(r["src"], r["dst"], r[col]) for r in self.routes]

    def require_node(self, code, label="location"):
        if code not in self.by_code:
            raise ApiError(f"Unknown {label}: {code!r}", 404, "UNKNOWN_LOCATION")

    def properties(self, metric):
        return graph_properties(self.nodes, self.edges(metric))

    def recommendation(self, metric):
        props = self.properties(metric)
        return props, recommend(props)


def load_graph(conn, network_id):
    net = repo.get_network(conn, network_id)
    if not net:
        raise ApiError(f"Network {network_id} not found", 404, "UNKNOWN_NETWORK")
    return GraphData(net, repo.list_locations(conn, network_id), repo.list_routes(conn, network_id))


def run_algorithm(graph, algorithm, metric, source, validate=True):
    edges = graph.edges(metric)
    if algorithm == "bellman_ford":
        return bellman_ford(graph.nodes, edges, source)
    if algorithm in ("dijkstra_heap", "dijkstra_array"):
        variant = "heap" if algorithm == "dijkstra_heap" else "array"
        try:
            return dijkstra(graph.nodes, edges, source, variant, validate=validate)
        except NegativeWeightError as exc:
            props, rec = graph.recommendation(metric)
            raise ApiError(
                f"Dijkstra cannot run on the '{metric}' metric: {len(exc.negative_edges)} negative edge(s). "
                f"{rec['headline']}.", 422, "NEGATIVE_WEIGHTS",
                negative_edges=[{"from": u, "to": v, "weight": w} for u, v, w in exc.negative_edges[:25]],
                recommendation=rec)
    raise ApiError(f"algorithm must be one of {list(ALGORITHMS)}", 400, "INVALID_ALGORITHM")


def best_effort(graph, metric, source):
    """Run whichever valid algorithm the data allows (used by analytics); None if impossible."""
    edges = graph.edges(metric)
    if all(w >= 0 for _, _, w in edges):
        return dijkstra(graph.nodes, edges, source)
    res = bellman_ford(graph.nodes, edges, source)
    return None if res.negative_cycle else res


def describe_path(graph, path):
    """Per-hop details and totals across all three metrics."""
    hops, totals = [], {"distance_km": 0, "cost_usd": 0, "time_hours": 0}
    for a, b in zip(path, path[1:]):
        r = graph.route_map[(a, b)]
        hops.append({"from": a, "to": b, "mode": r["mode"], "distance_km": r["distance_km"],
                     "cost_usd": r["cost_usd"], "time_hours": r["time_hours"]})
        for k in totals:
            totals[k] += r[k]
    return hops, {k: round(v, 2) for k, v in totals.items()}
