"""Main public routes for the website."""

from flask import Blueprint, render_template


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Render the public home page."""
    return render_template("index.html")
