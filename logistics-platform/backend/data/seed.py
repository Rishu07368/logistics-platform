"""Reproducible sample networks: four built-in scenarios."""
from ..algorithms.analysis import graph_properties
from ..db import repository as repo
from .generators import both_ways, generate_network, make_route

# code, name, country, kind, lat, lon, packages
L = [
    ("SHA", "Shanghai", "CN", "distribution_center", 31.23, 121.47, 88000),
    ("SZX", "Shenzhen", "CN", "warehouse", 22.54, 114.06, 61000),
    ("TYO", "Tokyo", "JP", "destination", 35.68, 139.69, 34000),
    ("SIN", "Singapore", "SG", "distribution_center", 1.35, 103.82, 72000),
    ("MUM", "Mumbai", "IN", "warehouse", 19.08, 72.88, 54000),
    ("DEL", "Delhi", "IN", "destination", 28.61, 77.21, 47000),
    ("DXB", "Dubai", "AE", "distribution_center", 25.2, 55.27, 69000),
    ("SYD", "Sydney", "AU", "destination", -33.87, 151.21, 26000),
    ("ROT", "Rotterdam", "NL", "distribution_center", 51.92, 4.48, 95000),
    ("HAM", "Hamburg", "DE", "warehouse", 53.55, 9.99, 52000),
    ("FRA", "Frankfurt", "DE", "distribution_center", 50.11, 8.68, 64000),
    ("LON", "London", "GB", "destination", 51.51, -0.13, 58000),
    ("PAR", "Paris", "FR", "destination", 48.86, 2.35, 49000),
    ("MAD", "Madrid", "ES", "destination", 40.42, -3.7, 31000),
    ("MIL", "Milan", "IT", "city", 45.46, 9.19, 28000),
    ("NYC", "New York", "US", "distribution_center", 40.71, -74.01, 91000),
    ("LAX", "Los Angeles", "US", "distribution_center", 34.05, -118.24, 83000),
    ("CHI", "Chicago", "US", "warehouse", 41.88, -87.63, 57000),
    ("HOU", "Houston", "US", "warehouse", 29.76, -95.37, 43000),
    ("TOR", "Toronto", "CA", "destination", 43.65, -79.38, 36000),
    ("MEX", "Mexico City", "MX", "destination", 19.43, -99.13, 33000),
    ("SAO", "S\u00e3o Paulo", "BR", "warehouse", -23.55, -46.63, 46000),
    ("CAI", "Cairo", "EG", "city", 30.04, 31.24, 24000),
    ("LOS", "Lagos", "NG", "destination", 6.52, 3.38, 22000),
    ("JNB", "Johannesburg", "ZA", "warehouse", -26.2, 28.05, 37000),
]
LOCATIONS = [dict(zip(("code", "name", "country", "kind", "lat", "lon", "packages"), r)) for r in L]
PAIRS = [  # undirected corridors: a, b, mode
    ("ROT", "HAM", "road"), ("ROT", "FRA", "road"), ("HAM", "FRA", "rail"), ("FRA", "PAR", "road"),
    ("ROT", "LON", "sea"), ("LON", "PAR", "rail"), ("PAR", "MAD", "road"), ("PAR", "MIL", "road"),
    ("FRA", "MIL", "rail"), ("MAD", "MIL", "air"), ("SHA", "SZX", "rail"), ("SHA", "TYO", "sea"),
    ("SZX", "SIN", "sea"), ("SIN", "MUM", "sea"), ("MUM", "DEL", "rail"), ("MUM", "DXB", "sea"),
    ("DEL", "DXB", "air"), ("SHA", "SIN", "sea"), ("TYO", "SZX", "air"), ("SIN", "SYD", "sea"),
    ("SHA", "DEL", "air"), ("SHA", "LAX", "sea"), ("TYO", "LAX", "sea"), ("SZX", "LAX", "air"),
    ("LAX", "CHI", "rail"), ("LAX", "HOU", "road"), ("LAX", "MEX", "road"), ("CHI", "NYC", "rail"),
    ("CHI", "TOR", "road"), ("NYC", "TOR", "road"), ("NYC", "HOU", "road"), ("HOU", "MEX", "road"),
    ("NYC", "ROT", "sea"), ("NYC", "LON", "air"), ("HOU", "SAO", "sea"), ("SAO", "ROT", "sea"),
    ("SAO", "JNB", "sea"), ("NYC", "SAO", "air"), ("DXB", "FRA", "air"), ("DXB", "CAI", "air"),
    ("DXB", "ROT", "sea"), ("CAI", "MIL", "sea"), ("CAI", "LOS", "air"), ("LOS", "JNB", "air"),
    ("LOS", "ROT", "sea"), ("JNB", "SIN", "sea"), ("JNB", "DXB", "air"), ("SYD", "LAX", "sea"),
    ("SYD", "SHA", "sea"), ("HAM", "NYC", "sea"), ("TOR", "LON", "air"),
]
NEG_CREDITS = [("NYC", "ROT"), ("SHA", "LAX"), ("DXB", "FRA"), ("SAO", "JNB")]   # one direction only
NEG_NOTE = "Test weight: backhaul credit modelled as a negative cost (algorithm testing only)"

SCENARIOS = {
    "standard": ("Standard network", "25 hubs, 102 directed routes, all weights positive.", "cost"),
    "negative_edges": ("Negative edges (no cycle)",
                       "Four directed routes carry a backhaul credit (negative cost) with no negative cycle.", "cost"),
    "negative_cycle": ("Negative cycle",
                       "Singapore\u2194Mumbai carry large negative test costs that form a negative cycle.", "cost"),
    "large": ("Large network (300 nodes)", "Generated geographic network for performance comparisons.", "cost"),
}


def _base_routes():
    by = {l["code"]: l for l in LOCATIONS}
    routes = []
    for a, b, mode in PAIRS:
        routes += both_ways(mode, by[a], by[b])
    return routes


def build_scenario(key):
    if key == "large":
        return generate_network(300, seed=7)
    locs, routes = [dict(l) for l in LOCATIONS], _base_routes()
    idx = {(r["src"], r["dst"]): r for r in routes}
    if key in ("negative_edges", "negative_cycle"):
        for pair in NEG_CREDITS:
            r = idx[pair]
            r["cost_usd"], r["note"] = -min(round(r["cost_usd"] * 0.25), 1200), NEG_NOTE
    if key == "negative_cycle":
        idx[("SIN", "MUM")].update(cost_usd=-1500, note="Test weight forming a negative cycle")
        idx[("MUM", "SIN")].update(cost_usd=-600, note="Test weight forming a negative cycle")
    return locs, routes


def load_scenario(conn, network_id, key):
    locs, routes = build_scenario(key)
    repo.insert_locations(conn, network_id, locs)
    repo.insert_routes(conn, network_id, routes)


def seed_database(conn):
    """Create any missing built-in scenario; existing networks (and edits) are left alone."""
    for key, (name, desc, metric) in SCENARIOS.items():
        if not repo.get_network_by_key(conn, key):
            nid = repo.create_network(conn, key, name, desc, key, True, metric)
            load_scenario(conn, nid, key)
    conn.commit()


def reset_network(conn, network):
    repo.clear_network(conn, network["id"])
    load_scenario(conn, network["id"], network["scenario"])
    conn.commit()


def has_negative_cycle(locs, routes, metric="cost_usd"):
    nodes = [l["code"] for l in locs]
    return graph_properties(nodes, [(r["src"], r["dst"], r[metric]) for r in routes])["has_negative_cycle"]
