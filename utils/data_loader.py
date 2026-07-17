"""Load and normalize official admission and preference data files.

The rest of the application should use the standard column names exposed by
this module instead of depending on a specific Excel template. Replacing an
official file in the data directory should not require route or prediction
code changes as long as the required information is present.
"""

from pathlib import Path

import pandas as pd

from config import Config


SUPPORTED_DATA_EXTENSIONS = {".xlsx", ".xls", ".csv"}
SUPPORTED_PREFERENCE_EXTENSIONS = {".xlsx", ".xls", ".csv"}

STANDARD_COLUMNS = {
    "school_code": "学校代号",
    "school_name": "学校名称",
    "major_code": "专业代号",
    "major_name": "专业名称",
    "plan_count": "计划数",
    "minimum_score": "分数线",
    "minimum_rank": "位次",
}

PREFERENCE_COLUMNS = {
    "school_code": "学校代号",
    "school_name": "学校名称",
    "major_code": "专业代号",
    "major_name": "专业名称",
}

# Zhejiang official filing line tables are expected to use this order.
# The fallback keeps imports working when exported files have unstable headers.
ADMISSION_POSITION_COLUMNS = (
    "school_code",
    "school_name",
    "major_code",
    "major_name",
    "plan_count",
    "minimum_score",
    "minimum_rank",
)

PREFERENCE_POSITION_COLUMNS = (
    "school_code",
    "school_name",
    "major_code",
    "major_name",
)

COLUMN_ALIASES = {
    "school_code": (
        "学校代号",
        "院校代号",
        "院校代码",
        "学校代码",
        "代码",
    ),
    "school_name": (
        "学校名称",
        "院校名称",
        "院校",
        "学校",
        "招生院校",
    ),
    "major_code": (
        "专业代号",
        "专业代码",
        "专业组代码",
    ),
    "major_name": (
        "专业名称",
        "专业",
        "专业类名称",
        "招生专业",
        "专业(类)",
    ),
    "plan_count": (
        "计划数",
        "招生计划数",
        "计划",
    ),
    "minimum_score": (
        "分数线",
        "最低投档分",
        "投档最低分",
        "最低分",
        "最低录取分",
    ),
    "minimum_rank": (
        "位次",
        "最低投档位次",
        "投档最低位次",
        "最低位次",
        "最低录取位次",
    ),
}


class DataNotFoundError(FileNotFoundError):
    """Raised when no official admission data files are available."""


class DataFormatError(ValueError):
    """Raised when a data file cannot be normalized for prediction."""


def get_data_files(data_dir=None):
    """Return supported official data files from the data directory."""
    directory = Path(data_dir or Config.DATA_DIR)

    if not directory.exists():
        raise DataNotFoundError(f"Data directory does not exist: {directory}")

    files = [
        file_path
        for file_path in directory.iterdir()
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_DATA_EXTENSIONS
    ]

    if not files:
        raise DataNotFoundError(f"No admission data files found in: {directory}")

    return sorted(files)


def load_admission_data(data_dir=None):
    """Load every supported official data file and return one DataFrame."""
    frames = []

    for file_path in get_data_files(data_dir):
        frame = read_admission_file(file_path)
        frame["source_file"] = file_path.name
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)


def read_admission_file(file_path):
    """Read one official admission file and normalize required columns."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        raw_frame = pd.read_csv(path)
    elif suffix in {".xlsx", ".xls"}:
        raw_frame = _read_excel_workbook(path)
    else:
        raise DataFormatError(f"Unsupported data file type: {path.suffix}")

    normalized = _normalize_columns(raw_frame, STANDARD_COLUMNS, ADMISSION_POSITION_COLUMNS)
    _validate_required_columns(normalized, STANDARD_COLUMNS, path)
    return _clean_admission_data(normalized)


def read_preference_file(file_path):
    """Read an uploaded preference file and preserve preference order."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_PREFERENCE_EXTENSIONS:
        raise DataFormatError(f"Unsupported preference file type: {path.suffix}")

    if suffix == ".csv":
        raw_frame = pd.read_csv(path)
    else:
        raw_frame = _read_excel_workbook(path)

    normalized = _normalize_columns(raw_frame, PREFERENCE_COLUMNS, PREFERENCE_POSITION_COLUMNS)
    _validate_required_columns(normalized, PREFERENCE_COLUMNS, path)
    return _clean_preference_data(normalized)


def _read_excel_workbook(path):
    """Read all sheets from an Excel workbook into one DataFrame."""
    engine = "openpyxl" if path.suffix.lower() == ".xlsx" else "xlrd"

    try:
        sheets = pd.read_excel(path, sheet_name=None, engine=engine)
    except ImportError as exc:
        raise DataFormatError(
            f"Reading {path.suffix} files requires the {engine} package."
        ) from exc

    frames = [sheet for sheet in sheets.values() if not sheet.empty]

    if not frames:
        raise DataFormatError(f"Excel workbook has no readable rows: {path}")

    return pd.concat(frames, ignore_index=True)


def _normalize_columns(frame, required_columns, position_columns):
    """Rename known headers, then fall back to the expected column order."""
    renamed_columns = {}
    stripped_columns = {column: str(column).strip() for column in frame.columns}

    for standard_name, aliases in COLUMN_ALIASES.items():
        if standard_name not in required_columns:
            continue

        for original_column, stripped_column in stripped_columns.items():
            if stripped_column in aliases:
                renamed_columns[original_column] = standard_name
                break

    normalized = frame.rename(columns=renamed_columns)
    missing_columns = [
        column for column in required_columns if column not in normalized.columns
    ]

    if missing_columns and len(frame.columns) >= len(position_columns):
        position_map = {
            frame.columns[index]: standard_name
            for index, standard_name in enumerate(position_columns)
        }
        normalized = frame.rename(columns=position_map)

    return normalized


def _validate_required_columns(frame, required_columns, file_path):
    """Ensure the normalized data contains every required field."""
    missing_columns = [
        column
        for column in required_columns
        if column not in frame.columns
    ]

    if missing_columns:
        readable_columns = ", ".join(required_columns[column] for column in missing_columns)
        raise DataFormatError(
            f"Missing required columns in {file_path.name}: {readable_columns}"
        )


def _clean_admission_data(frame):
    """Keep required fields and coerce plan, scores, and ranks to numbers."""
    cleaned = frame[list(STANDARD_COLUMNS)].copy()

    for column in ("school_code", "school_name", "major_code", "major_name"):
        cleaned[column] = cleaned[column].map(_clean_text_value)

    cleaned["school_code"] = cleaned["school_code"].map(
        lambda value: _format_code(value, 4)
    )
    cleaned["major_code"] = cleaned["major_code"].map(
        lambda value: _format_code(value, 3)
    )

    cleaned["plan_count"] = pd.to_numeric(cleaned["plan_count"], errors="coerce")
    cleaned["minimum_score"] = pd.to_numeric(cleaned["minimum_score"], errors="coerce")
    cleaned["minimum_rank"] = _clean_rank_series(cleaned["minimum_rank"])

    cleaned = cleaned.dropna(
        subset=[
            "school_code",
            "school_name",
            "major_code",
            "major_name",
            "minimum_score",
            "minimum_rank",
        ]
    )
    cleaned["plan_count"] = cleaned["plan_count"].astype("Int64")
    cleaned["minimum_score"] = cleaned["minimum_score"].astype(int)
    cleaned["minimum_rank"] = cleaned["minimum_rank"].astype(int)

    return cleaned.reset_index(drop=True)


def _clean_preference_data(frame):
    """Keep preference fields and add a 1-based preference index."""
    cleaned = frame[list(PREFERENCE_COLUMNS)].copy()

    for column in PREFERENCE_COLUMNS:
        cleaned[column] = cleaned[column].map(_clean_text_value)

    cleaned["school_code"] = cleaned["school_code"].map(
        lambda value: _format_code(value, 4)
    )
    cleaned["major_code"] = cleaned["major_code"].map(
        lambda value: _format_code(value, 3)
    )

    cleaned = cleaned.dropna(subset=list(PREFERENCE_COLUMNS))
    cleaned = cleaned[
        (cleaned["school_code"] != "")
        & (cleaned["school_name"] != "")
        & (cleaned["major_code"] != "")
        & (cleaned["major_name"] != "")
    ].copy()
    cleaned.insert(0, "preference_index", range(1, len(cleaned) + 1))

    return cleaned.reset_index(drop=True)


def _clean_text_value(value):
    """Normalize Excel text cells while preserving school and major codes."""
    if pd.isna(value):
        return ""

    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]

    return text


def _format_code(value, width):
    """Pad numeric school and major codes with leading zeroes."""
    text = _clean_text_value(value)

    if text.isdigit():
        return text.zfill(width)

    return text


def _clean_rank_series(series):
    """Coerce rank-like values such as '12,345位' to integers."""
    numeric_series = pd.to_numeric(series, errors="coerce")
    text_series = series.astype(str).str.strip()

    cleaned_text = (
        text_series
        .str.replace(",", "", regex=False)
        .str.replace("位", "", regex=False)
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"[^0-9]", "", regex=True)
        .replace("", pd.NA)
    )
    fallback_series = pd.to_numeric(cleaned_text, errors="coerce")

    return numeric_series.fillna(fallback_series)
