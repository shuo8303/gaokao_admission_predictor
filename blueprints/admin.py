"""Admin-only pages for viewing lightweight usage statistics."""

from flask import Blueprint, abort, current_app, render_template, request

from utils.usage_logger import get_usage_statistics


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/stats")
def stats():
    """Render the usage statistics dashboard.

    The page is protected by a simple token in the query string. Configure the
    token on the server with the ADMIN_STATS_TOKEN environment variable, then
    visit /admin/stats?token=your-token.
    """
    expected_token = current_app.config.get("ADMIN_STATS_TOKEN", "")
    submitted_token = request.args.get("token", "")

    if not expected_token or submitted_token != expected_token:
        abort(403)

    statistics = get_usage_statistics()
    return render_template("admin_stats.html", statistics=statistics)
