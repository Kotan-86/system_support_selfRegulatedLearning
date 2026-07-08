# 仕様: docs/spec/framework-drivers-persistence.md#mapper-契約what
# 仕様: docs/spec/domain-model.md#Message（対話メッセージ）
"""TutorSession 集約と tutor.db 行の相互変換。"""
from __future__ import annotations

from domain.shared.ids import LearningSessionId, MessageId, TutorSessionId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from domain.tutoring.message import Message, MessageRole
from domain.tutoring.tutor_session import TutorSession

from framework_drivers.db.learning.sqlite_learning_session_mapper import (
    format_datetime,
    parse_datetime,
)
from interfaces.tutoring.tutoring_model_json import (
    deserialize_interpretation_state_card,
    serialize_interpretation_state_card,
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
) -> tuple[str, str, str, str, str | None, str | None, str | None]:
    """Message を messages INSERT パラメータへ変換する。"""
    return (
        str(tutor_session_id),
        message.role.value,
        message.content,
        format_datetime(message.created_at),
        message.utterance_type.value if message.utterance_type is not None else None,
        message.dialogue_move.value if message.dialogue_move is not None else None,
        serialize_interpretation_state_card(message.interpretation_state),
    )


def message_row_to_message(row: object) -> Message:
    """messages 1 行を Message に変換する。"""
    role_value = _row_value(row, "role")
    try:
        role = MessageRole(role_value)
    except ValueError as exc:
        raise SqliteTutorMapperError(f"unknown message role: {role_value!r}") from exc

    utterance_type = _parse_optional_enum(
        _optional_row_value(row, "utterance_type"),
        enum_type=LearnerUtteranceType,
        field_name="utterance_type",
    )
    dialogue_move = _parse_optional_enum(
        _optional_row_value(row, "dialogue_move"),
        enum_type=DialogueMove,
        field_name="dialogue_move",
    )
    interpretation_state_raw = _optional_row_value(row, "interpretation_state")
    try:
        interpretation_state = deserialize_interpretation_state_card(
            str(interpretation_state_raw)
            if interpretation_state_raw is not None
            else None
        )
    except ValueError as exc:
        raise SqliteTutorMapperError(str(exc)) from exc

    try:
        return Message.create(
            id=MessageId(str(_row_value(row, "id"))),
            role=role,
            content=str(_row_value(row, "content")),
            created_at=parse_datetime(str(_row_value(row, "created_at"))),
            utterance_type=utterance_type,
            dialogue_move=dialogue_move,
            interpretation_state=interpretation_state,
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


def _optional_row_value(row: object, key: str) -> object | None:
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]  # type: ignore[index]
    except (KeyError, IndexError):
        return None


def _parse_optional_enum(
    raw: object | None,
    *,
    enum_type: type[LearnerUtteranceType] | type[DialogueMove],
    field_name: str,
) -> LearnerUtteranceType | DialogueMove | None:
    if raw is None or raw == "":
        return None
    try:
        return enum_type(str(raw))
    except ValueError as exc:
        raise SqliteTutorMapperError(f"unknown {field_name}: {raw!r}") from exc
