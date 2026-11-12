import itertools

INF = float("inf")


def nid(client, key):
    return next(n["id"] for n in client.get("/api/networks").json["networks"] if n["key"] == key)


def route(client, key, algo, src="SHA", dst="JNB", metric="cost", **kw):
    return client.post(f"/api/networks/{nid(client, key)}/route",
                       json={"source": src, "target": dst, "algorithm": algo, "metric": metric, **kw})


def test_four_scenarios_seeded(client):
    keys = {n["key"]: n for n in client.get("/api/networks").json["networks"]}
    assert set(keys) == {"standard", "negative_edges", "negative_cycle", "large"}
    assert keys["standard"]["locations"] == 25 and keys["large"]["locations"] == 300


def test_standard_both_algorithms_agree(client):
    a = route(client, "standard", "dijkstra_heap", alternatives=True).json
    b = route(client, "standard", "bellman_ford").json
    assert a["status"] == "ok" and a["path"] == b["path"] and a["total"] == b["total"]
    assert a["alternatives"] and a["alternatives"][0]["extra"] >= 0
    assert abs(a["totals"]["cost_usd"] - a["total"]) < 0.01


def test_all_pairs_sample_dijkstra_equals_bellman_ford(client):
    for s, t in itertools.islice(itertools.product(["SHA", "NYC", "LOS"], ["ROT", "SYD", "MEX", "TOR"]), 12):
        assert route(client, "standard", "dijkstra_heap", s, t, "time").json["total"] == \
               route(client, "standard", "bellman_ford", s, t, "time").json["total"]


def test_dijkstra_blocked_on_negative_edges_but_bellman_ford_works(client):
    r = route(client, "negative_edges", "dijkstra_heap")
    assert r.status_code == 422 and r.json["code"] == "NEGATIVE_WEIGHTS"
    assert r.json["recommendation"]["algorithm"] == "bellman_ford"
    ok = route(client, "negative_edges", "bellman_ford").json
    assert ok["status"] == "ok" and ok["total"] is not None
    assert route(client, "negative_edges", "dijkstra_heap", metric="distance").status_code == 200  # other metric is fine


def test_negative_cycle_scenario(client):
    r = route(client, "negative_cycle", "bellman_ford", "SHA", "MUM").json
    assert r["status"] == "negative_cycle" and set(r["negative_cycle"]["nodes"]) == {"SIN", "MUM"}
    assert r["path"] is None and "negative" in r["message"].lower()
    rec = client.get(f"/api/networks/{nid(client, 'negative_cycle')}/analysis?metric=cost").json["recommendation"]
    assert rec["status"] == "invalid"
    assert route(client, "negative_cycle", "auto", "SHA", "MUM", metric="time").json["status"] == "ok"


def test_auto_picks_recommended_algorithm(client):
    assert route(client, "standard", "auto").json["algorithm"].startswith("dijkstra")
    assert route(client, "negative_edges", "auto").json["algorithm"] == "bellman_ford"


def test_compare_endpoint(client):
    r = client.post(f"/api/networks/{nid(client, 'large')}/compare",
                    json={"source": "N001", "target": "N200", "metric": "cost", "repeats": 3}).json
    assert r["agreement"] and len(r["rows"]) == 3 and all(x["median_ms"] > 0 for x in r["rows"])
    neg = client.post(f"/api/networks/{nid(client, 'negative_edges')}/compare",
                      json={"source": "SHA", "target": "JNB", "metric": "cost", "force_dijkstra": True}).json
    assert neg["rows"][0]["applicable"] is False and neg["rows"][2]["total"] is not None
    assert any(x["forced"] for x in neg["rows"])


def test_benchmark_endpoint(client):
    r = client.post("/api/benchmark", json={"sizes": [20, 40], "repeats": 1}).json
    assert len(r["points"]) == 2 * 2 * 3
    bf = {(p["graph"], p["vertices"]): p for p in r["points"] if p["algorithm"] == "bellman_ford"}
    assert bf[("bf_worst_case", 40)]["iterations"] > bf[("random", 40)]["iterations"]
    assert client.post("/api/benchmark", json={"sizes": [1]}).status_code == 400


def test_summary_and_analytics(client):
    s = client.get(f"/api/networks/{nid(client, 'standard')}/summary").json
    assert s["locations"] == 25 and s["directed_routes"] == 102 and s["packages"] > 0
    assert s["connectivity"]["strongly_connected"] is True
    a = client.get(f"/api/networks/{nid(client, 'standard')}/analytics?metric=cost").json
    assert {m["mode"] for m in a["modes"]} == {"road", "rail", "sea", "air"} and a["hubs"]


def test_network_crud_and_validation(client):
    n = nid(client, "standard")
    loc = {"code": "tst", "name": "Testville", "country": "xx", "kind": "warehouse", "lat": 10, "lon": 20}
    assert client.post(f"/api/networks/{n}/locations", json=loc).status_code == 201
    assert client.post(f"/api/networks/{n}/locations", json=loc).status_code == 409
    assert client.post(f"/api/networks/{n}/locations", json={**loc, "code": "BAD", "lat": 99}).status_code == 422
    r = client.post(f"/api/networks/{n}/routes", json={"src": "TST", "dst": "SHA", "mode": "air", "bidirectional": True})
    assert r.status_code == 201 and len(r.json) == 2 and r.json[0]["distance_km"] > 0
    assert client.post(f"/api/networks/{n}/routes", json={"src": "TST", "dst": "SHA"}).status_code == 409
    assert client.post(f"/api/networks/{n}/routes", json={"src": "TST", "dst": "NOPE"}).status_code == 404
    assert route(client, "standard", "dijkstra_heap", "TST", "JNB").json["status"] == "ok"
    rid = r.json[0]["id"]
    assert client.put(f"/api/routes/{rid}", json={"distance_km": -5}).status_code == 422
    assert client.put(f"/api/routes/{rid}", json={"cost_usd": -50}).json["cost_usd"] == -50
    assert route(client, "standard", "dijkstra_heap", "TST", "JNB").status_code == 422     # now negative
    assert client.delete(f"/api/routes/{rid}").status_code == 204
    lid = next(l["id"] for l in client.get(f"/api/networks/{n}/graph").json["locations"] if l["code"] == "TST")
    assert client.delete(f"/api/locations/{lid}").status_code == 204
    assert all(r["src"] != "TST" for r in client.get(f"/api/networks/{n}/graph").json["routes"])


def test_negative_edge_introduced_by_user_changes_recommendation(client):
    n = nid(client, "standard")
    rid = next(r["id"] for r in client.get(f"/api/networks/{n}/graph").json["routes"] if (r["src"], r["dst"]) == ("ROT", "HAM"))
    client.put(f"/api/routes/{rid}", json={"cost_usd": -100})
    assert client.get(f"/api/networks/{n}/analysis?metric=cost").json["recommendation"]["algorithm"] == "bellman_ford"
    assert client.post(f"/api/networks/{n}/reset").status_code == 200
    assert client.get(f"/api/networks/{n}/analysis?metric=cost").json["recommendation"]["algorithm"].startswith("dijkstra")


def test_generate_and_delete_network(client):
    r = client.post("/api/networks/generate", json={"nodes": 40, "seed": 5, "negative_edges": 3})
    assert r.status_code == 201
    g = r.json["id"]
    assert client.get(f"/api/networks/{g}/analysis?metric=cost").json["properties"]["has_negative_cycle"] is False
    assert client.post("/api/networks/generate", json={"nodes": 40, "seed": 5, "negative_edges": 3}).status_code == 409
    assert client.post("/api/networks/generate", json={"nodes": 2}).status_code == 422
    assert client.delete(f"/api/networks/{g}").status_code == 204
    assert client.delete(f"/api/networks/{nid(client, 'standard')}").status_code == 403


def test_error_handling(client):
    assert client.get("/api/networks/999/graph").status_code == 404
    assert route(client, "standard", "nope").status_code == 400
    assert route(client, "standard", "dijkstra_heap", metric="speed").status_code == 400
    assert route(client, "standard", "dijkstra_heap", src="ZZZ").status_code == 404
    assert client.post(f"/api/networks/1/route", data="not json", content_type="application/json").status_code == 400
