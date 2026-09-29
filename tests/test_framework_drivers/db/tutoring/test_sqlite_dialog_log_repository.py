# 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-1 A2, A4, A8, A11, A12, A17)
# 仕様: docs/spec/dialog-log-save.md#tutordb-の表 (dialog_logs、upsert)
"""SqliteDialogLogRepository: dialog_logs への upsert。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

import pytest

from application.tutoring.dto.save_dialog_log import DialogLog, EndMethod
from domain.shared.ids import LearningSessionId, MessageId, TutorSessionId
from domain.tutoring.message import MessageRole
from domain.tutoring.tutor_session import TutorSession
from framework_drivers.db.tutoring.sqlite_dialog_log_repository import (
    SqliteDialogLogRepository,
)
from framework_drivers.db.tutoring.sqlite_tutor_session_repository import (
    SqliteTutorSessionRepository,
)

T0 = datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)
T7 = datetime(2026, 9, 29, 1, 0, 7, tzinfo=timezone.utc)
SAVE_1 = datetime(2026, 9, 29, 1, 5, 0, tzinfo=timezone.utc)
SAVE_2 = datetime(2026, 9, 29, 1, 30, 0, tzinfo=timezone.utc)


def _make_session(
    repo: SqliteTutorSessionRepository, session_id: str, texts: list[tuple[str, str]]
) -> TutorSession:
    session = TutorSession.start(
        id=TutorSessionId(session_id),
        learning_session_id=LearningSessionId(f"ls-{session_id}"),
        started_at=T0,
    )
    counter = 0
    for user_text, ai_text in texts:
        counter += 2
        session = session.append_message(
            message_id=MessageId(str(counter)),
            role=MessageRole.USER,
            content=user_text,
            created_at=T0,
        ).append_message(
            message_id=MessageId(str(counter + 1)),
            role=MessageRole.ASSISTANT,
            content=ai_text,
            created_at=T0,
            responded_at=T7,
        )
    repo.save(session)
    return session


def _log(session: TutorSession, *, method: EndMethod, at: datetime) -> DialogLog:
    return DialogLog(
        participant_id="1",
        lecture_id="lecture-1",
        learning_session_id=str(session.learning_session_id),
        tutor_session_id=str(session.id),
        ended_at=at,
        end_method=method,
        messages=session.messages,
    )


def _rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM dialog_logs ORDER BY session_id").fetchall()


class TestSave:
    def test_a2_a4_a8_columns_and_json_are_written_and_consistent(
        self,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        session = _make_session(
            sqlite_tutor_session_repository, "ts-1", [("質問1", "回答1"), ("質問2", "回答2")]
        )
        repo = SqliteDialogLogRepository(tutor_db_conn)

        repo.save(_log(session, method=EndMethod.END_BUTTON, at=SAVE_1))

        (row,) = _rows(tutor_db_conn)
        assert row["session_id"] == "ts-1"
        assert row["participant_id"] == "1"
        assert row["lecture_id"] == "lecture-1"
        assert row["learning_session_id"] == "ls-ts-1"
        assert row["end_method"] == "end_button"
        assert row["ended_at"] == "2026-09-29T01:05:00+00:00"
        body = json.loads(row["log_json"])
        # 列と JSON の値は一致する
        assert body["participant_id"] == row["participant_id"]
        assert body["lecture_id"] == row["lecture_id"]
        assert body["learning_session_id"] == row["learning_session_id"]
        assert body["tutor_session_id"] == row["session_id"]
        assert body["end_method"] == row["end_method"]
        assert body["ended_at"] == row["ended_at"]
        assert body["format_version"] == 1
        assert [(m["role"], m["content"]) for m in body["messages"]] == [
            ("user", "質問1"),
            ("assistant", "回答1"),
            ("user", "質問2"),
            ("assistant", "回答2"),
        ]

    def test_a11_saving_twice_keeps_one_row(
        self,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        session = _make_session(sqlite_tutor_session_repository, "ts-1", [("質問", "回答")])
        repo = SqliteDialogLogRepository(tutor_db_conn)
        log = _log(session, method=EndMethod.END_BUTTON, at=SAVE_1)

        repo.save(log)
        repo.save(log)

        assert len(_rows(tutor_db_conn)) == 1

    def test_a12_second_save_overwrites_with_latest_content(
        self,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        first_session = _make_session(
            sqlite_tutor_session_repository, "ts-1", [("質問1", "回答1")]
        )
        repo = SqliteDialogLogRepository(tutor_db_conn)
        repo.save(_log(first_session, method=EndMethod.END_BUTTON, at=SAVE_1))
        longer = first_session.append_message(
            message_id=MessageId("90"),
            role=MessageRole.USER,
            content="質問2",
            created_at=T0,
        ).append_message(
            message_id=MessageId("91"),
            role=MessageRole.ASSISTANT,
            content="回答2",
            created_at=T0,
            responded_at=T7,
        )

        repo.save(_log(longer, method=EndMethod.PAGE_LEAVE, at=SAVE_2))

        (row,) = _rows(tutor_db_conn)
        assert row["end_method"] == "page_leave"
        assert row["ended_at"] == "2026-09-29T01:30:00+00:00"
        body = json.loads(row["log_json"])
        assert body["end_method"] == "page_leave"
        assert body["ended_at"] == "2026-09-29T01:30:00+00:00"
        assert [m["content"] for m in body["messages"]] == [
            "質問1",
            "回答1",
            "質問2",
            "回答2",
        ]

    def test_different_sessions_get_different_rows(
        self,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        one = _make_session(sqlite_tutor_session_repository, "ts-1", [("a", "b")])
        two = _make_session(sqlite_tutor_session_repository, "ts-2", [("c", "d")])
        repo = SqliteDialogLogRepository(tutor_db_conn)

        repo.save(_log(one, method=EndMethod.END_BUTTON, at=SAVE_1))
        repo.save(_log(two, method=EndMethod.END_BUTTON, at=SAVE_1))

        assert [row["session_id"] for row in _rows(tutor_db_conn)] == ["ts-1", "ts-2"]

    def test_a13_empty_messages_are_saved_as_empty_list(
        self,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        session = _make_session(sqlite_tutor_session_repository, "ts-1", [])
        repo = SqliteDialogLogRepository(tutor_db_conn)

        repo.save(_log(session, method=EndMethod.END_BUTTON, at=SAVE_1))

        (row,) = _rows(tutor_db_conn)
        assert json.loads(row["log_json"])["messages"] == []


class TestFailure:
    def test_a17_failed_save_raises_and_keeps_the_previous_log(
        self,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        good = _make_session(sqlite_tutor_session_repository, "ts-1", [("質問", "回答")])
        repo = SqliteDialogLogRepository(tutor_db_conn)
        repo.save(_log(good, method=EndMethod.END_BUTTON, at=SAVE_1))
        before = [dict(row) for row in _rows(tutor_db_conn)]
        # sessions に無い対話セッションIDへの保存は、外部キー制約で失敗する
        orphan = TutorSession.start(
            id=TutorSessionId("ts-missing"),
            learning_session_id=LearningSessionId("ls-missing"),
            started_at=T0,
        )

        with pytest.raises(sqlite3.Error):
            repo.save(_log(orphan, method=EndMethod.END_BUTTON, at=SAVE_2))

        assert [dict(row) for row in _rows(tutor_db_conn)] == before
