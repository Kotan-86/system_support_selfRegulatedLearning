"""
初回メッセージが半角数字のみ（学習者ID）のとき、定型文を返し LLM を呼ばないことを検証する。
"""
from unittest.mock import patch

import pytest


class TestFirstMessageCannedResponse:
    """初回・半角数字のみのとき定型文が返り _call_llm が呼ばれない。"""

    def test_first_message_digits_only_returns_canned_response(self, app_client) -> None:
        """初回メッセージが半角数字のみのとき 200 かつ response が定型文と完全一致する。"""
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        from app.main import FIRST_MESSAGE_CANNED_RESPONSE

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

    def test_first_message_digits_only_does_not_call_llm(self, app_client) -> None:
        """初回メッセージが半角数字のみのとき _call_llm が 1 回も呼ばれない。"""
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        with patch("app.main._call_llm") as mock_llm:
            app_client.post(
                "/chat",
                json={"message": "1", "participant_id": "1"},
                content_type="application/json",
            )
        mock_llm.assert_not_called()

    def test_first_message_non_digits_calls_llm(self, app_client) -> None:
        """初回でもメッセージが半角数字以外のときは _call_llm が呼ばれる。"""
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        with patch("app.main._call_llm") as mock_llm:
            mock_llm.return_value = "スタブ応答"
            app_client.post(
                "/chat",
                json={"message": "こんにちは", "participant_id": "1"},
                content_type="application/json",
            )
        mock_llm.assert_called_once()

    def test_second_message_digits_calls_llm(self, app_client) -> None:
        """同一セッションで 1 通目が「1」で定型文、2 通目が「2」のときは _call_llm が呼ばれる。"""
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        with patch("app.main._call_llm") as mock_llm:
            mock_llm.return_value = "スタブ応答"
            r1 = app_client.post(
                "/chat",
                json={"message": "1", "participant_id": "1"},
                content_type="application/json",
            )
        assert r1.status_code == 200
        data1 = r1.get_json()
        assert data1 is not None and "session_id" in data1
        sid = data1["session_id"]

        with patch("app.main._call_llm") as mock_llm2:
            mock_llm2.return_value = "2通目スタブ"
            app_client.post(
                "/chat",
                json={"message": "2", "session_id": sid},
                content_type="application/json",
            )
        mock_llm2.assert_called_once()
