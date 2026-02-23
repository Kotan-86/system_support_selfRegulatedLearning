"""
Step 4: 永続化レイヤー（CRUD）の用意

db.repository が提供する操作を検証する:
- デフォルト DB パス（TUTOR_DB_PATH 未設定時は db/data/tutor.db）
- セッション作成 → 発行した id を返す
- メッセージ追加（session_id, role, content）
- 履歴取得（session_id, 直近 N 件を created_at 昇順）
"""
from pathlib import Path

import pytest


@pytest.fixture
def initialized_db(env_tutor_db_path, tmp_path: Path):
    """一時パスに DB を用意し、init_db で初期化する。"""
    db_path = tmp_path / "tutor.db"
    env_tutor_db_path.setenv("TUTOR_DB_PATH", str(db_path))
    try:
        from db import init_db

        init_db.init_db()
    except ImportError:
        pytest.skip("db.init_db が未実装のためスキップ")
    return db_path


class TestStep4GetDbPath:
    """get_db_path() は TUTOR_DB_PATH またはデフォルトパスを返す。"""

    def test_get_db_path_returns_default_when_env_unset(
        self, env_tutor_db_path, default_db_path: Path
    ) -> None:
        """TUTOR_DB_PATH が未設定のとき、デフォルトは db/data/tutor.db。"""
        env_tutor_db_path.delenv("TUTOR_DB_PATH", raising=False)
        try:
            from db import repository

            path = repository.get_db_path()
        except ImportError:
            pytest.skip("db.repository が未実装のためスキップ")
        assert path is not None
        path_resolved = Path(path).resolve()
        default_resolved = default_db_path.resolve()
        assert path_resolved == default_resolved, (
            "デフォルトは db/data/tutor.db であること"
        )

    def test_get_db_path_returns_env_value_when_set(
        self, env_tutor_db_path, tmp_path: Path
    ) -> None:
        """TUTOR_DB_PATH が設定されているとき、そのパスを返す。"""
        custom = tmp_path / "custom.db"
        env_tutor_db_path.setenv("TUTOR_DB_PATH", str(custom))
        try:
            from db import repository

            path = repository.get_db_path()
        except ImportError:
            pytest.skip("db.repository が未実装のためスキップ")
        assert path == custom or str(path) == str(custom)


class TestStep4CreateSession:
    """create_session() はセッションを挿入し、id を返す。"""

    def test_create_session_returns_id(self, initialized_db) -> None:
        try:
            from db import repository

            sid = repository.create_session()
        except ImportError:
            pytest.skip("db.repository が未実装のためスキップ")
        assert sid is not None, "create_session() は id を返すこと"
        assert isinstance(sid, (str, int)), "id は str または int"

    def test_create_session_persists_row(self, initialized_db) -> None:
        import sqlite3

        try:
            from db import repository

            sid = repository.create_session()
            path = repository.get_db_path()
        except ImportError:
            pytest.skip("db.repository が未実装のためスキップ")
        conn = sqlite3.connect(str(path))
        cur = conn.execute("SELECT id, created_at FROM sessions WHERE id = ?", (sid,))
        row = cur.fetchone()
        conn.close()
        assert row is not None, "sessions に 1 行挿入されていること"


class TestStep4AddMessage:
    """add_message(session_id, role, content) でメッセージが永続化される。"""

    def test_add_message_persists_user_and_assistant(
        self, initialized_db
    ) -> None:
        try:
            from db import repository

            sid = repository.create_session()
            repository.add_message(sid, "user", "こんにちは")
            repository.add_message(sid, "assistant", "こんにちは。何かお手伝いしましょうか。")
        except ImportError:
            pytest.skip("db.repository が未実装のためスキップ")
        # 永続化されていることは get_history で確認する
        history = repository.get_history(sid, limit=10)
        assert len(history) >= 2
        roles = [h["role"] for h in history]
        assert "user" in roles and "assistant" in roles


class TestStep4GetHistory:
    """get_history(session_id, limit=N) は created_at 昇順で直近 N 件を返す。"""

    def test_get_history_returns_messages_in_order(
        self, initialized_db
    ) -> None:
        try:
            from db import repository

            sid = repository.create_session()
            repository.add_message(sid, "user", "1")
            repository.add_message(sid, "assistant", "2")
            repository.add_message(sid, "user", "3")
        except ImportError:
            pytest.skip("db.repository が未実装のためスキップ")
        history = repository.get_history(sid, limit=10)
        assert len(history) == 3
        # created_at 昇順 = 古い順
        assert history[0]["content"] == "1" and history[0]["role"] == "user"
        assert history[1]["content"] == "2" and history[1]["role"] == "assistant"
        assert history[2]["content"] == "3" and history[2]["role"] == "user"

    def test_get_history_respects_limit(self, initialized_db) -> None:
        try:
            from db import repository

            sid = repository.create_session()
            for i in range(5):
                repository.add_message(sid, "user", str(i))
                repository.add_message(sid, "assistant", str(i))
        except ImportError:
            pytest.skip("db.repository が未実装のためスキップ")
        # 直近 3 件 = 最後の 3 件（昇順なので [6,7,8] 番目＝0-indexed で 6,7,8 番目）
        history = repository.get_history(sid, limit=3)
        assert len(history) == 3, "limit=3 のとき最大 3 件返すこと"

    def test_get_history_each_item_has_role_and_content(
        self, initialized_db
    ) -> None:
        try:
            from db import repository

            sid = repository.create_session()
            repository.add_message(sid, "user", "テスト")
        except ImportError:
            pytest.skip("db.repository が未実装のためスキップ")
        history = repository.get_history(sid, limit=10)
        assert len(history) >= 1
        for row in history:
            assert "role" in row and "content" in row, (
                "各要素に role と content があること"
            )
