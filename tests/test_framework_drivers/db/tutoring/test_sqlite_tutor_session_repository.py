# 仕様: docs/spec/application-usecase.md#TutorSessionRepository
# 仕様: docs/spec/framework-drivers-persistence.md#対話-dbtutordbとの接続
"""SqliteTutorSessionRepository の統合テスト。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from domain.shared.ids import LearningSessionId, TutorSessionId
from domain.tutoring.message import MessageRole
from domain.tutoring.tutor_session import TutorSession
from framework_drivers.db.tutoring.sqlite_tutor_session_repository import (
    SqliteTutorSessionRepository,
)
from tests.test_application.fakes.tutoring.fake_id_generators import FakeMessageIdGenerator

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _session(
    *,
    tutor_session_id: str = "tutor-1",
    learning_session_id: str = "learning-1",
) -> TutorSession:
    return TutorSession.start(
        id=TutorSessionId(tutor_session_id),
        learning_session_id=LearningSessionId(learning_session_id),
        started_at=FIXED_NOW,
    )


class TestSqliteTutorSessionRepositoryRead:
    """Repository read 経路の基本動作。"""

    def test_find_returns_none_when_empty(
        self, sqlite_tutor_session_repository: SqliteTutorSessionRepository
    ) -> None:
        result = sqlite_tutor_session_repository.find_by_id(TutorSessionId("missing"))

        assert result is None

    def test_find_by_learning_session_id_returns_none_when_empty(
        self, sqlite_tutor_session_repository: SqliteTutorSessionRepository
    ) -> None:
        result = sqlite_tutor_session_repository.find_by_learning_session_id(
            LearningSessionId("missing")
        )

        assert result is None


class TestSqliteTutorSessionRepositoryWrite:
    """Repository write 経路の基本動作。"""

    def test_save_persists_session_with_learning_session_id(
        self,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        session = _session()
        sqlite_tutor_session_repository.save(session)

        row = tutor_db_conn.execute(
            """
            SELECT id, participant_id, learning_session_id
            FROM sessions
            WHERE id = ?
            """,
            ("tutor-1",),
        ).fetchone()
        assert row is not None
        assert row["participant_id"] == ""
        assert row["learning_session_id"] == "learning-1"

        loaded = sqlite_tutor_session_repository.find_by_id(TutorSessionId("tutor-1"))
        assert loaded is not None
        assert loaded.learning_session_id == LearningSessionId("learning-1")
        assert loaded.messages == ()

    def test_find_by_learning_session_id_returns_saved_session(
        self, sqlite_tutor_session_repository: SqliteTutorSessionRepository
    ) -> None:
        session = _session()
        sqlite_tutor_session_repository.save(session)

        loaded = sqlite_tutor_session_repository.find_by_learning_session_id(
            LearningSessionId("learning-1")
        )

        assert loaded is not None
        assert loaded.id == TutorSessionId("tutor-1")

    def test_save_appends_messages_without_duplicating_existing(
        self,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        message_ids = FakeMessageIdGenerator()
        session = _session()
        sqlite_tutor_session_repository.save(session)

        with_messages = session.append_message(
            message_id=message_ids.next_id(),
            role=MessageRole.USER,
            content="user message",
            created_at=FIXED_NOW,
        ).append_message(
            message_id=message_ids.next_id(),
            role=MessageRole.ASSISTANT,
            content="assistant message",
            created_at=FIXED_NOW,
        )
        sqlite_tutor_session_repository.save(with_messages)

        count = tutor_db_conn.execute(
            "SELECT COUNT(*) AS cnt FROM messages WHERE session_id = ?",
            ("tutor-1",),
        ).fetchone()
        assert count is not None
        assert int(count["cnt"]) == 2

        loaded = sqlite_tutor_session_repository.find_by_id(TutorSessionId("tutor-1"))
        assert loaded is not None
        assert len(loaded.messages) == 2
        assert loaded.messages[0].role is MessageRole.USER
        assert loaded.messages[0].content == "user message"
        assert loaded.messages[1].role is MessageRole.ASSISTANT

    def test_list_all_returns_all_sessions(
        self, sqlite_tutor_session_repository: SqliteTutorSessionRepository
    ) -> None:
        sqlite_tutor_session_repository.save(
            _session(tutor_session_id="tutor-a", learning_session_id="learning-a")
        )
        sqlite_tutor_session_repository.save(
            _session(tutor_session_id="tutor-b", learning_session_id="learning-b")
        )

        sessions = sqlite_tutor_session_repository.list_all()

        assert len(sessions) == 2
        assert {str(session.id) for session in sessions} == {"tutor-a", "tutor-b"}
