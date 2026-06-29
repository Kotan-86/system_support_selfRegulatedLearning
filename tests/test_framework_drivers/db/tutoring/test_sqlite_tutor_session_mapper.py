# 仕様: docs/spec/framework-drivers-persistence.md#mapper-契約what
"""sqlite_tutor_session_mapper の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from domain.shared.ids import LearningSessionId, MessageId, TutorSessionId
from domain.tutoring.message import Message, MessageRole
from domain.tutoring.tutor_session import TutorSession
from framework_drivers.db.tutoring.sqlite_tutor_session_mapper import (
    message_row_to_message,
    rows_to_tutor_session,
    tutor_session_to_insert_params,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


class TestSqliteTutorSessionMapper:
    """Mapper の round-trip 相当を検証する。"""

    def test_tutor_session_to_insert_params_maps_learning_session_id(self) -> None:
        session = TutorSession.start(
            id=TutorSessionId("tutor-1"),
            learning_session_id=LearningSessionId("learning-1"),
            started_at=FIXED_NOW,
        )

        params = tutor_session_to_insert_params(session)

        assert params == ("tutor-1", "2026-06-21T12:00:00+00:00", "", "learning-1")

    def test_rows_to_tutor_session_restores_messages(self) -> None:
        session_row = {
            "id": "tutor-1",
            "created_at": "2026-06-21T12:00:00+00:00",
            "participant_id": "",
            "learning_session_id": "learning-1",
        }
        message_row = {
            "id": 7,
            "session_id": "tutor-1",
            "role": "user",
            "content": "hello",
            "created_at": "2026-06-21T12:01:00+00:00",
        }

        session = rows_to_tutor_session(session_row, (message_row,))

        assert session.id == TutorSessionId("tutor-1")
        assert session.learning_session_id == LearningSessionId("learning-1")
        assert len(session.messages) == 1
        assert session.messages[0].id == MessageId("7")
        assert session.messages[0].role is MessageRole.USER

    def test_message_row_to_message_parses_role(self) -> None:
        message = message_row_to_message(
            {
                "id": 1,
                "session_id": "tutor-1",
                "role": "assistant",
                "content": "reply",
                "created_at": "2026-06-21T12:00:00+00:00",
            }
        )

        assert message.role is MessageRole.ASSISTANT
        assert message.content == "reply"
