"""Application entry point for the Gaokao Admission Predictor."""

from flask import Flask

from blueprints.main import main_bp
from blueprints.precise import precise_bp
from blueprints.quick import quick_bp
from config import Config


def create_app():
    """Create and configure the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.register_blueprint(main_bp)
    app.register_blueprint(quick_bp)
    app.register_blueprint(precise_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
