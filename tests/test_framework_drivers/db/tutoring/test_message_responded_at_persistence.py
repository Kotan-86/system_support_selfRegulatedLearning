# 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-1 A5 記録の部分, A14, A15)
# 仕様: docs/spec/dialog-log-save.md#tutordb-の表 (messages.responded_at)
"""AI 応答の生成を終えた時刻(responded_at)の永続化と復元。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from domain.shared.ids import LearningSessionId, MessageId, TutorSessionId
from domain.tutoring.message import Message, MessageRole
from domain.tutoring.tutor_session import TutorSession
from framework_drivers.db.tutoring import sqlite_tutor_session_mapper as mapper
from framework_drivers.db.tutoring.sqlite_tutor_session_repository import (
    SqliteTutorSessionRepository,
)

T0 = datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)
T7 = datetime(2026, 9, 29, 1, 0, 7, tzinfo=timezone.utc)


def _session_with_turn() -> TutorSession:
    session = TutorSession.start(
        id=TutorSessionId("ts-1"),
        learning_session_id=LearningSessionId("ls-1"),
        started_at=T0,
    )
    return session.append_message(
        message_id=MessageId("m-1"),
        role=MessageRole.USER,
        content="質問です",
        created_at=T0,
    ).append_message(
        message_id=MessageId("m-2"),
        role=MessageRole.ASSISTANT,
        content="応答です",
        created_at=T0,
        responded_at=T7,
    )


class TestResponseTimeRoundTrip:
    def test_a5_responded_at_is_saved_and_restored_and_created_at_unchanged(
        self,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
    ) -> None:
        sqlite_tutor_session_repository.save(_session_with_turn())

        restored = sqlite_tutor_session_repository.find_by_id(TutorSessionId("ts-1"))

        assert restored is not None
        user, assistant = restored.messages
        assert user.responded_at is None
        assert assistant.responded_at == T7
        # 並び順に使う created_at は、これまでどおり受け付けた時刻のまま
        assert user.created_at == T0
        assert assistant.created_at == T0

    def test_a5_responded_at_column_holds_shared_if_time_format(
        self,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        sqlite_tutor_session_repository.save(_session_with_turn())

        rows = tutor_db_conn.execute(
            "SELECT role, created_at, responded_at FROM messages ORDER BY id"
        ).fetchall()

        assert [row["role"] for row in rows] == ["user", "assistant"]
        assert rows[0]["responded_at"] is None
        assert rows[1]["responded_at"] == "2026-09-29T01:00:07+00:00"
        assert rows[1]["created_at"] == "2026-09-29T01:00:00+00:00"

    def test_a15_row_saved_before_the_change_restores_as_no_record(
        self,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        """responded_at が NULL の行(変更前に保存された AI 応答)は None で復元する。"""
        tutor_db_conn.execute(
            "INSERT INTO sessions (id, created_at, participant_id, learning_session_id) "
            "VALUES ('ts-old', '2026-06-21T12:00:00+00:00', '', 'ls-old')"
        )
        tutor_db_conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) "
            "VALUES ('ts-old', 'assistant', '旧の応答', '2026-06-21T12:00:00+00:00')"
        )
        tutor_db_conn.commit()

        restored = sqlite_tutor_session_repository.find_by_id(TutorSessionId("ts-old"))

        assert restored is not None
        assert restored.messages[0].content == "旧の応答"
        assert restored.messages[0].responded_at is None


class TestMapper:
    def test_format_responded_at_uses_time_format_or_none(self) -> None:
        with_time = Message.create(
            id=MessageId("1"),
            role=MessageRole.ASSISTANT,
            content="x",
            created_at=T0,
            responded_at=datetime(2026, 9, 29, 1, 0, 7, 999999, tzinfo=timezone.utc),
        )
        without = Message.create(
            id=MessageId("2"),
            role=MessageRole.USER,
            content="y",
            created_at=T0,
        )

        # 秒未満は切り捨て(既存の時刻の形式と同じ)
        assert mapper.format_responded_at(with_time) == "2026-09-29T01:00:07+00:00"
        assert mapper.format_responded_at(without) is None

    def test_message_row_to_message_restores_responded_at(self) -> None:
        base = {
            "id": 1,
            "session_id": "ts-1",
            "role": "assistant",
            "content": "x",
            "created_at": "2026-09-29T01:00:00+00:00",
        }

        restored = mapper.message_row_to_message(
            {**base, "responded_at": "2026-09-29T01:00:07+00:00"}
        )

        assert restored.responded_at == T7

    def test_message_row_to_message_treats_missing_null_empty_as_none(self) -> None:
        base = {
            "id": 1,
            "session_id": "ts-1",
            "role": "assistant",
            "content": "x",
            "created_at": "2026-09-29T01:00:00+00:00",
        }

        assert mapper.message_row_to_message(base).responded_at is None
        assert (
            mapper.message_row_to_message({**base, "responded_at": None}).responded_at
            is None
        )
        assert (
            mapper.message_row_to_message({**base, "responded_at": ""}).responded_at
            is None
        )

    def test_a14_message_to_insert_params_stays_seven_elements(self) -> None:
        """既存テスト(7要素の展開)を壊さない。responded_at は別の関数で扱う。"""
        message = Message.create(
            id=MessageId("1"),
            role=MessageRole.ASSISTANT,
            content="x",
            created_at=T0,
            responded_at=T7,
        )

        params = mapper.message_to_insert_params(message, TutorSessionId("ts-1"))

        assert len(params) == 7
