"""
アプリ Step 5: 統合（同一 session で 2 回 /chat）

同一 session_id で 2 回 POST /chat し、2 回目の応答生成時に
1 回目のやり取りがプロンプトに含まれていることを検証する。
Step 3 と Step 4 の組み合わせの E2E。
"""
import os

import pytest

from domain.shared.ids import TutorSessionId
from framework_drivers.db.tutoring.sqlite_connection import connect_tutor_db
from framework_drivers.db.tutoring.sqlite_tutor_session_repository import (
    SqliteTutorSessionRepository,
)


def _load_messages(session_id: str) -> list[str]:
    conn = connect_tutor_db(os.environ["TUTOR_DB_PATH"])
    try:
        repo = SqliteTutorSessionRepository(conn)
        session = repo.find_by_id(TutorSessionId(session_id))
        assert session is not None
        return [message.role.value for message in session.messages]
    finally:
        conn.close()


class TestAppStep5Integration:
    """同一セッションで 2 回チャットすると文脈が引き継がれる。"""

    def test_two_chats_in_same_session_persist_and_second_sees_first(
        self, app_client, fake_llm_gateway
    ) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        fake_llm_gateway.set_response("1回目の応答")
        r1 = app_client.post(
            "/chat",
            json={"message": "1回目", "participant_id": "1"},
            content_type="application/json",
        )
        assert r1.status_code == 200
        data1 = r1.get_json()
        assert data1 is not None and "session_id" in data1
        sid = data1["session_id"]

        fake_llm_gateway.generate_calls.clear()
        fake_llm_gateway.set_response("2回目の応答")
        r2 = app_client.post(
            "/chat",
            json={"message": "2回目", "session_id": sid, "participant_id": "1"},
            content_type="application/json",
        )
        assert r2.status_code == 200
        assert len(fake_llm_gateway.generate_calls) >= 1
        prompt = fake_llm_gateway.generate_calls[-1]
        assert "1回目" in prompt and "1回目の応答" in prompt, (
            "2 回目のプロンプトに 1 回目のやり取りが含まれること"
        )

        roles = _load_messages(sid)
        assert roles == ["user", "assistant", "user", "assistant"]
