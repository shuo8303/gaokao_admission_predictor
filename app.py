"""Application entry point for the Gaokao Admission Predictor."""

from flask import Flask, render_template, request

from blueprints.admin import admin_bp
from blueprints.main import main_bp
from blueprints.precise import precise_bp
from blueprints.quick import quick_bp
from config import Config
from utils.usage_logger import log_visit


def create_app():
    """Create and configure the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(quick_bp)
    app.register_blueprint(precise_bp)

    @app.before_request
    def show_closed_page_when_needed():
        """Show a temporary closed page before official filing lines publish."""
        allowed_endpoints = {"static", "admin.stats"}

        if not app.config["SITE_CLOSED"]:
            return

        if request.endpoint in allowed_endpoints:
            return

        return render_template("site_closed.html"), 503

    @app.before_request
    def record_visit():
        """Record page visits for lightweight traffic statistics."""
        if request.endpoint == "static":
            return

        log_visit()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
