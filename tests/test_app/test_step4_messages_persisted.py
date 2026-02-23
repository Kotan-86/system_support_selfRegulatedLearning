"""
アプリ Step 4: メッセージの永続化

POST /chat のあと、repository.get_history(session_id) で
ユーザー発言と LLM 応答の 2 件が保存されていることを検証する。
LLM はモックして応答を固定し、内容を assert する。
"""
from unittest.mock import patch

import pytest


class TestAppStep4MessagesPersisted:
    """/chat の送受信が messages に保存される。"""

    def test_after_post_chat_history_contains_user_and_assistant(
        self, app_client
    ) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        with patch("app.main._call_llm") as mock_llm:
            mock_llm.return_value = "テスト用の応答です。"
            r = app_client.post(
                "/chat",
                json={"message": "永続化テスト"},
                content_type="application/json",
            )
            assert r.status_code == 200
            data = r.get_json()
            assert data is not None and "session_id" in data
            sid = data["session_id"]
        # DB から履歴を取得（app と同じ TUTOR_DB_PATH が conftest で設定されている）
        from db import repository

        history = repository.get_history(sid, limit=10)
        assert len(history) >= 2, "履歴に少なくとも user と assistant の 2 件があること"
        roles = [h["role"] for h in history]
        assert "user" in roles and "assistant" in roles
        contents = [h["content"] for h in history]
        assert "永続化テスト" in contents, "ユーザー発言が保存されていること"
        assert "テスト用の応答です。" in contents, "LLM 応答が保存されていること"
