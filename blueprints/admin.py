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

    statistics = get_usage_statistics(
        quick_page=_get_page_argument("quick_page"),
        precise_page=_get_page_argument("precise_page"),
        visit_page=_get_page_argument("visit_page"),
    )
    return render_template("admin_stats.html", statistics=statistics)


def _get_page_argument(name):
    """Read a positive page number from the query string."""
    try:
        return max(int(request.args.get(name, "1")), 1)
    except ValueError:
        return 1
