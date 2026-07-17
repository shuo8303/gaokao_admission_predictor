"""Validate whether a candidate score and rank belong to the same score band."""

from pathlib import Path

import pandas as pd

from config import Config
from utils.data_loader import DataFormatError, DataNotFoundError


SUPPORTED_SCORE_RANK_EXTENSIONS = {".xlsx", ".xls", ".csv"}

SCORE_RANK_COLUMNS = {
    "score": "分数",
    "highest_rank": "最高位次",
    "lowest_rank": "最低位次",
}

SCORE_RANK_POSITION_COLUMNS = (
    "score",
    "highest_rank",
    "lowest_rank",
)

COLUMN_ALIASES = {
    "score": ("分数", "成绩", "高考成绩"),
    "highest_rank": ("最高位次", "最高名次", "起始位次", "最小位次"),
    "lowest_rank": ("最低位次", "最低名次", "结束位次", "最大位次"),
}


def validate_score_rank_match(score, rank):
    """Raise ValueError when rank is outside the score band's rank range."""
    score_rank_data = load_score_rank_data()
    highest_score_row = score_rank_data.sort_values(by="score", ascending=False).iloc[0]
    lowest_score_row = score_rank_data.sort_values(by="score", ascending=True).iloc[0]
    highest_score = int(highest_score_row["score"])
    lowest_score = int(lowest_score_row["score"])
    highest_score_best_rank = int(highest_score_row["highest_rank"])

    matched_rows = score_rank_data[score_rank_data["score"] == score]

    if matched_rows.empty:
        if score > highest_score:
            if 1 <= rank < highest_score_best_rank:
                return

            raise ValueError(
                f"成绩与位次不匹配：高于分数位次表最高分 {highest_score} 分时，"
                f"位次应在 1 - {highest_score_best_rank-1} 之间，"
                f"你输入的是 {rank}。"
            )

        if score < lowest_score:
            raise ValueError("不在一段线范围：当前系统仅支持一段线上线考生。")

        raise ValueError(
            f"分数位次表缺少 {score} 分对应的位次范围，请检查数据表。"
        )

    row = matched_rows.iloc[0]
    highest_rank = int(row["highest_rank"])
    lowest_rank = int(row["lowest_rank"])

    if not highest_rank <= rank <= lowest_rank:
        raise ValueError(
            f"成绩与位次不匹配：{score} 分对应位次范围为 "
            f"{highest_rank} - {lowest_rank}，"
            f"你输入的是 {rank}。"
        )


def load_score_rank_data(score_rank_dir=None):
    """Load and normalize the score-rank reference table."""
    file_path = _get_score_rank_file(score_rank_dir)
    raw_frame = _read_score_rank_file(file_path)
    normalized = _normalize_score_rank_columns(raw_frame)
    _validate_score_rank_columns(normalized, file_path)
    return _clean_score_rank_data(normalized)


def _get_score_rank_file(score_rank_dir=None):
    """Return the first supported score-rank reference file."""
    directory = Path(score_rank_dir or Config.SCORE_RANK_DIR)

    if not directory.exists():
        raise DataNotFoundError(f"Score-rank directory does not exist: {directory}")

    files = [
        file_path
        for file_path in directory.iterdir()
        if file_path.is_file()
        and file_path.suffix.lower() in SUPPORTED_SCORE_RANK_EXTENSIONS
    ]

    if not files:
        raise DataNotFoundError(f"No score-rank table found in: {directory}")

    return sorted(files)[0]


def _read_score_rank_file(file_path):
    """Read a score-rank table from Excel or CSV."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)

    if suffix in {".xlsx", ".xls"}:
        engine = "openpyxl" if suffix == ".xlsx" else "xlrd"

        try:
            sheets = pd.read_excel(path, sheet_name=None, engine=engine)
        except ImportError as exc:
            raise DataFormatError(
                f"Reading {path.suffix} files requires the {engine} package."
            ) from exc

        frames = [sheet for sheet in sheets.values() if not sheet.empty]
        if not frames:
            raise DataFormatError(f"Score-rank workbook has no readable rows: {path}")

        return pd.concat(frames, ignore_index=True)

    raise DataFormatError(f"Unsupported score-rank file type: {path.suffix}")


def _normalize_score_rank_columns(frame):
    """Rename known headers, then fall back to score-rank table order."""
    renamed_columns = {}
    stripped_columns = {column: str(column).strip() for column in frame.columns}

    for standard_name, aliases in COLUMN_ALIASES.items():
        for original_column, stripped_column in stripped_columns.items():
            if stripped_column in aliases:
                renamed_columns[original_column] = standard_name
                break

    normalized = frame.rename(columns=renamed_columns)
    missing_columns = [
        column for column in SCORE_RANK_COLUMNS if column not in normalized.columns
    ]

    if missing_columns and len(frame.columns) >= len(SCORE_RANK_POSITION_COLUMNS):
        position_map = {
            frame.columns[index]: standard_name
            for index, standard_name in enumerate(SCORE_RANK_POSITION_COLUMNS)
        }
        normalized = frame.rename(columns=position_map)

    return normalized


def _validate_score_rank_columns(frame, file_path):
    """Ensure the score-rank table contains score and rank range fields."""
    missing_columns = [
        column for column in SCORE_RANK_COLUMNS if column not in frame.columns
    ]

    if missing_columns:
        readable_columns = ", ".join(
            SCORE_RANK_COLUMNS[column] for column in missing_columns
        )
        raise DataFormatError(
            f"Missing required columns in {file_path.name}: {readable_columns}"
        )


def _clean_score_rank_data(frame):
    """Coerce score and rank range columns to integers."""
    cleaned = frame[list(SCORE_RANK_COLUMNS)].copy()

    for column in SCORE_RANK_COLUMNS:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.dropna(subset=list(SCORE_RANK_COLUMNS))
    cleaned = cleaned.astype(int)
    cleaned["highest_rank"], cleaned["lowest_rank"] = (
        cleaned[["highest_rank", "lowest_rank"]].min(axis=1),
        cleaned[["highest_rank", "lowest_rank"]].max(axis=1),
    )

    return cleaned.reset_index(drop=True)
