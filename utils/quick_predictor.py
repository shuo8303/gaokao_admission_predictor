"""Quick prediction helpers for score and rank based filtering."""

PAGE_SCORE_FLOOR_OFFSET = 3
DOWNLOAD_SCORE_RANGE = 3

SORT_OPTIONS = {
    "school": "school_name",
    "rank": "minimum_rank",
    "score": "minimum_score",
}

SORT_LABELS = {
    "school": "学校名称排序",
    "rank": "最低位次排序",
    "score": "最低分排序",
}


def find_quick_matches(admission_data, score, rank, sort_by="rank"):
    """Return rows not lower than score minus 3 whose rank line is reached."""
    sort_key = SORT_OPTIONS.get(sort_by, SORT_OPTIONS["rank"])
    in_score_window = admission_data["minimum_score"] >= score - PAGE_SCORE_FLOOR_OFFSET
    rank_reached = admission_data["minimum_rank"] >= rank
    matched = admission_data[in_score_window & rank_reached].copy()

    return _sort_matches(matched, sort_key)


def find_download_matches(admission_data, score, rank, sort_by="rank"):
    """Return rows within three points above or below score for download."""
    sort_key = SORT_OPTIONS.get(sort_by, SORT_OPTIONS["rank"])
    in_score_range = admission_data["minimum_score"].between(
        score - DOWNLOAD_SCORE_RANGE,
        score + DOWNLOAD_SCORE_RANGE,
        inclusive="both",
    )
    rank_reached = admission_data["minimum_rank"] >= rank
    matched = admission_data[in_score_range & rank_reached].copy()

    return _sort_matches(matched, sort_key)


def parse_candidate_inputs(score_value, rank_value):
    """Validate form input and return numeric score and rank."""
    try:
        score = int(score_value)
        rank = int(rank_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("请输入有效的高考成绩和高考位次。") from exc

    if score < 0 or rank <= 0:
        raise ValueError("高考成绩不能为负数，高考位次必须大于 0。")

    return score, rank


def _sort_matches(matched, sort_key):
    """Sort matched rows and return serializable records."""
    if sort_key == "school_name":
        matched = matched.sort_values(by=[sort_key, "major_name"], ascending=True)
    else:
        matched = matched.sort_values(by=[sort_key, "school_name"], ascending=True)

    return matched.to_dict(orient="records")
