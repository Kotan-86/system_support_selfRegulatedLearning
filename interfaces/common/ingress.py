# 仕様: docs/spec/interfaces-layer.md#ingress-規約
"""外部入力を Application 層 DTO 用の型へ正規化する。"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from application.common.errors import ErrorCode, ValidationError
from application.common.result import Result, err, ok
from application.common.viewing_seconds import (
    parse_position_delta as _parse_position_delta,
)
from application.common.viewing_seconds import (
    parse_video_position as _parse_video_position,
)
from domain.learning.quiz_attempt import QuizAnswer
from domain.learning.viewing_event import ViewingAction
from domain.shared.ids import LearnerId, LectureId, TutorSessionId

from interfaces.common.default_lecture import resolve_default_lecture_id


def parse_learner_id(participant_id: str) -> Result[LearnerId, ValidationError]:
    """participant_id を LearnerId へ変換する。空文字・空白のみは拒否する。"""
    normalized = participant_id.strip()
    if not normalized:
        return err(ValidationError("participant_id must not be empty"))
    try:
        return ok(LearnerId(normalized))
    except ValueError as exc:
        return err(ValidationError(str(exc)))


def parse_lecture_id(
    lecture_id: str | None,
    *,
    use_default_when_missing: bool = True,
) -> Result[LectureId, ValidationError]:
    """lecture_id を LectureId へ変換する。未送信時は default_lecture を用いる。"""
    if lecture_id is None:
        if use_default_when_missing:
            return ok(resolve_default_lecture_id())
        return err(ValidationError("lecture_id must not be empty"))
    normalized = lecture_id.strip()
    if not normalized:
        return err(ValidationError("lecture_id must not be empty"))
    try:
        return ok(LectureId(normalized))
    except ValueError as exc:
        return err(ValidationError(str(exc)))


def parse_video_position(value: Any) -> Result[int, ValidationError]:
    """current_time を video_position（整数秒）へ正規化する。"""
    return _parse_video_position(value)


def parse_position_delta(value: Any) -> Result[int, ValidationError]:
    """duration を position_delta（整数秒）へ正規化する。"""
    return _parse_position_delta(value)


def _parse_datetime_string(
    value: Any,
    *,
    field_name: str,
) -> Result[datetime, ValidationError]:
    """ISO 8601 文字列を datetime へ変換する。"""
    if value is None:
        return err(ValidationError(f"{field_name} is required"))
    if not isinstance(value, str):
        return err(ValidationError(f"{field_name} must be a string"))
    normalized = value.strip()
    if not normalized:
        return err(ValidationError(f"{field_name} must not be empty"))
    iso_value = normalized[:-1] + "+00:00" if normalized.endswith("Z") else normalized
    try:
        return ok(datetime.fromisoformat(iso_value))
    except ValueError as exc:
        return err(ValidationError(f"invalid {field_name}: {exc}"))


def parse_occurred_at(value: Any) -> Result[datetime, ValidationError]:
    """time_stamp を occurred_at へ変換する。"""
    return _parse_datetime_string(value, field_name="time_stamp")


def parse_attempted_at(value: Any) -> Result[datetime, ValidationError]:
    """timestamp / created_at を attempted_at へ変換する。"""
    return _parse_datetime_string(value, field_name="timestamp")


def parse_viewing_action(value: Any) -> Result[ViewingAction, ValidationError]:
    """action を ViewingAction へ変換する。"""
    if value is None:
        return err(ValidationError("action is required"))
    if not isinstance(value, str):
        return err(ValidationError("action must be a string"))
    normalized = value.strip()
    if not normalized:
        return err(ValidationError("action must not be empty"))
    try:
        return ok(ViewingAction(normalized))
    except ValueError:
        valid = ", ".join(sorted(action.value for action in ViewingAction))
        return err(
            ValidationError(
                f"unknown action: {normalized!r}. Must be one of: {valid}"
            )
        )


def parse_required_int(value: Any, *, field_name: str) -> Result[int, ValidationError]:
    """必須の整数フィールドを正規化する。"""
    if value is None:
        return err(ValidationError(f"{field_name} is required"))
    if isinstance(value, bool):
        return err(ValidationError(f"{field_name} must be an integer, not bool"))
    if isinstance(value, int):
        return ok(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return err(ValidationError(f"{field_name} must be a finite number"))
        if value != int(value):
            return err(ValidationError(f"{field_name} must be an integer"))
        return ok(int(value))
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return err(ValidationError(f"{field_name} must be an integer"))
        try:
            numeric = float(stripped)
        except ValueError:
            return err(ValidationError(f"{field_name} must be an integer"))
        if not math.isfinite(numeric) or numeric != int(numeric):
            return err(ValidationError(f"{field_name} must be an integer"))
        return ok(int(numeric))
    return err(ValidationError(f"{field_name} must be an integer"))


def _parse_is_correct(value: Any, *, index: int) -> Result[bool, ValidationError]:
    if isinstance(value, bool):
        return ok(value)
    if isinstance(value, int) and value in (0, 1):
        return ok(bool(value))
    return err(
        ValidationError(f"answers[{index}].is_correct must be a boolean or 0/1")
    )


def parse_user_message(value: Any) -> Result[str, ValidationError]:
    """message を user_message へ変換する。空・未送信は EMPTY_USER_MESSAGE とする。"""
    if value is None:
        return err(
            ValidationError(
                "user_message must not be empty",
                code=ErrorCode.EMPTY_USER_MESSAGE,
            )
        )
    if not isinstance(value, str):
        return err(
            ValidationError(
                "user_message must be a string",
                code=ErrorCode.EMPTY_USER_MESSAGE,
            )
        )
    if not value:
        return err(
            ValidationError(
                "user_message must not be empty",
                code=ErrorCode.EMPTY_USER_MESSAGE,
            )
        )
    return ok(value)


def parse_tutor_session_id(
    value: Any,
) -> Result[TutorSessionId | None, ValidationError]:
    """session_id を tutor_session_id へ変換する。未送信・空文字は None とする。"""
    if value is None:
        return ok(None)
    if not isinstance(value, str):
        return err(ValidationError("session_id must be a string"))
    normalized = value.strip()
    if not normalized:
        return ok(None)
    try:
        return ok(TutorSessionId(normalized))
    except ValueError as exc:
        return err(ValidationError(str(exc)))


def parse_quiz_answers(value: Any) -> Result[tuple[QuizAnswer, ...], ValidationError]:
    """answers 配列を QuizAnswer のタプルへ変換する。"""
    if not isinstance(value, list):
        return err(ValidationError("answers must be a list"))
    if len(value) == 0:
        return err(ValidationError("answers must contain at least one item"))

    answers: list[QuizAnswer] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            return err(ValidationError(f"answers[{index}] must be an object"))

        question_index_result = parse_required_int(
            item.get("question_index"),
            field_name=f"answers[{index}].question_index",
        )
        if question_index_result.is_err:
            return question_index_result  # type: ignore[return-value]

        selected = item.get("selected_answer")
        if selected is None:
            return err(
                ValidationError(f"answers[{index}].selected_answer is required")
            )
        if not isinstance(selected, str):
            return err(
                ValidationError(f"answers[{index}].selected_answer must be a string")
            )
        selected_answer = selected.strip()
        if not selected_answer:
            return err(
                ValidationError(f"answers[{index}].selected_answer must not be empty")
            )

        is_correct_result = _parse_is_correct(
            item.get("is_correct"),
            index=index,
        )
        if is_correct_result.is_err:
            return is_correct_result  # type: ignore[return-value]

        answers.append(
            QuizAnswer(
                question_index=question_index_result.value,
                selected_answer=selected_answer,
                is_correct=is_correct_result.value,
            )
        )

    return ok(tuple(answers))
