"""Routes for precise prediction with uploaded preference files."""

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, render_template, request
from werkzeug.utils import secure_filename

from utils.data_loader import (
    DataFormatError,
    DataNotFoundError,
    SUPPORTED_PREFERENCE_EXTENSIONS,
    load_admission_data,
    read_preference_file,
)
from utils.auth_guard import login_required
from utils.precise_predictor import parse_precise_inputs, predict_first_admission
from utils.score_rank_validator import validate_score_rank_match


precise_bp = Blueprint("precise", __name__, url_prefix="/precise")


@precise_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Render precise prediction form and optional result."""
    context = {
        "submitted": False,
        "error": None,
        "prediction": None,
        "form_values": {"score": "", "rank": ""},
    }

    if request.method == "POST":
        context["submitted"] = True
        context["form_values"] = {
            "score": request.form.get("score", "").strip(),
            "rank": request.form.get("rank", "").strip(),
        }

        try:
            score, rank = parse_precise_inputs(
                context["form_values"]["score"],
                context["form_values"]["rank"],
            )
            validate_score_rank_match(score, rank)
            uploaded_path = _save_preference_file(request.files.get("preference_file"))
            preferences = read_preference_file(uploaded_path)
            admission_data = load_admission_data()
            context["prediction"] = predict_first_admission(
                preferences, admission_data, score, rank
            )
        except (ValueError, DataNotFoundError, DataFormatError) as exc:
            context["error"] = str(exc)

    return render_template("precise_predict.html", **context)


def _save_preference_file(uploaded_file):
    """Validate and save the uploaded preference file."""
    if not uploaded_file or not uploaded_file.filename:
        raise ValueError("请上传志愿表文件。")

    suffix = Path(uploaded_file.filename).suffix.lower()
    if suffix not in SUPPORTED_PREFERENCE_EXTENSIONS:
        raise ValueError("志愿表仅支持 xlsx、xls 或 csv 文件。")

    safe_name = secure_filename(uploaded_file.filename)
    stored_name = f"{uuid4().hex}_{safe_name}"
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)
    stored_path = upload_folder / stored_name
    uploaded_file.save(stored_path)

    return stored_path
