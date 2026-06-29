# 仕様: docs/spec/framework-drivers-persistence.md#mapper-契約what
"""LearningSession 集約と learning.db 行の相互変換。"""
from __future__ import annotations

from datetime import datetime

from domain.learning.learning_session import LearningSession
from domain.learning.quiz_attempt import QuizAnswer, QuizAttempt
from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import (
    LectureId,
    LearnerId,
    LearningSessionId,
    QuizAttemptId,
    ViewingEventId,
)


class SqliteMapperError(ValueError):
    """SQLite 行をドメイン Entity へ変換できない。"""


def format_datetime(value: datetime) -> str:
    """ドメイン datetime を ISO 8601 文字列へ変換する（マイクロ秒は省略）。"""
    if value.microsecond:
        value = value.replace(microsecond=0)
    return value.isoformat()


def parse_datetime(value: str) -> datetime:
    """ISO 8601 文字列を datetime へ復元する。"""
    return datetime.fromisoformat(value)


def duration_to_position_delta(duration: float) -> int:
    """REAL duration を 0 方向へ切り捨てて position_delta に復元する。"""
    return int(duration)


def position_delta_to_duration(position_delta: int) -> float:
    """position_delta を REAL duration へ変換する。"""
    return float(position_delta)


def viewing_log_row_to_viewing_event(row: object) -> ViewingEvent:
    """viewing_logs 1 行を ViewingEvent に変換する。"""
    action_value = _row_value(row, "action")
    try:
        action = ViewingAction(action_value)
    except ValueError as exc:
        raise SqliteMapperError(f"unknown viewing action: {action_value!r}") from exc

    duration = float(_row_value(row, "duration"))
    position_delta = duration_to_position_delta(duration)

    try:
        return ViewingEvent.create(
            id=ViewingEventId(str(_row_value(row, "id"))),
            occurred_at=parse_datetime(str(_row_value(row, "time_stamp"))),
            video_position=int(_row_value(row, "current_time")),
            action=action,
            position_delta=position_delta,
        )
    except ValueError as exc:
        raise SqliteMapperError(str(exc)) from exc


def quiz_answer_row_to_quiz_answer(row: object) -> QuizAnswer:
    """quiz_attempt_answers 1 行を QuizAnswer に変換する。"""
    is_correct_raw = _row_value(row, "is_correct")
    if is_correct_raw not in (0, 1):
        raise SqliteMapperError(
            f"is_correct must be 0 or 1, got {is_correct_raw!r}"
        )
    return QuizAnswer(
        question_index=int(_row_value(row, "question_index")),
        selected_answer=str(_row_value(row, "selected_answer")),
        is_correct=bool(is_correct_raw),
    )


def quiz_attempt_rows_to_quiz_attempt(
    attempt_row: object, answer_rows: tuple[object, ...]
) -> QuizAttempt:
    """quiz_attempts 1 行と回答行群を QuizAttempt に変換する。"""
    answers = tuple(
        quiz_answer_row_to_quiz_answer(row)
        for row in sorted(
            answer_rows,
            key=lambda row: int(_row_value(row, "question_index")),
        )
    )
    try:
        return QuizAttempt.create(
            id=QuizAttemptId(str(_row_value(attempt_row, "id"))),
            attempted_at=parse_datetime(str(_row_value(attempt_row, "created_at"))),
            score_numerator=int(_row_value(attempt_row, "score_numerator")),
            score_denominator=int(_row_value(attempt_row, "score_denominator")),
            answers=answers,
        )
    except ValueError as exc:
        raise SqliteMapperError(str(exc)) from exc


def rows_to_learning_session(
    session_row: object,
    viewing_rows: tuple[object, ...],
    attempt_rows: tuple[object, ...],
    answers_by_attempt_id: dict[int, tuple[object, ...]],
) -> LearningSession:
    """learning_sessions と子行群から LearningSession 集約を再構成する。"""
    viewing_events = tuple(
        viewing_log_row_to_viewing_event(row)
        for row in sorted(
            viewing_rows,
            key=lambda row: (
                str(_row_value(row, "time_stamp")),
                int(_row_value(row, "id")),
            ),
        )
    )
    quiz_attempts = tuple(
        quiz_attempt_rows_to_quiz_attempt(
            attempt_row,
            answers_by_attempt_id.get(int(_row_value(attempt_row, "id")), ()),
        )
        for attempt_row in sorted(
            attempt_rows,
            key=lambda row: (
                str(_row_value(row, "created_at")),
                int(_row_value(row, "id")),
            ),
        )
    )
    return LearningSession(
        id=LearningSessionId(str(_row_value(session_row, "id"))),
        learner_id=LearnerId(str(_row_value(session_row, "learner_id"))),
        lecture_id=LectureId(str(_row_value(session_row, "lecture_id"))),
        started_at=parse_datetime(str(_row_value(session_row, "started_at"))),
        viewing_events=viewing_events,
        quiz_attempts=quiz_attempts,
    )


def learning_session_to_insert_params(session: LearningSession) -> tuple[str, str, str, str]:
    """learning_sessions INSERT 用パラメータを返す。"""
    return (
        str(session.id),
        str(session.learner_id),
        str(session.lecture_id),
        format_datetime(session.started_at),
    )


def viewing_event_to_insert_params(
    event: ViewingEvent, learning_session_id: LearningSessionId
) -> tuple[str, str, int, str, float]:
    """viewing_logs INSERT 用パラメータを返す（id は AUTOINCREMENT）。"""
    return (
        str(learning_session_id),
        format_datetime(event.occurred_at),
        event.video_position,
        event.action.value,
        position_delta_to_duration(event.position_delta),
    )


def quiz_attempt_to_insert_params(
    attempt: QuizAttempt, learning_session_id: LearningSessionId
) -> tuple[str, str, int, int]:
    """quiz_attempts INSERT 用パラメータを返す（id は AUTOINCREMENT）。"""
    return (
        str(learning_session_id),
        format_datetime(attempt.attempted_at),
        attempt.score_numerator,
        attempt.score_denominator,
    )


def quiz_answer_to_insert_params(
    answer: QuizAnswer, attempt_id: int
) -> tuple[int, int, str, int]:
    """quiz_attempt_answers INSERT 用パラメータを返す。"""
    return (
        attempt_id,
        answer.question_index,
        answer.selected_answer,
        1 if answer.is_correct else 0,
    )


def _row_value(row: object, key: str) -> object:
    if hasattr(row, "keys") and key in row.keys():  # type: ignore[union-attr]
        return row[key]  # type: ignore[index]
    getter = getattr(row, "get", None)
    if callable(getter):
        return getter(key)
    return getattr(row, key)
