"""
実呼び出しテスト: Vertex AI を本当に呼び、対話が成立することを検証する。

このファイルでは _call_llm を patch しない。
認証が無い場合はスキップする（RUN_REAL_LLM_TESTS=1 または GOOGLE_APPLICATION_CREDENTIALS を参照）。
"""
import os

import pytest


def _should_skip_real_llm() -> bool:
    """実 LLM テストをスキップすべきなら True。"""
    if os.environ.get("RUN_REAL_LLM_TESTS") == "1":
        return False
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return False
    return True


@pytest.mark.real_llm
class TestRealChatOneTurn:
    """1 ターンで非空応答が返る（実 Vertex 呼び出し）。"""

    def test_chat_returns_non_empty_assistant_reply(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        if _should_skip_real_llm():
            pytest.skip(
                "実 LLM テストは RUN_REAL_LLM_TESTS=1 または GOOGLE_APPLICATION_CREDENTIALS を設定して実行"
            )

        r = app_client.post(
            "/chat",
            json={"message": "こんにちは。1+1は何ですか？"},
            content_type="application/json",
        )
        assert r.status_code == 200, f"200 であること (got {r.status_code}, body={r.get_data(as_text=True)})"
        data = r.get_json()
        assert data is not None
        assert "response" in data, "レスポンスに response が含まれること"
        reply = data["response"]
        assert isinstance(reply, str) and len(reply.strip()) > 0, (
            "assistant の応答が非空であること"
        )


@pytest.mark.real_llm
class TestRealChatTwoTurns:
    """2 ターンで文脈が保持されている（実 Vertex 呼び出し）。"""

    def test_two_turns_context_retained(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        if _should_skip_real_llm():
            pytest.skip(
                "実 LLM テストは RUN_REAL_LLM_TESTS=1 または GOOGLE_APPLICATION_CREDENTIALS を設定して実行"
            )

        # 1 回目: 「2+3は?」
        r1 = app_client.post(
            "/chat",
            json={"message": "2+3は?"},
            content_type="application/json",
        )
        assert r1.status_code == 200
        data1 = r1.get_json()
        assert data1 is not None and "session_id" in data1
        sid = data1["session_id"]

        # 2 回目: 「さっきの答えを数字だけ言って」
        r2 = app_client.post(
            "/chat",
            json={"message": "さっきの答えを数字だけ言って", "session_id": sid},
            content_type="application/json",
        )
        assert r2.status_code == 200
        data2 = r2.get_json()
        assert data2 is not None and "response" in data2
        second_reply = data2["response"]
        assert "5" in second_reply, (
            f"2 回目の応答に「5」が含まれること（履歴が効いていること）。got: {second_reply!r}"
        )
