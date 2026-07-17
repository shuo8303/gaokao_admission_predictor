"""Routes for quick score and rank based prediction."""

import csv
from io import StringIO

from flask import Blueprint, Response, render_template, request

from utils.data_loader import DataFormatError, DataNotFoundError, load_admission_data
from utils.quick_predictor import (
    SORT_LABELS,
    find_download_matches,
    find_quick_matches,
    parse_candidate_inputs,
)
from utils.auth_guard import login_required
from utils.score_rank_validator import validate_score_rank_match


quick_bp = Blueprint("quick", __name__, url_prefix="/quick")


@quick_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Render the quick prediction form and optional prediction results."""
    context = {
        "results": [],
        "submitted": False,
        "error": None,
        "sort_labels": SORT_LABELS,
        "form_values": {"score": "", "rank": "", "sort_by": "rank"},
    }

    if request.method == "POST":
        context["submitted"] = True
        context["form_values"] = {
            "score": request.form.get("score", "").strip(),
            "rank": request.form.get("rank", "").strip(),
            "sort_by": request.form.get("sort_by", "rank"),
        }

        try:
            score, rank = parse_candidate_inputs(
                context["form_values"]["score"],
                context["form_values"]["rank"],
            )
            validate_score_rank_match(score, rank)
            admission_data = load_admission_data()
            context["results"] = find_quick_matches(
                admission_data,
                score,
                rank,
                context["form_values"]["sort_by"],
            )
        except (ValueError, DataNotFoundError, DataFormatError) as exc:
            context["error"] = str(exc)

    return render_template("quick_predict.html", **context)


@quick_bp.route("/download", methods=["POST"])
@login_required
def download():
    """Download quick prediction rows within score plus or minus 3."""
    try:
        score, rank = parse_candidate_inputs(
            request.form.get("score", "").strip(),
            request.form.get("rank", "").strip(),
        )
        validate_score_rank_match(score, rank)
        sort_by = request.form.get("sort_by", "rank")
        admission_data = load_admission_data()
        results = find_download_matches(admission_data, score, rank, sort_by)
    except (ValueError, DataNotFoundError, DataFormatError) as exc:
        return Response(str(exc), status=400, mimetype="text/plain; charset=utf-8")

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "学校代号",
        "学校名称",
        "专业代号",
        "专业名称",
        "投档最低分",
        "投档最低位次",
    ])

    for item in results:
        writer.writerow([
            item["school_code"],
            item["school_name"],
            item["major_code"],
            item["major_name"],
            item["minimum_score"],
            item["minimum_rank"],
        ])

    filename = f"quick_prediction_{score}_{rank}.csv"
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
