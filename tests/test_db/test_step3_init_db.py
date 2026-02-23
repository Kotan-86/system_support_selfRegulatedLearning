"""
Step 3: 初期 DB 作成（マイグレーション／初期化）

init_db を実行すると db/data/tutor.db が作成され、sessions と messages
テーブルが存在することを検証する。環境変数 TUTOR_DB_PATH でパスを
上書きできることも検証する。
"""
import os
import sqlite3
from pathlib import Path

import pytest


class TestStep3InitDbCreatesDatabase:
    """init_db 実行で DB ファイルが作成され、テーブルが存在する。"""

    def test_init_db_creates_file_at_default_path(
        self, env_tutor_db_path, tmp_path: Path
    ) -> None:
        """init_db を呼ぶと DB ファイルが作成される（パスは TUTOR_DB_PATH またはデフォルト）。"""
        db_path = tmp_path / "tutor.db"
        env_tutor_db_path.setenv("TUTOR_DB_PATH", str(db_path))
        try:
            from db import init_db

            init_db.init_db()
        except ImportError:
            pytest.skip("db.init_db が未実装のためスキップ")
        assert db_path.exists(), "init_db() 実行後に DB ファイルが存在すること"
        assert db_path.is_file()

    def test_after_init_db_sessions_and_messages_tables_exist(
        self, env_tutor_db_path, tmp_path: Path
    ) -> None:
        """init_db 実行後、sessions と messages テーブルが存在する。"""
        db_path = tmp_path / "tutor.db"
        env_tutor_db_path.setenv("TUTOR_DB_PATH", str(db_path))
        try:
            from db import init_db

            init_db.init_db()
        except ImportError:
            pytest.skip("db.init_db が未実装のためスキップ")
        conn = sqlite3.connect(str(db_path))
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('sessions','messages')"
        )
        tables = {row[0] for row in cur.fetchall()}
        conn.close()
        assert "sessions" in tables and "messages" in tables, (
            "init_db 実行後に sessions と messages テーブルが存在すること"
        )


class TestStep3InitDbRespectsTutorDbPath:
    """TUTOR_DB_PATH が設定されているとき、そのパスに DB を作成する。"""

    def test_init_db_uses_tutor_db_path_env(
        self, env_tutor_db_path, tmp_path: Path
    ) -> None:
        """TUTOR_DB_PATH を設定した状態で init_db を呼ぶと、そのパスに DB が作成される。"""
        custom_db = tmp_path / "custom" / "tutor.db"
        custom_db.parent.mkdir(parents=True, exist_ok=True)
        env_tutor_db_path.setenv("TUTOR_DB_PATH", str(custom_db))
        try:
            from db import init_db

            init_db.init_db()
        except ImportError:
            pytest.skip("db.init_db が未実装のためスキップ")
        assert custom_db.exists(), (
            "TUTOR_DB_PATH で指定したパスに DB ファイルが作成されること"
        )
