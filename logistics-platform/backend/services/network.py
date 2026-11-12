"""Network management: validated CRUD, sample-network generation, scenario reset."""
import random
import re

from ..data.generators import MODES, generate_network, make_route, route_metrics
from ..data.seed import has_negative_cycle, reset_network
from ..db import repository as repo
from .errors import ApiError

KINDS = ("city", "warehouse", "distribution_center", "destination")


def _num(body, key, lo=None, hi=None, required=True, integer=False):
    if body.get(key) in (None, ""):
        if required:
            raise ApiError(f"'{key}' is required", 422, "VALIDATION")
        return None
    try:
        v = float(body[key])
    except (TypeError, ValueError):
        raise ApiError(f"'{key}' must be a number", 422, "VALIDATION")
    if v != v or v in (float("inf"), float("-inf")):
        raise ApiError(f"'{key}' must be finite", 422, "VALIDATION")
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise ApiError(f"'{key}' must be between {lo} and {hi}", 422, "VALIDATION")
    return int(v) if integer else v


def _network(conn, nid):
    net = repo.get_network(conn, nid)
    if not net:
        raise ApiError(f"Network {nid} not found", 404, "UNKNOWN_NETWORK")
    return net


def add_location(conn, nid, body):
    _network(conn, nid)
    code = str(body.get("code", "")).strip().upper()
    name = str(body.get("name", "")).strip()
    if not re.fullmatch(r"[A-Z0-9]{2,6}", code):
        raise ApiError("'code' must be 2-6 letters/digits", 422, "VALIDATION")
    if not name:
        raise ApiError("'name' is required", 422, "VALIDATION")
    kind = body.get("kind", "city")
    if kind not in KINDS:
        raise ApiError(f"'kind' must be one of {list(KINDS)}", 422, "VALIDATION")
    loc = {"code": code, "name": name, "country": str(body.get("country", "")).strip().upper()[:3] or "XX",
           "kind": kind, "lat": _num(body, "lat", -90, 90), "lon": _num(body, "lon", -180, 180),
           "packages": _num(body, "packages", 0, 10**7, required=False, integer=True) or 0}
    if any(l["code"] == code for l in repo.list_locations(conn, nid)):
        raise ApiError(f"Location {code} already exists", 409, "DUPLICATE")
    repo.insert_locations(conn, nid, [loc])
    conn.commit()
    return next(l for l in repo.list_locations(conn, nid) if l["code"] == code)


def update_location(conn, loc_id, body):
    loc = repo.get_location(conn, loc_id)
    if not loc:
        raise ApiError("Location not found", 404, "NOT_FOUND")
    fields = {}
    for k in ("name", "country"):
        if k in body:
            fields[k] = str(body[k]).strip() or loc[k]
    if "kind" in body:
        if body["kind"] not in KINDS:
            raise ApiError(f"'kind' must be one of {list(KINDS)}", 422, "VALIDATION")
        fields["kind"] = body["kind"]
    for k, lo, hi in (("lat", -90, 90), ("lon", -180, 180), ("packages", 0, 10**7)):
        if k in body:
            fields[k] = _num(body, k, lo, hi, integer=(k == "packages"))
    if fields:
        repo.update_location(conn, loc_id, fields)
        conn.commit()
    return repo.get_location(conn, loc_id)


def delete_location(conn, loc_id):
    loc = repo.get_location(conn, loc_id)
    if not loc:
        raise ApiError("Location not found", 404, "NOT_FOUND")
    repo.delete_location(conn, loc)
    conn.commit()


def add_route(conn, nid, body):
    _network(conn, nid)
    locs = {l["code"]: l for l in repo.list_locations(conn, nid)}
    src, dst = str(body.get("src", "")).upper(), str(body.get("dst", "")).upper()
    for c in (src, dst):
        if c not in locs:
            raise ApiError(f"Unknown location {c!r}", 404, "UNKNOWN_LOCATION")
    if src == dst:
        raise ApiError("A route needs two different locations", 422, "VALIDATION")
    mode = body.get("mode", "road")
    if mode not in MODES:
        raise ApiError(f"'mode' must be one of {list(MODES)}", 422, "VALIDATION")
    auto = route_metrics(mode, locs[src], locs[dst])
    r = {"src": src, "dst": dst, "mode": mode, "note": str(body.get("note", ""))[:200],
         "distance_km": _num(body, "distance_km", 0, 40000, required=False),
         "cost_usd": _num(body, "cost_usd", -10**7, 10**7, required=False),
         "time_hours": _num(body, "time_hours", -10**5, 10**5, required=False),
         "weekly_trips": _num(body, "weekly_trips", 0, 1000, required=False, integer=True)}
    for k, v in auto.items():                     # missing values are derived from coordinates + mode
        if r.get(k) is None:
            r[k] = v
    both = [r] + ([{**r, "src": dst, "dst": src}] if body.get("bidirectional") else [])
    for x in both:
        if repo.get_route_pair(conn, nid, x["src"], x["dst"]):
            raise ApiError(f"Route {x['src']}\u2192{x['dst']} already exists; edit it instead", 409, "DUPLICATE")
    repo.insert_routes(conn, nid, both)
    conn.commit()
    return [repo.get_route_pair(conn, nid, x["src"], x["dst"]) for x in both]


def update_route(conn, route_id, body):
    route = repo.get_route(conn, route_id)
    if not route:
        raise ApiError("Route not found", 404, "NOT_FOUND")
    fields = {}
    for k, lo, hi in (("distance_km", 0, 40000), ("cost_usd", -10**7, 10**7),
                      ("time_hours", -10**5, 10**5), ("weekly_trips", 0, 1000)):
        if k in body:
            fields[k] = _num(body, k, lo, hi, integer=(k == "weekly_trips"))
    if "mode" in body:
        if body["mode"] not in MODES:
            raise ApiError(f"'mode' must be one of {list(MODES)}", 422, "VALIDATION")
        fields["mode"] = body["mode"]
    if "note" in body:
        fields["note"] = str(body["note"])[:200]
    if fields:
        repo.update_route(conn, route_id, fields)
        conn.commit()
    return repo.get_route(conn, route_id)


def delete_route(conn, route_id):
    if not repo.get_route(conn, route_id):
        raise ApiError("Route not found", 404, "NOT_FOUND")
    repo.delete_route(conn, route_id)
    conn.commit()


def generate_sample(conn, body):
    n = _num(body, "nodes", 5, 500, integer=True)
    seed = _num(body, "seed", 0, 10**9, required=False, integer=True) or 1
    negatives = _num(body, "negative_edges", 0, 50, required=False, integer=True) or 0
    locs, routes = generate_network(n, seed)
    name = str(body.get("name") or f"Generated network ({n} nodes, seed {seed})")[:80]
    rng, applied = random.Random(seed), 0
    for r in rng.sample(routes, min(negatives, len(routes))):   # negative test credits, rolled back on a cycle
        old = r["cost_usd"]
        r["cost_usd"], r["note"] = -round(old * 0.15), "Test weight: negative credit (algorithm testing only)"
        if has_negative_cycle(locs, routes):
            r["cost_usd"], r["note"] = old, ""
        else:
            applied += 1
    key = f"gen-{n}-{seed}-{negatives}"
    if repo.get_network_by_key(conn, key):
        raise ApiError("A network with these parameters already exists", 409, "DUPLICATE")
    nid = repo.create_network(conn, key, name, f"Generated geographic network; {applied} negative test edge(s).",
                              "generated", False, "cost")
    repo.insert_locations(conn, nid, locs)
    repo.insert_routes(conn, nid, routes)
    conn.commit()
    return repo.get_network(conn, nid)


def delete_network(conn, nid):
    net = _network(conn, nid)
    if net["builtin"]:
        raise ApiError("Built-in scenarios cannot be deleted; use reset instead", 403, "BUILTIN")
    repo.delete_network(conn, nid)
    conn.commit()


def reset(conn, nid):
    net = _network(conn, nid)
    if net["scenario"] == "generated":
        raise ApiError("Generated networks cannot be reset; delete and regenerate", 403, "NOT_RESETTABLE")
    reset_network(conn, net)
    return net
