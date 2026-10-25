# 仕様: docs/spec/participant-login.md#3-参加者の特定fr-52 (AC12, AC14)
"""
POST /chat の participant_id(ログイン導入後)。

旧: session_id も participant_id も無いと 400。
新: participant_id は省略可。省略するとログインした本人として処理する(AC14)。
本人と異なる participant_id は 403(AC12)。
"""
from tests.login_helpers import login_as


class TestPostChatParticipantId:
    """participant_id は省略可。省略時はログインした本人。"""

    def test_post_chat_without_participant_id_uses_logged_in_participant(
        self, chat_lad_client
    ) -> None:
        """AC14: session_id も participant_id も送らなくても、ログインした本人で 200 と session_id が返る。(旧: 400)"""
        r = chat_lad_client.post(
            "/chat",
            json={"message": "こんにちは"},
            content_type="application/json",
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        data = r.get_json()
        assert data is not None
        assert isinstance(data["session_id"], str) and len(data["session_id"]) > 0

    def test_post_chat_with_own_participant_id_returns_200_and_session_id(
        self, chat_lad_client
    ) -> None:
        """session_id を送らず本人の participant_id を送ると 200 と session_id が返る。"""
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

    def test_post_chat_with_other_participant_id_returns_403(
        self, chat_lad_client
    ) -> None:
        """AC12: 本人と異なる participant_id は 403。"""
        login_as(chat_lad_client, "A")
        r = chat_lad_client.post(
            "/chat",
            json={"message": "はじめて", "participant_id": "B"},
            content_type="application/json",
        )
        assert r.status_code == 403
