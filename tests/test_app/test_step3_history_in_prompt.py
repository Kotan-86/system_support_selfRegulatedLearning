"""
アプリ Step 3: プロンプトへの履歴組み込み

POST /chat で、その session_id の過去のやり取り（get_history）が
プロンプトに含まれて LLM に渡されることを検証する。LLM はモックし、
渡されたプロンプトに履歴の内容が含まれることを assert する。

実装側では LLM 呼び出しを _call_llm(prompt) -> str のようにまとめると
このテストの patch 対象（app.main._call_llm）でモックしやすい。
"""
from unittest.mock import patch

import pytest


class TestAppStep3HistoryInPrompt:
    """履歴がプロンプトに含まれる。"""

    def test_second_message_prompt_includes_first_exchange(
        self, app_client
    ) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        # 1 回目: 「りんご」と送り、モックで「りんごですね」と返す
        with patch("app.main._call_llm") as mock_llm:
            mock_llm.return_value = "りんごですね。"
            r1 = app_client.post(
                "/chat",
                json={"message": "りんご"},
                content_type="application/json",
            )
            assert r1.status_code == 200
            data1 = r1.get_json()
            assert data1 is not None and "session_id" in data1
            sid = data1["session_id"]
        # 2 回目: 同じ session_id で「みかん」と送る。渡されたプロンプトを捕捉
        captured_prompts = []
        with patch("app.main._call_llm") as mock_llm:
            def capture_and_return(prompt):
                captured_prompts.append(prompt)
                return "みかんですね。"
            mock_llm.side_effect = capture_and_return
            r2 = app_client.post(
                "/chat",
                json={"message": "みかん", "session_id": sid},
                content_type="application/json",
            )
            assert r2.status_code == 200
        assert len(captured_prompts) >= 1, "LLM が 1 回以上呼ばれること"
        last_prompt = captured_prompts[-1]
        assert "りんご" in last_prompt, "プロンプトに 1 回目のユーザー発言（りんご）が含まれること"
        assert "りんごですね" in last_prompt or "assistant" in last_prompt.lower(), (
            "プロンプトに 1 回目の応答または履歴が含まれること"
        )
