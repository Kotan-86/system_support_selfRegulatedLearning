"""
Step 5: 動作確認（DB 構築の完了判定）

初期化 → セッション作成 → メッセージ 2 件追加（user, assistant）
→ 履歴取得で 2 件返ることを統合で検証する。
"""
import pytest


class TestStep5Integration:
    """DB 構築の一連の流れが正しく動作する。"""

    def test_full_flow_init_create_session_add_two_messages_get_history(
        self, env_tutor_db_path, tmp_path
    ) -> None:
        """init_db → create_session → add_message(user) → add_message(assistant) → get_history で 2 件返る。"""
        db_path = tmp_path / "tutor.db"
        env_tutor_db_path.setenv("TUTOR_DB_PATH", str(db_path))

        try:
            from db import init_db
            from db import repository
        except ImportError:
            pytest.skip("db.init_db または db.repository が未実装のためスキップ")

        init_db.init_db()
        sid = repository.create_session()
        repository.add_message(sid, "user", "小テストの問5がわかりません")
        repository.add_message(
            sid, "assistant", "問5についてですね。どの部分が難しかったか教えてもらえますか？"
        )

        history = repository.get_history(sid, limit=10)
        assert len(history) == 2, "履歴が 2 件返ること"
        assert history[0]["role"] == "user" and "問5" in history[0]["content"]
        assert history[1]["role"] == "assistant"
