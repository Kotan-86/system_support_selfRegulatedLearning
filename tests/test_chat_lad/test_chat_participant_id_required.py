"""
Phase 3 Step 3.1: POST /chat で新規セッション時に participant_id 必須

session_id を送らず participant_id も送らない場合 400、
participant_id を送った場合 200 と session_id が返ることを検証する。
"""
from unittest.mock import patch

import pytest


class TestPostChatParticipantIdRequired:
    """新規セッション時は participant_id が必須。"""

    def test_post_chat_without_session_id_and_without_participant_id_returns_400(
        self, chat_lad_client
    ) -> None:
        """session_id も participant_id も送らないと 400 が返る。"""
        if chat_lad_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = chat_lad_client.post(
            "/chat",
            json={"message": "こんにちは"},
            content_type="application/json",
        )
        assert r.status_code == 400, (
            "participant_id が無い新規チャット時は 400 を返すこと"
        )
        data = r.get_json()
        assert data is not None
        assert "error" in data or "participant" in str(data).lower()

    def test_post_chat_with_participant_id_returns_200_and_session_id(
        self, chat_lad_client
    ) -> None:
        """session_id を送らず participant_id を送ると 200 と session_id が返る。"""
        if chat_lad_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        with patch("app.main._call_llm") as mock_llm:
            mock_llm.return_value = "スタブ応答"
            r = chat_lad_client.post(
                "/chat",
                json={"message": "はじめて", "participant_id": "1"},
                content_type="application/json",
            )
        assert r.status_code == 200
        data = r.get_json()
        assert data is not None
        assert "session_id" in data
        assert isinstance(data["session_id"], str) and len(data["session_id"]) > 0
