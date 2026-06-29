"""
アプリ Step 3: プロンプトへの履歴組み込み

POST /chat で、その session_id の過去のやり取り（get_history）が
プロンプトに含まれて LLM に渡されることを検証する。LLM は Fake に差し替え、
渡されたプロンプトに履歴の内容が含まれることを assert する。
"""
import pytest


class TestAppStep3HistoryInPrompt:
    """履歴がプロンプトに含まれる。"""

    def test_second_message_prompt_includes_first_exchange(
        self, app_client, fake_llm_gateway
    ) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        fake_llm_gateway.set_response("りんごですね。")
        r1 = app_client.post(
            "/chat",
            json={"message": "りんご", "participant_id": "1"},
            content_type="application/json",
        )
        assert r1.status_code == 200
        data1 = r1.get_json()
        assert data1 is not None and "session_id" in data1
        sid = data1["session_id"]

        fake_llm_gateway.generate_calls.clear()
        fake_llm_gateway.set_response("みかんですね。")
        r2 = app_client.post(
            "/chat",
            json={"message": "みかん", "session_id": sid, "participant_id": "1"},
            content_type="application/json",
        )
        assert r2.status_code == 200
        assert len(fake_llm_gateway.generate_calls) >= 1, "LLM が 1 回以上呼ばれること"
        last_prompt = fake_llm_gateway.generate_calls[-1]
        assert "りんご" in last_prompt, "プロンプトに 1 回目のユーザー発言（りんご）が含まれること"
        assert "りんごですね" in last_prompt or "assistant" in last_prompt.lower(), (
            "プロンプトに 1 回目の応答または履歴が含まれること"
        )
