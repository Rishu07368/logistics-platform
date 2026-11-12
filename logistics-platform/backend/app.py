"""Application factory + static frontend hosting."""
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from . import config
from .data.seed import seed_database
from .db import database
from .routes.api import bp
from .services.errors import ApiError

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def create_app(database_path=None):
    app = Flask(__name__, static_folder=None)
    app.config["DATABASE_PATH"] = database_path or config.DATABASE_PATH
    conn = database.connect(app.config["DATABASE_PATH"])
    database.init_schema(conn)
    seed_database(conn)
    conn.close()
    app.register_blueprint(bp)

    @app.errorhandler(ApiError)
    def api_error(e):
        return jsonify(e.to_dict()), e.status

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Not found", "code": "NOT_FOUND"}), 404

    @app.errorhandler(405)
    def bad_method(_):
        return jsonify({"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}), 405

    @app.errorhandler(Exception)
    def unexpected(e):
        app.logger.exception(e)
        return jsonify({"error": "Internal server error", "code": "INTERNAL"}), 500

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND, "index.html")

    @app.get("/<path:path>")
    def static_files(path):
        return send_from_directory(FRONTEND, path)

    return app
