"""
アプリ Step 4: メッセージの永続化

POST /chat のあと、TutorSession にユーザー発言と LLM 応答の 2 件が
保存されていることを検証する。LLM は Fake で応答を固定し、内容を assert する。
"""
import os

import pytest

from domain.shared.ids import TutorSessionId
from framework_drivers.db.tutoring.sqlite_connection import connect_tutor_db
from framework_drivers.db.tutoring.sqlite_tutor_session_repository import (
    SqliteTutorSessionRepository,
)


def _load_messages(session_id: str) -> list[tuple[str, str]]:
    conn = connect_tutor_db(os.environ["TUTOR_DB_PATH"])
    try:
        repo = SqliteTutorSessionRepository(conn)
        session = repo.find_by_id(TutorSessionId(session_id))
        assert session is not None
        return [(message.role.value, message.content) for message in session.messages]
    finally:
        conn.close()


class TestAppStep4MessagesPersisted:
    """/chat の送受信が messages に保存される。"""

    def test_after_post_chat_history_contains_user_and_assistant(
        self, app_client, fake_llm_gateway
    ) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        fake_llm_gateway.set_response("テスト用の応答です。")
        r = app_client.post(
            "/chat",
            json={"message": "永続化テスト", "participant_id": "1"},
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data is not None and "session_id" in data
        sid = data["session_id"]

        messages = _load_messages(sid)
        assert len(messages) >= 2, "履歴に少なくとも user と assistant の 2 件があること"
        roles = [role for role, _content in messages]
        contents = [content for _role, content in messages]
        assert "user" in roles and "assistant" in roles
        assert "永続化テスト" in contents, "ユーザー発言が保存されていること"
        assert "テスト用の応答です。" in contents, "LLM 応答が保存されていること"
