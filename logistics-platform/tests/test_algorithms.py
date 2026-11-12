import random

import pytest

from backend.algorithms.analysis import graph_properties, recommend
from backend.algorithms.bellman_ford import bellman_ford
from backend.algorithms.common import INF, NegativeWeightError
from backend.algorithms.dijkstra import dijkstra
from backend.data.generators import random_edges, worst_case_chain

# CLRS Figure 24.6 (non-negative)
N1 = list("stxyz")
E1 = [("s", "t", 10), ("s", "y", 5), ("t", "x", 1), ("t", "y", 2), ("y", "t", 3), ("y", "x", 9),
      ("y", "z", 2), ("x", "z", 4), ("z", "s", 7), ("z", "x", 6)]
# CLRS Figure 24.4 (negative edges, no negative cycle)
E2 = [("s", "t", 6), ("s", "y", 7), ("t", "x", 5), ("t", "y", 8), ("t", "z", -4), ("x", "t", -2),
      ("y", "x", -3), ("y", "z", 9), ("z", "s", 2), ("z", "x", 7)]


@pytest.mark.parametrize("variant", ["heap", "array"])
def test_dijkstra_known_distances_and_path(variant):
    r = dijkstra(N1, E1, "s", variant)
    assert r.dist == {"s": 0, "y": 5, "t": 8, "x": 9, "z": 7}
    assert r.path_to("x") == ["s", "y", "t", "x"]


def test_dijkstra_rejects_negative_edges():
    with pytest.raises(NegativeWeightError) as exc:
        dijkstra(N1, E2, "s")
    assert ("t", "z", -4) in exc.value.negative_edges


def test_dijkstra_unreachable_and_unknown_source():
    r = dijkstra(["a", "b"], [], "a")
    assert r.dist["b"] == INF and r.path_to("b") is None
    with pytest.raises(KeyError):
        dijkstra(["a"], [], "zz")


def test_bellman_ford_negative_edges_known_distances():
    r = bellman_ford(N1, E2, "s")
    assert r.dist == {"s": 0, "t": 2, "x": 4, "y": 7, "z": -2}
    assert r.path_to("x") == ["s", "y", "x"] and r.negative_cycle is None


def test_bellman_ford_matches_dijkstra_on_non_negative_graph():
    assert bellman_ford(N1, E1, "s").dist == dijkstra(N1, E1, "s").dist


def test_bellman_ford_detects_negative_cycle():
    r = bellman_ford(list("abcd"), [("a", "b", 1), ("b", "c", -3), ("c", "b", 1), ("c", "d", 2)], "a")
    assert set(r.negative_cycle) == {"b", "c"} and r.negative_cycle_weight == -2
    assert r.dist["d"] == -INF and r.path_to("d") is None


def test_cycle_unreachable_from_source_is_ignored():
    edges = [("a", "b", 1), ("x", "y", -2), ("y", "x", 1)]
    assert bellman_ford(list("abxy"), edges, "a").negative_cycle is None
    assert bellman_ford(list("abxy"), edges, None).negative_cycle is not None     # global detection


def test_early_termination_vs_worst_case():
    nodes, edges = random_edges(200, 4, seed=3)
    assert bellman_ford(nodes, edges, "v0").stats["early_termination"]
    nodes, edges = worst_case_chain(100)
    r = bellman_ford(nodes, edges, "v0")
    assert r.stats["iterations"] >= 99 and r.dist["v99"] == 99


def test_cross_validation_on_random_graphs():
    for seed in range(40):
        nodes, edges = random_edges(random.Random(seed).randint(5, 60), 3, seed)
        a, b, c = (dijkstra(nodes, edges, "v0", "heap"), dijkstra(nodes, edges, "v0", "array"),
                   bellman_ford(nodes, edges, "v0"))
        assert a.dist == b.dist == c.dist


def test_forced_dijkstra_gives_wrong_answer_on_negative_graph():
    wrong = dijkstra(N1, E2, "s", validate=False)
    assert wrong.dist != bellman_ford(N1, E2, "s").dist


def test_recommendations_follow_graph_properties():
    assert recommend(graph_properties(N1, E1))["algorithm"] in ("dijkstra_heap", "dijkstra_array")
    assert recommend(graph_properties(N1, E2))["algorithm"] == "bellman_ford"
    cyc = recommend(graph_properties(list("abc"), [("a", "b", 1), ("b", "c", -3), ("c", "a", 1)]))
    assert cyc["status"] == "invalid" and cyc["algorithm"] is None
    nodes, edges = random_edges(300, 4)
    assert recommend(graph_properties(nodes, edges))["algorithm"] == "dijkstra_heap"
