"""
Step 1: スキーマ定義をバージョン管理する

db/schema.sql が存在し、実行すると sessions / messages テーブルと
必要なカラム・インデックスが作成されることを検証する。
"""
import sqlite3
from pathlib import Path

import pytest


class TestStep1SchemaFileExists:
    """db/schema.sql が存在する。"""

    def test_schema_file_exists(self, db_schema_path: Path) -> None:
        assert db_schema_path.exists(), "db/schema.sql が存在すること"
        assert db_schema_path.is_file()
        assert db_schema_path.suffix == ".sql"


class TestStep1SchemaCreatesTables:
    """schema.sql を実行すると sessions と messages テーブルが作成される。"""

    def _execute_schema(self, conn: sqlite3.Connection, schema_path: Path) -> None:
        sql = schema_path.read_text(encoding="utf-8")
        conn.executescript(sql)

    def test_sessions_table_exists_with_columns(
        self, db_schema_path: Path
    ) -> None:
        conn = sqlite3.connect(":memory:")
        self._execute_schema(conn, db_schema_path)
        cur = conn.execute(
            "SELECT name FROM pragma_table_info('sessions') ORDER BY cid"
        )
        columns = [row[0] for row in cur.fetchall()]
        conn.close()
        assert "id" in columns, "sessions に id カラムがあること"
        assert "created_at" in columns, "sessions に created_at カラムがあること"

    def test_messages_table_exists_with_columns(
        self, db_schema_path: Path
    ) -> None:
        conn = sqlite3.connect(":memory:")
        self._execute_schema(conn, db_schema_path)
        cur = conn.execute(
            "SELECT name FROM pragma_table_info('messages') ORDER BY cid"
        )
        columns = [row[0] for row in cur.fetchall()]
        conn.close()
        assert "id" in columns, "messages に id カラムがあること"
        assert "session_id" in columns, "messages に session_id カラムがあること"
        assert "role" in columns, "messages に role カラムがあること"
        assert "content" in columns, "messages に content カラムがあること"
        assert "created_at" in columns, "messages に created_at カラムがあること"

    def test_messages_has_index_for_session_or_session_and_created_at(
        self, db_schema_path: Path
    ) -> None:
        """messages に session_id または (session_id, created_at) のインデックスがある（履歴取得用）。"""
        conn = sqlite3.connect(":memory:")
        self._execute_schema(conn, db_schema_path)
        cur = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='messages'"
        )
        indexes = [(row[0], (row[1] or "").upper()) for row in cur.fetchall()]
        conn.close()
        # session_id を含むインデックスが少なくとも1つあること
        has_session_index = any(
            "SESSION_ID" in sql for _name, sql in indexes
        )
        assert has_session_index, (
            "messages に session_id を含むインデックスがあること "
            "(session_id 単独または session_id, created_at の複合)"
        )
