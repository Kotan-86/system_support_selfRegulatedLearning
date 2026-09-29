# 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-1 A11, A15)
# 仕様: docs/spec/dialog-log-save.md#tutordb-の表
"""tutor.db のスキーマ: dialog_logs の新設、messages.responded_at の追加、変更前DBへの対応。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from framework_drivers.db.tutoring.sqlite_connection import (
    apply_tutor_schema,
    connect_in_memory_tutor_db,
)

# 変更前の tutor.db の形(dialog_logs なし、messages に responded_at なし)。
_LEGACY_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    participant_id TEXT NOT NULL DEFAULT '',
    learning_session_id TEXT NOT NULL DEFAULT ''
);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    utterance_type TEXT,
    dialogue_move TEXT,
    interpretation_state TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
CREATE INDEX idx_messages_session_created ON messages(session_id, created_at);
"""

_MESSAGE_ORIGINAL_COLUMNS = (
    "id, session_id, role, content, created_at, "
    "utterance_type, dialogue_move, interpretation_state"
)


def _legacy_conn(tmp_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(tmp_path / "legacy_tutor.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript(_LEGACY_SCHEMA)
    conn.execute(
        "INSERT INTO sessions (id, created_at, participant_id, learning_session_id) "
        "VALUES ('ts-old', '2026-06-21T12:00:00+00:00', '', 'ls-old')"
    )
    conn.execute(
        "INSERT INTO messages (session_id, role, content, created_at) "
        "VALUES ('ts-old', 'user', '旧の発言', '2026-06-21T12:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO messages (session_id, role, content, created_at, "
        "utterance_type, dialogue_move, interpretation_state) "
        "VALUES ('ts-old', 'assistant', '旧の応答', '2026-06-21T12:00:00+00:00', "
        "'FACT_REQUEST', 'ELICIT_REASON', '{\"a\": 1}')"
    )
    conn.commit()
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> dict[str, sqlite3.Row]:
    return {row["name"]: row for row in conn.execute(f"PRAGMA table_info({table})")}


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


class TestFreshSchema:
    """新規の tutor.db に、dialog_logs と messages.responded_at がある。"""

    def test_dialog_logs_table_has_the_shared_if_columns(
        self, tutor_db_conn: sqlite3.Connection
    ) -> None:
        columns = _columns(tutor_db_conn, "dialog_logs")

        assert set(columns) == {
            "session_id",
            "participant_id",
            "lecture_id",
            "learning_session_id",
            "end_method",
            "ended_at",
            "log_json",
        }
        # session_id が主キー、他は必須(NOT NULL)
        assert columns["session_id"]["pk"] == 1
        for name in (
            "participant_id",
            "lecture_id",
            "learning_session_id",
            "end_method",
            "ended_at",
            "log_json",
        ):
            assert columns[name]["notnull"] == 1, name

    def test_messages_has_nullable_responded_at(
        self, tutor_db_conn: sqlite3.Connection
    ) -> None:
        columns = _columns(tutor_db_conn, "messages")

        assert "responded_at" in columns
        assert columns["responded_at"]["notnull"] == 0

    def test_a11_same_session_id_cannot_be_inserted_twice(
        self, tutor_db_conn: sqlite3.Connection
    ) -> None:
        """A11: 同じ対話セッションIDの行を2つ作れない(DB の制約)。"""
        tutor_db_conn.execute(
            "INSERT INTO sessions (id, created_at, participant_id, learning_session_id) "
            "VALUES ('ts-1', '2026-09-29T01:00:00+00:00', '', 'ls-1')"
        )
        insert = (
            "INSERT INTO dialog_logs (session_id, participant_id, lecture_id, "
            "learning_session_id, end_method, ended_at, log_json) "
            "VALUES ('ts-1', '1', 'lecture-1', 'ls-1', 'end_button', "
            "'2026-09-29T01:05:00+00:00', '{}')"
        )
        tutor_db_conn.execute(insert)

        with pytest.raises(sqlite3.IntegrityError):
            tutor_db_conn.execute(insert)

        count = tutor_db_conn.execute("SELECT COUNT(*) AS c FROM dialog_logs").fetchone()
        assert count["c"] == 1


class TestLegacySchemaMigration:
    """A15: 変更前の形の tutor.db に適用しても動き、既存の行は変わらない。"""

    def test_a15_apply_adds_table_and_column_and_keeps_existing_rows(
        self, tmp_path: Path, tutor_schema_path: Path
    ) -> None:
        conn = _legacy_conn(tmp_path)
        before = [
            dict(row)
            for row in conn.execute(
                f"SELECT {_MESSAGE_ORIGINAL_COLUMNS} FROM messages ORDER BY id"
            )
        ]
        assert "dialog_logs" not in _table_names(conn)
        assert "responded_at" not in _columns(conn, "messages")

        apply_tutor_schema(conn, tutor_schema_path)

        assert "dialog_logs" in _table_names(conn)
        assert "responded_at" in _columns(conn, "messages")
        after = [
            dict(row)
            for row in conn.execute(
                f"SELECT {_MESSAGE_ORIGINAL_COLUMNS} FROM messages ORDER BY id"
            )
        ]
        assert after == before
        # 変更前の行の responded_at は「記録なし」(NULL)
        rows = conn.execute("SELECT responded_at FROM messages").fetchall()
        assert len(rows) == 2
        assert all(row["responded_at"] is None for row in rows)
        conn.close()

    def test_a15_apply_twice_is_idempotent(
        self, tmp_path: Path, tutor_schema_path: Path
    ) -> None:
        conn = _legacy_conn(tmp_path)

        apply_tutor_schema(conn, tutor_schema_path)
        apply_tutor_schema(conn, tutor_schema_path)

        names = list(_columns(conn, "messages"))
        assert names.count("responded_at") == 1
        count = conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()
        assert count["c"] == 2
        conn.close()

    def test_a15_in_memory_helper_also_migrates(self, tutor_schema_path: Path) -> None:
        conn = connect_in_memory_tutor_db(tutor_schema_path)
        assert "responded_at" in _columns(conn, "messages")
        assert "dialog_logs" in _table_names(conn)
        conn.close()
