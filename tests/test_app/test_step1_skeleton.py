"""
アプリ Step 1: 骨組み

app.main に Flask アプリがあり、GET / と POST /chat が動作することを検証する。
LAD 未使用・履歴は空のままでよい。
"""
from unittest.mock import patch

import pytest


class TestAppStep1ModuleExists:
    """app.main が Flask アプリを提供する。"""

    def test_app_main_has_flask_app(self) -> None:
        try:
            from app.main import app
        except ImportError:
            pytest.skip("app.main が未実装のためスキップ")
        from flask import Flask

        assert isinstance(app, Flask), "app.main は Flask インスタンスを公開すること"


class TestAppStep1GetRoot:
    """GET / が 200 を返す。"""

    def test_get_root_returns_200(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get("/")
        assert r.status_code == 200, "GET / は 200 を返すこと"


class TestAppStep1PostChat:
    """POST /chat が message を受け取り JSON を返す。"""

    def test_post_chat_requires_message(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.post("/chat", json={}, content_type="application/json")
        assert r.status_code in (400, 422), "message がないときは 4xx を返すこと"

    def test_post_chat_with_message_returns_json(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        with patch("app.main._call_llm") as mock_llm:
            mock_llm.return_value = "スタブ応答"
            r = app_client.post(
                "/chat",
                json={"message": "こんにちは"},
                content_type="application/json",
            )
        assert r.status_code == 200, "message があるときは 200 を返すこと"
        data = r.get_json()
        assert data is not None, "レスポンスは JSON であること"
        assert "response" in data or "error" in data, (
            "レスポンスに response または error キーがあること"
        )
