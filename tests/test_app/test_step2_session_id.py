"""
アプリ Step 2: session_id の扱い

POST /chat で session_id が無いときは新規作成してレスポンスに含めること、
session_id を送ったときはそのセッションを使うことを検証する。
"""
import pytest


class TestAppStep2SessionIdCreation:
    """session_id がないとき新規作成し、レスポンスに含める。"""

    def test_post_chat_without_session_id_returns_session_id(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.post(
            "/chat",
            json={"message": "はじめてのメッセージ", "participant_id": "1"},
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data is not None
        assert "session_id" in data, "session_id がないリクエストでもレスポンスに session_id を含めること"
        assert isinstance(data["session_id"], str) and len(data["session_id"]) > 0


class TestAppStep2SessionIdReuse:
    """同じ session_id を送るとそのセッションが使われる。"""

    def test_post_chat_with_session_id_returns_same_session_id(
        self, app_client
    ) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r1 = app_client.post(
            "/chat",
            json={"message": "1回目", "participant_id": "1"},
            content_type="application/json",
        )
        assert r1.status_code == 200
        data1 = r1.get_json()
        assert data1 is not None and "session_id" in data1
        sid = data1["session_id"]
        r2 = app_client.post(
            "/chat",
            json={"message": "2回目", "session_id": sid, "participant_id": "1"},
            content_type="application/json",
        )
        assert r2.status_code == 200
        data2 = r2.get_json()
        assert data2 is not None
        assert data2.get("session_id") == sid, (
            "同じ session_id を送ったとき、レスポンスの session_id は同じであること"
        )
