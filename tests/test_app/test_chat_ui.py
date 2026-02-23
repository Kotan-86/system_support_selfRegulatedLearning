"""
チャット UI の構造テスト（Agent の実装迷走防止）。

プラン「チャットUI設計（吹き出し・ローディング）」セクション 6 に基づく。
GET / の HTML に必須要素・吹き出しクラス・ローディング・session_id が含まれること、
および app/static/css/style.css の存在とキーセレクタを検証する。
"""
from pathlib import Path

import pytest


class TestChatUiHtmlStructure:
    """GET / の HTML にチャット UI の必須要素が含まれる。"""

    def test_root_returns_html_with_chat_box(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get("/")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "chat-box" in html, "チャットエリア（id=chat-box または class に chat-box）が含まれること"

    def test_root_has_message_form_and_input(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get("/")
        html = r.get_data(as_text=True)
        assert "message-form" in html, "フォーム（id=message-form）が含まれること"
        assert "message-input" in html, "入力欄（id=message-input）が含まれること"
        assert "submit" in html or "送信" in html, "送信ボタンが含まれること"

    def test_root_has_post_to_chat(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get("/")
        html = r.get_data(as_text=True)
        assert "/chat" in html, "POST 先 /chat の記述が含まれること（fetch 等）"

    def test_root_has_user_message_class(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get("/")
        html = r.get_data(as_text=True)
        assert "user-message" in html, "学習者吹き出し用クラス user-message が含まれること"

    def test_root_has_tutor_message_class(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get("/")
        html = r.get_data(as_text=True)
        assert "tutor-message" in html, "tutor 吹き出し用クラス tutor-message が含まれること"

    def test_root_has_loading_indicator(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get("/")
        html = r.get_data(as_text=True)
        has_loading = (
            "loading-indicator" in html
            or "loading" in html
            or "spinner" in html
        )
        assert has_loading, (
            "ローディング用の class/id（loading-indicator, loading, spinner のいずれか）が含まれること"
        )

    def test_root_has_session_id_in_script(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get("/")
        html = r.get_data(as_text=True)
        has_session = "session_id" in html or "sessionId" in html
        assert has_session, (
            "2 通目以降で session_id を送る記述（session_id または sessionId）が script 内に含まれること"
        )


class TestChatUiCss:
    """app/static/css/style.css が存在し、キーセレクタが定義されている。"""

    def test_style_css_exists(self, project_root: Path) -> None:
        css_path = project_root / "app" / "static" / "css" / "style.css"
        assert css_path.exists(), "app/static/css/style.css が存在すること"

    def test_style_css_has_tutor_message_selector(self, project_root: Path) -> None:
        css_path = project_root / "app" / "static" / "css" / "style.css"
        if not css_path.exists():
            pytest.skip("style.css が未作成のためスキップ")
        content = css_path.read_text(encoding="utf-8")
        has_tutor = ".tutor-message" in content or ".bubble-tutor" in content
        assert has_tutor, "tutor 吹き出し用のセレクタ（.tutor-message または .bubble-tutor）が含まれること"

    def test_style_css_has_user_message_selector(self, project_root: Path) -> None:
        css_path = project_root / "app" / "static" / "css" / "style.css"
        if not css_path.exists():
            pytest.skip("style.css が未作成のためスキップ")
        content = css_path.read_text(encoding="utf-8")
        has_user = ".user-message" in content or ".bubble-user" in content
        assert has_user, "学習者吹き出し用のセレクタ（.user-message または .bubble-user）が含まれること"

    def test_style_css_has_spinner_animation(self, project_root: Path) -> None:
        css_path = project_root / "app" / "static" / "css" / "style.css"
        if not css_path.exists():
            pytest.skip("style.css が未作成のためスキップ")
        content = css_path.read_text(encoding="utf-8")
        assert "@keyframes" in content, "スピナー用の @keyframes が含まれること"
        has_spinner_class = (
            "loading-indicator" in content or "spinner" in content or "loading" in content
        )
        assert has_spinner_class, (
            "ローディング/スピナー用の class 名（loading-indicator, spinner, loading のいずれか）が含まれること"
        )
