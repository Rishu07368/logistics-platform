"""HTTP layer only: parse, delegate to services, serialise."""
from flask import Blueprint, current_app, g, jsonify, request

from ..algorithms.analysis import COMPLEXITY
from ..db import database, repository as repo
from ..services import analytics, network, routing
from ..services.errors import ApiError
from ..services.graph import ALGORITHMS, METRICS, load_graph

bp = Blueprint("api", __name__, url_prefix="/api")


def db():
    if "db" not in g:
        g.db = database.connect(current_app.config["DATABASE_PATH"])
    return g.db


@bp.teardown_app_request
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


@bp.errorhandler(ApiError)
def handle_api_error(e):
    return jsonify(e.to_dict()), e.status


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400, "INVALID_JSON")
    return data


def metric_arg(default="cost"):
    return request.args.get("metric", default)


@bp.get("/health")
def health():
    db().execute("SELECT 1")
    return {"status": "ok"}


@bp.get("/theory")
def theory():
    return {"algorithms": COMPLEXITY, "metrics": list(METRICS), "supported": list(ALGORITHMS)}


@bp.get("/networks")
def networks():
    return {"networks": repo.list_networks(db())}


@bp.post("/networks/generate")
def generate():
    return jsonify(network.generate_sample(db(), body())), 201


@bp.delete("/networks/<int:nid>")
def delete_net(nid):
    network.delete_network(db(), nid)
    return "", 204


@bp.post("/networks/<int:nid>/reset")
def reset(nid):
    return jsonify(network.reset(db(), nid))


@bp.get("/networks/<int:nid>/graph")
def graph(nid):
    gr = load_graph(db(), nid)
    return {"network": gr.network, "locations": gr.locations, "routes": gr.routes}


@bp.get("/networks/<int:nid>/summary")
def summary(nid):
    return analytics.summary(db(), nid)


@bp.get("/networks/<int:nid>/analysis")
def analysis(nid):
    props, rec = load_graph(db(), nid).recommendation(metric_arg())
    return {"metric": metric_arg(), "properties": props, "recommendation": rec}


@bp.get("/networks/<int:nid>/analytics")
def analytics_view(nid):
    return analytics.analytics(db(), nid, metric_arg())


@bp.post("/networks/<int:nid>/route")
def route(nid):
    b = body()
    return routing.calculate_route(db(), nid, b.get("source"), b.get("target"), b.get("algorithm", "auto"),
                                   b.get("metric", "cost"), bool(b.get("alternatives")))


@bp.post("/networks/<int:nid>/compare")
def compare(nid):
    b = body()
    return routing.compare_algorithms(db(), nid, b.get("source"), b.get("target"), b.get("metric", "cost"),
                                      b.get("repeats", 5), bool(b.get("force_dijkstra")))


@bp.post("/benchmark")
def benchmark():
    b = request.get_json(silent=True) or {}
    return routing.benchmark(b.get("sizes"), b.get("repeats", 3), b.get("avg_degree", 4), b.get("seed", 1))


@bp.post("/networks/<int:nid>/locations")
def add_location(nid):
    return jsonify(network.add_location(db(), nid, body())), 201


@bp.put("/locations/<int:lid>")
def edit_location(lid):
    return jsonify(network.update_location(db(), lid, body()))


@bp.delete("/locations/<int:lid>")
def remove_location(lid):
    network.delete_location(db(), lid)
    return "", 204


@bp.post("/networks/<int:nid>/routes")
def add_route(nid):
    return jsonify(network.add_route(db(), nid, body())), 201


@bp.put("/routes/<int:rid>")
def edit_route(rid):
    return jsonify(network.update_route(db(), rid, body()))


@bp.delete("/routes/<int:rid>")
def remove_route(rid):
    network.delete_route(db(), rid)
    return "", 204
