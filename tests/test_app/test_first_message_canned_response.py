"""
初回メッセージが半角数字のみ（学習者ID）のとき、定型文を返し LLM を呼ばないことを検証する。
"""
import pytest

from application.tutoring.use_cases.send_chat_message import FIRST_MESSAGE_CANNED_RESPONSE


class TestFirstMessageCannedResponse:
    """初回・半角数字のみのとき定型文が返り LLM が呼ばれない。"""

    def test_first_message_digits_only_returns_canned_response(self, app_client) -> None:
        """初回メッセージが半角数字のみのとき 200 かつ response が定型文と完全一致する。"""
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")

        r = app_client.post(
            "/chat",
            json={"message": "1", "participant_id": "1"},
            content_type="application/json",
        )
        assert r.status_code == 200, "初回・数字のみのときは 200 を返すこと"
        data = r.get_json()
        assert data is not None and data.get("response") == FIRST_MESSAGE_CANNED_RESPONSE, (
            "response が定型文と完全一致すること"
        )
        assert "session_id" in data and isinstance(data["session_id"], str)

    def test_first_message_digits_only_does_not_call_llm(
        self, app_client, fake_llm_gateway
    ) -> None:
        """初回メッセージが半角数字のみのとき LLM が 1 回も呼ばれない。"""
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        fake_llm_gateway.generate_calls.clear()
        app_client.post(
            "/chat",
            json={"message": "1", "participant_id": "1"},
            content_type="application/json",
        )
        assert fake_llm_gateway.generate_calls == []

    def test_first_message_non_digits_calls_llm(
        self, app_client, fake_llm_gateway
    ) -> None:
        """初回でもメッセージが半角数字以外のときは LLM が呼ばれる。"""
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        fake_llm_gateway.generate_calls.clear()
        app_client.post(
            "/chat",
            json={"message": "こんにちは", "participant_id": "1"},
            content_type="application/json",
        )
        assert len(fake_llm_gateway.generate_calls) == 1

    def test_second_message_digits_calls_llm(
        self, app_client, fake_llm_gateway
    ) -> None:
        """同一セッションで 1 通目が「1」で定型文、2 通目が「2」のときは LLM が呼ばれる。"""
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r1 = app_client.post(
            "/chat",
            json={"message": "1", "participant_id": "1"},
            content_type="application/json",
        )
        assert r1.status_code == 200
        data1 = r1.get_json()
        assert data1 is not None and "session_id" in data1
        sid = data1["session_id"]

        fake_llm_gateway.generate_calls.clear()
        app_client.post(
            "/chat",
            json={"message": "2", "session_id": sid, "participant_id": "1"},
            content_type="application/json",
        )
        assert len(fake_llm_gateway.generate_calls) == 1
