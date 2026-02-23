"""
アプリ Step 5: 統合（同一 session で 2 回 /chat）

同一 session_id で 2 回 POST /chat し、2 回目の応答生成時に
1 回目のやり取りがプロンプトに含まれていることを検証する。
Step 3 と Step 4 の組み合わせの E2E。
"""
from unittest.mock import patch

import pytest


class TestAppStep5Integration:
    """同一セッションで 2 回チャットすると文脈が引き継がれる。"""

    def test_two_chats_in_same_session_persist_and_second_sees_first(
        self, app_client
    ) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        # 1 回目
        with patch("app.main._call_llm") as mock_llm:
            mock_llm.return_value = "1回目の応答"
            r1 = app_client.post(
                "/chat",
                json={"message": "1回目"},
                content_type="application/json",
            )
            assert r1.status_code == 200
            data1 = r1.get_json()
            assert data1 is not None and "session_id" in data1
            sid = data1["session_id"]
        # 2 回目: プロンプトに 1 回目が含まれることを確認
        captured = []
        with patch("app.main._call_llm") as mock_llm:
            mock_llm.side_effect = lambda p: (captured.append(p) or "2回目の応答")
            r2 = app_client.post(
                "/chat",
                json={"message": "2回目", "session_id": sid},
                content_type="application/json",
            )
            assert r2.status_code == 200
        assert len(captured) >= 1
        prompt = captured[-1]
        assert "1回目" in prompt and "1回目の応答" in prompt, (
            "2 回目のプロンプトに 1 回目のやり取りが含まれること"
        )
        # 履歴が 4 件（user, assistant, user, assistant）になっていること
        from db import repository

        history = repository.get_history(sid, limit=10)
        assert len(history) == 4
        assert [h["role"] for h in history] == ["user", "assistant", "user", "assistant"]
