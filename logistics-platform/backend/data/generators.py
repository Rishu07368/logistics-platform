"""Deterministic generators: transport-mode physics, geographic networks, benchmark graphs."""
import math
import random

# speed km/h, cost per km, fixed cost, handling hours, path-length factor over great-circle, weekly trips
MODES = {
    "road": dict(speed=65, rate=1.8, fixed=150, handling=4, factor=1.25, trips=14),
    "rail": dict(speed=55, rate=1.1, fixed=250, handling=10, factor=1.2, trips=7),
    "sea": dict(speed=32, rate=0.35, fixed=900, handling=36, factor=1.3, trips=3),
    "air": dict(speed=750, rate=6.5, fixed=1800, handling=8, factor=1.0, trips=10),
}


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(a))


def route_metrics(mode, a, b):
    """Distance (km), cost (USD per shipment batch) and time (h) for a mode between two locations."""
    m = MODES[mode]
    dist = round(haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) * m["factor"])
    return {"distance_km": dist, "cost_usd": round(dist * m["rate"] + m["fixed"]),
            "time_hours": round(dist / m["speed"] + m["handling"], 1), "weekly_trips": m["trips"]}


def make_route(mode, a, b, note=""):
    return {"src": a["code"], "dst": b["code"], "mode": mode, "note": note, **route_metrics(mode, a, b)}


def both_ways(mode, a, b):
    return [make_route(mode, a, b), make_route(mode, b, a)]


REGIONS = [  # name, country, lat range, lon range, weight
    ("US", (25, 49), (-124, -72), 4), ("BR", (-33, -5), (-65, -38), 2), ("DE", (40, 58), (-5, 28), 4),
    ("ZA", (-30, 25), (-10, 38), 2), ("IN", (8, 40), (68, 120), 5), ("AU", (-37, -20), (115, 150), 1)]


def generate_network(n, seed=7):
    """Random geographic network with n locations; strongly connected, all weights positive."""
    rng = random.Random(seed)
    weights = [r[3] for r in REGIONS]
    locs = []
    for i in range(n):
        country, la, lo, _ = rng.choices(REGIONS, weights)[0]
        kind = ("distribution_center" if i % 10 == 0 else "warehouse" if i % 5 == 0
                else "destination" if i % 2 else "city")
        locs.append({"code": f"N{i + 1:03d}", "name": f"Node {i + 1:03d}", "country": country, "kind": kind,
                     "lat": round(rng.uniform(*la), 2), "lon": round(rng.uniform(*lo), 2),
                     "packages": rng.randint(500, 9000) * (6 if kind != "city" else 1)})
    pairs, parent = set(), list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    dist = lambda i, j: haversine_km(locs[i]["lat"], locs[i]["lon"], locs[j]["lat"], locs[j]["lon"])
    for i in range(n):
        for j in sorted((j for j in range(n) if j != i), key=lambda j: dist(i, j))[:3]:
            pairs.add((min(i, j), max(i, j)))
            parent[find(i)] = find(j)
    while len({find(i) for i in range(n)}) > 1:      # bridge the closest disconnected pair
        best = min(((dist(i, j), i, j) for i in range(n) for j in range(i + 1, n) if find(i) != find(j)))
        pairs.add((best[1], best[2]))
        parent[find(best[1])] = find(best[2])
    routes = []
    for i, j in sorted(pairs):
        d = dist(i, j)
        mode = "road" if d < 900 else "rail" if d < 2200 else ("air" if (i + j) % 2 else "sea")
        routes += both_ways(mode, locs[i], locs[j])
    return locs, routes


def random_edges(n, avg_degree=4, seed=1, max_w=100):
    """Benchmark graph: random connected digraph with positive integer weights, shuffled edge order."""
    rng = random.Random(seed)
    nodes = [f"v{i}" for i in range(n)]
    edges = {(nodes[i], nodes[(i + 1) % n]) for i in range(n)}          # ring keeps it connected
    while len(edges) < n * avg_degree:
        a, b = rng.sample(nodes, 2)
        edges.add((a, b))
    out = [(a, b, rng.randint(1, max_w)) for a, b in edges]
    rng.shuffle(out)
    return nodes, out


def worst_case_chain(n):
    """Chain v0->v1->...: edges listed in reverse order, so each pass of Bellman-Ford fixes one hop."""
    nodes = [f"v{i}" for i in range(n)]
    edges = [(nodes[i], nodes[i + 1], 1) for i in range(n - 1)][::-1]
    edges += [(nodes[i], nodes[(i + 2) % n], 5) for i in range(n)]       # extra edges: E ~ 2V
    return nodes, edges
