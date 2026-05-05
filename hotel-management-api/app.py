import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from auth import jwt
from config import get_config
from models import db
from routes import register_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_override=None):
    app = Flask(__name__)

    cfg = get_config()
    app.config.from_object(cfg)

    if config_override:
        app.config.update(config_override)

    # Extensions
    db.init_app(app)
    JWTManager(app)
    CORS(app, origins=app.config.get("CORS_ORIGINS", "*"))

    # Routes
    register_routes(app)

    # Create tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified.")

    # Error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "message": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found", "message": str(e)}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("Unhandled server error")
        return jsonify({"error": "Internal server error"}), 500

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
