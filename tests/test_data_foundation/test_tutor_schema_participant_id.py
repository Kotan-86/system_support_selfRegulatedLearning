"""
Phase 1 Step 1.2: 対話用 DB のスキーマ

sessions に participant_id, learning_session_id (TEXT, NOT NULL) が存在することを検証する。
仕様: docs/spec/framework-drivers-persistence.md
"""
import sqlite3
from pathlib import Path

import pytest


def _execute_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql)


class TestStep1_2SessionsHasParticipantId:
    """対話用スキーマの sessions に participant_id があること。"""

    def test_sessions_has_participant_id_column(
        self, tutor_schema_path: Path
    ) -> None:
        """sessions に participant_id カラムが定義されている。"""
        if not tutor_schema_path.exists():
            pytest.skip("db/schema.sql が未作成のためスキップ")
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, tutor_schema_path)
        cur = conn.execute(
            "SELECT name, type, [notnull] FROM pragma_table_info('sessions') ORDER BY cid"
        )
        rows = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
        conn.close()
        assert "participant_id" in rows, "sessions に participant_id カラムがあること"
        col_type, notnull = rows["participant_id"]
        assert notnull == 1, "participant_id は NOT NULL であること"
        assert col_type.upper() == "TEXT", "participant_id は TEXT 型であること"

    def test_sessions_still_has_id_and_created_at(
        self, tutor_schema_path: Path
    ) -> None:
        """sessions には従来どおり id と created_at もある。"""
        if not tutor_schema_path.exists():
            pytest.skip("db/schema.sql が未作成のためスキップ")
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, tutor_schema_path)
        cur = conn.execute(
            "SELECT name FROM pragma_table_info('sessions') ORDER BY cid"
        )
        columns = [row[0] for row in cur.fetchall()]
        conn.close()
        assert "id" in columns
        assert "created_at" in columns
        assert "participant_id" in columns


class TestSessionsHasLearningSessionId:
    """対話用スキーマの sessions に learning_session_id があること。"""

    def test_sessions_has_learning_session_id_column(
        self, tutor_schema_path: Path
    ) -> None:
        """sessions に learning_session_id カラムが定義されている。"""
        if not tutor_schema_path.exists():
            pytest.skip("db/schema.sql が未作成のためスキップ")
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, tutor_schema_path)
        cur = conn.execute(
            "SELECT name, type, [notnull] FROM pragma_table_info('sessions') ORDER BY cid"
        )
        rows = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
        conn.close()
        assert "learning_session_id" in rows, (
            "sessions に learning_session_id カラムがあること"
        )
        col_type, notnull = rows["learning_session_id"]
        assert notnull == 1, "learning_session_id は NOT NULL であること"
        assert col_type.upper() == "TEXT", "learning_session_id は TEXT 型であること"
