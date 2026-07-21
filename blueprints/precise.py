"""Routes for precise prediction with uploaded preference files."""

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, abort, current_app, render_template, request, send_file
from openpyxl import Workbook
from werkzeug.utils import secure_filename

from utils.data_loader import (
    DataFormatError,
    DataNotFoundError,
    SUPPORTED_PREFERENCE_EXTENSIONS,
    load_admission_data,
    read_preference_file,
)
from utils.precise_predictor import (
    evaluate_all_preferences,
    parse_precise_inputs,
    predict_first_admission,
)
from utils.score_rank_validator import validate_score_rank_match
from utils.usage_logger import log_prediction


precise_bp = Blueprint("precise", __name__, url_prefix="/precise")


@precise_bp.route("/template")
def download_template():
    """Download a standard preference table template."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "志愿表模板"

    headers = ["学校代号", "学校名称", "专业代号", "专业名称"]
    examples = [
        ["0001", "浙江大学", "011", "社会学"],
        ["1", "浙江大学", "11", "社会学"],
        ["1140", "北京邮电大学", "001", "计算机类（元班）"],
        ["1140", "北京邮电大学", "1", "计算机类（元班）"],
        ["学校、专业代号开头的0可省略", "无0也可识别", "代号结尾的0不可省略", "阅读后请将本行及示例删除"],
    ]

    worksheet.append(headers)
    for row in examples:
        worksheet.append(row)

    for column_cells in worksheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = max_length + 6

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="志愿表模板.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@precise_bp.route("/", methods=["GET", "POST"])
def index():
    """Render precise prediction form and optional result."""
    context = {
        "submitted": False,
        "error": None,
        "prediction": None,
        "export_id": None,
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
            reached_preferences = evaluate_all_preferences(
                preferences, admission_data, score, rank
            )
            context["export_id"] = _save_reached_preferences_export(
                reached_preferences
            )
            log_prediction(
                feature="precise",
                score=score,
                rank=rank,
                has_result=bool(context["prediction"]),
                result_school=(
                    context["prediction"]["school_name"]
                    if context["prediction"]
                    else None
                ),
                result_major=(
                    context["prediction"]["major_name"]
                    if context["prediction"]
                    else None
                ),
            )
        except DataFormatError:
            context["error"] = (
                "志愿表无法识别。志愿表列顺序："
                "学校代号、学校名称、专业代号、专业名称。"
            )
        except (ValueError, DataNotFoundError) as exc:
            context["error"] = str(exc)

    return render_template("precise_predict.html", **context)


@precise_bp.route("/export/<export_id>")
def download_reached_preferences(export_id):
    """Download the latest precise prediction pass-status report."""
    if not export_id or not export_id.replace("_", "").isalnum():
        abort(404)

    export_path = Path(current_app.config["UPLOAD_FOLDER"]) / f"{export_id}.xlsx"
    if not export_path.exists():
        abort(404)

    return send_file(
        export_path,
        as_attachment=True,
        download_name="所有过线志愿.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _save_preference_file(uploaded_file):
    """Validate and save the uploaded preference file."""
    if not uploaded_file or not uploaded_file.filename:
        raise ValueError("请上传志愿表文件。")

    suffix = Path(uploaded_file.filename).suffix.lower()
    if suffix not in SUPPORTED_PREFERENCE_EXTENSIONS:
        raise ValueError("志愿表仅支持 xlsx、xls 或 csv 文件。")

    safe_name = secure_filename(uploaded_file.filename)
    if not safe_name or Path(safe_name).suffix.lower() != suffix:
        safe_name = f"preference{suffix}"

    stored_name = f"{uuid4().hex}_{safe_name}"
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)
    stored_path = upload_folder / stored_name
    uploaded_file.save(stored_path)

    return stored_path


def _save_reached_preferences_export(reached_preferences):
    """Create an Excel report for every preference and return its file id."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "所有过线志愿"

    headers = [
        "志愿顺序",
        "学校代号",
        "学校名称",
        "专业代号",
        "专业名称",
        "最低分",
        "最低位次",
        "是否过线",
    ]
    worksheet.append(headers)

    for preference in reached_preferences:
        worksheet.append(
            [
                preference["preference_index"],
                preference["school_code"],
                preference["school_name"],
                preference["major_code"],
                preference["major_name"],
                preference["minimum_score"],
                preference["minimum_rank"],
                preference["is_reached"],
            ]
        )

    for column_cells in worksheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = (
            max_length + 6
        )

    export_id = f"reached_preferences_{uuid4().hex}"
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)
    workbook.save(upload_folder / f"{export_id}.xlsx")

    return export_id
