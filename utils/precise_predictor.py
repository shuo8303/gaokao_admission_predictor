"""Precise prediction helpers for uploaded preference tables."""


def predict_first_admission(preferences, admission_data, score, rank):
    """Return the first preference that reaches the published filing line."""
    for preference in preferences.to_dict(orient="records"):
        matched_program = _find_matching_program(preference, admission_data)

        if matched_program is None:
            continue
        score_reached = score > matched_program["minimum_score"]
        rank_reached = (
            score == matched_program["minimum_score"]
            and rank <= matched_program["minimum_rank"]
        )

        if score_reached or rank_reached:
            return {
                "preference_index": preference["preference_index"],
                "school_code": matched_program["school_code"],
                "school_name": matched_program["school_name"],
                "major_code": matched_program["major_code"],
                "major_name": matched_program["major_name"],
                "minimum_score": matched_program["minimum_score"],
                "minimum_rank": matched_program["minimum_rank"],
                "basis": _build_prediction_basis(
                    score,
                    rank,
                    matched_program["minimum_score"],
                    matched_program["minimum_rank"],
                    score_reached,
                    rank_reached,
                ),
            }

    return None


def evaluate_all_preferences(preferences, admission_data, score, rank):
    """Return every preference with official line data and pass status.

    The exported report keeps the user's original preference order. A
    preference is marked as reached when it follows the same logic as precise
    prediction: score is higher than the minimum score, or score equals the
    minimum score and rank is not worse than the minimum rank.
    """
    evaluated_preferences = []

    for preference in preferences.to_dict(orient="records"):
        matched_program = _find_matching_program(preference, admission_data)

        if matched_program is None:
            evaluated_preferences.append(
                {
                    "preference_index": preference["preference_index"],
                    "school_code": preference["school_code"],
                    "school_name": preference["school_name"],
                    "major_code": preference["major_code"],
                    "major_name": preference["major_name"],
                    "minimum_score": "",
                    "minimum_rank": "",
                    "is_reached": "-",
                }
            )
            continue

        reached = _is_line_reached(
            score,
            rank,
            matched_program["minimum_score"],
            matched_program["minimum_rank"],
        )
        evaluated_preferences.append(
            {
                "preference_index": preference["preference_index"],
                "school_code": matched_program["school_code"],
                "school_name": matched_program["school_name"],
                "major_code": matched_program["major_code"],
                "major_name": matched_program["major_name"],
                "minimum_score": matched_program["minimum_score"],
                "minimum_rank": matched_program["minimum_rank"],
                "is_reached": "是" if reached else "-",
            }
        )

    return evaluated_preferences


def parse_precise_inputs(score_value, rank_value):
    """Validate precise prediction score and rank input."""
    try:
        score = int(score_value)
        rank = int(rank_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("请输入有效的高考成绩和高考位次。") from exc

    if score < 0 or rank <= 0:
        raise ValueError("高考成绩不能为负数，高考位次必须大于 0。")

    return score, rank


def _find_matching_program(preference, admission_data):
    """Find official filing data by code first, then by school and major name."""
    code_matches = admission_data[
        (admission_data["school_code"] == preference["school_code"])
        & (admission_data["major_code"] == preference["major_code"])
    ]

    if not code_matches.empty:
        return code_matches.iloc[0].to_dict()

    name_matches = admission_data[
        (admission_data["school_name"] == preference["school_name"])
        & (admission_data["major_name"] == preference["major_name"])
    ]

    if not name_matches.empty:
        return name_matches.iloc[0].to_dict()

    return None


def _is_line_reached(score, rank, minimum_score, minimum_rank):
    """Return whether a candidate reaches one published filing line."""
    return score > minimum_score or (score == minimum_score and rank <= minimum_rank)


def _build_prediction_basis(
    score,
    rank,
    minimum_score,
    minimum_rank,
    score_reached,
    rank_reached,
):
    """Build a readable explanation for the matched preference."""
    reasons = []

    if score_reached:
        reasons.append(f"考生成绩 {score} > 投档分数线 {minimum_score}")

    if rank_reached:
        reasons.append(
            f"考生成绩 {score} = 投档分数线 {minimum_score}，"
            f"且考生位次 {rank} <= 投档最低位次 {minimum_rank}"
        )

    return "；".join(reasons)
