# 仕様: docs/spec/framework-drivers-persistence.md#対話-dbtutordbとの接続
# 仕様: docs/spec/framework-drivers-persistence.md#mapper-契約what
"""TutorSession 集約と tutor.db 行の相互変換。"""
from __future__ import annotations

from domain.shared.ids import LearningSessionId, MessageId, TutorSessionId
from domain.tutoring.message import Message, MessageRole
from domain.tutoring.tutor_session import TutorSession

from framework_drivers.db.learning.sqlite_learning_session_mapper import (
    format_datetime,
    parse_datetime,
)


class SqliteTutorMapperError(ValueError):
    """SQLite 行を Tutoring ドメインへ変換できない。"""


def tutor_session_to_insert_params(session: TutorSession) -> tuple[str, str, str, str]:
    """TutorSession を sessions INSERT パラメータへ変換する。"""
    return (
        str(session.id),
        format_datetime(session.started_at),
        "",
        str(session.learning_session_id),
    )


def message_to_insert_params(
    message: Message, tutor_session_id: TutorSessionId
) -> tuple[str, str, str, str]:
    """Message を messages INSERT パラメータへ変換する。"""
    return (
        str(tutor_session_id),
        message.role.value,
        message.content,
        format_datetime(message.created_at),
    )


def message_row_to_message(row: object) -> Message:
    """messages 1 行を Message に変換する。"""
    role_value = _row_value(row, "role")
    try:
        role = MessageRole(role_value)
    except ValueError as exc:
        raise SqliteTutorMapperError(f"unknown message role: {role_value!r}") from exc

    try:
        return Message.create(
            id=MessageId(str(_row_value(row, "id"))),
            role=role,
            content=str(_row_value(row, "content")),
            created_at=parse_datetime(str(_row_value(row, "created_at"))),
        )
    except ValueError as exc:
        raise SqliteTutorMapperError(str(exc)) from exc


def rows_to_tutor_session(
    session_row: object,
    message_rows: tuple[object, ...],
) -> TutorSession:
    """sessions 行と messages 行群から TutorSession を復元する。"""
    messages = tuple(message_row_to_message(row) for row in message_rows)
    started_at = parse_datetime(str(_row_value(session_row, "created_at")))

    return TutorSession(
        id=TutorSessionId(str(_row_value(session_row, "id"))),
        learning_session_id=LearningSessionId(
            str(_row_value(session_row, "learning_session_id"))
        ),
        started_at=started_at,
        messages=messages,
    )


def _row_value(row: object, key: str) -> object:
    if isinstance(row, dict):
        return row[key]
    return row[key]  # type: ignore[index]
