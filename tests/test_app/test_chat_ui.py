"""
チャット UI の構造テスト（Agent の実装迷走防止）。

Phase 6 以降、チャット UI は GET /reflect?participant_id= に統合される。
GET /reflect の HTML に必須要素・吹き出しクラス・ローディング・session_id が含まれること、
および reflect.css / style.css の存在とキーセレクタを検証する。
"""
from pathlib import Path

import pytest

REFLECT_URL = "/reflect?participant_id=1"


def _chat_panel_js(project_root: Path) -> str:
    js_path = (
        project_root
        / "framework_drivers"
        / "platform"
        / "static"
        / "js"
        / "reflect"
        / "chat_panel.js"
    )
    return js_path.read_text(encoding="utf-8")


class TestChatUiHtmlStructure:
    """GET /reflect の HTML にチャット UI の必須要素が含まれる。"""

    def test_reflect_returns_html_with_chat_box(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get(REFLECT_URL)
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "chat-box" in html, "チャットエリア（id=chat-box）が含まれること"

    def test_reflect_has_message_form_and_input(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get(REFLECT_URL)
        html = r.get_data(as_text=True)
        assert "message-form" in html, "フォーム（id=message-form）が含まれること"
        assert "message-input" in html, "入力欄（id=message-input）が含まれること"
        assert "submit" in html or "送信" in html, "送信ボタンが含まれること"

    def test_reflect_has_post_to_chat(self, app_client) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get(REFLECT_URL)
        html = r.get_data(as_text=True)
        assert "/chat" in html or "postChat" in html, (
            "POST 先 /chat の記述が含まれること（fetch 等）"
        )

    def test_reflect_has_user_message_class(self, app_client, project_root: Path) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get(REFLECT_URL)
        html = r.get_data(as_text=True)
        js = _chat_panel_js(project_root)
        assert "user-message" in html or "user-message" in js, (
            "学習者吹き出し用クラス user-message が HTML または chat_panel.js に含まれること"
        )

    def test_reflect_has_tutor_message_class(self, app_client, project_root: Path) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get(REFLECT_URL)
        html = r.get_data(as_text=True)
        js = _chat_panel_js(project_root)
        assert "tutor-message" in html or "tutor-message" in js, (
            "tutor 吹き出し用クラス tutor-message が HTML または chat_panel.js に含まれること"
        )

    def test_reflect_has_loading_indicator(self, app_client, project_root: Path) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get(REFLECT_URL)
        html = r.get_data(as_text=True)
        js = _chat_panel_js(project_root)
        combined = html + js
        has_loading = (
            "loading-indicator" in combined
            or "loading" in combined
            or "spinner" in combined
        )
        assert has_loading, (
            "ローディング用の class/id（loading-indicator, loading, spinner のいずれか）が含まれること"
        )

    def test_reflect_has_session_id_in_script(self, app_client, project_root: Path) -> None:
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get(REFLECT_URL)
        html = r.get_data(as_text=True)
        js = _chat_panel_js(project_root)
        combined = html + js
        has_session = "session_id" in combined or "sessionId" in combined
        assert has_session, (
            "2 通目以降で session_id を送る記述（session_id または sessionId）が含まれること"
        )

    def test_reflect_has_no_learner_id_prompt(self, app_client) -> None:
        """Phase 6: participant_id は URL から取得し、初回 ID 入力プロンプトは表示しない。"""
        if app_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = app_client.get(REFLECT_URL)
        html = r.get_data(as_text=True)
        assert "学習者IDを教えてください" not in html
        assert "半角数字" not in html


class TestChatUiCss:
    """reflect.css / style.css が存在し、キーセレクタが定義されている。"""

    def test_reflect_css_exists(self, project_root: Path) -> None:
        css_path = (
            project_root
            / "framework_drivers"
            / "platform"
            / "static"
            / "css"
            / "reflect.css"
        )
        assert css_path.exists(), "framework_drivers/platform/static/css/reflect.css が存在すること"

    def test_reflect_css_has_tutor_message_selector(self, project_root: Path) -> None:
        css_path = (
            project_root
            / "framework_drivers"
            / "platform"
            / "static"
            / "css"
            / "reflect.css"
        )
        if not css_path.exists():
            pytest.skip("reflect.css が未作成のためスキップ")
        content = css_path.read_text(encoding="utf-8")
        has_tutor = ".tutor-message" in content or ".bubble-tutor" in content
        assert has_tutor, "tutor 吹き出し用のセレクタ（.tutor-message または .bubble-tutor）が含まれること"

    def test_reflect_css_has_user_message_selector(self, project_root: Path) -> None:
        css_path = (
            project_root
            / "framework_drivers"
            / "platform"
            / "static"
            / "css"
            / "reflect.css"
        )
        if not css_path.exists():
            pytest.skip("reflect.css が未作成のためスキップ")
        content = css_path.read_text(encoding="utf-8")
        has_user = ".user-message" in content or ".bubble-user" in content
        assert has_user, "学習者吹き出し用のセレクタ（.user-message または .bubble-user）が含まれること"

    def test_reflect_css_has_spinner_animation(self, project_root: Path) -> None:
        css_path = (
            project_root
            / "framework_drivers"
            / "platform"
            / "static"
            / "css"
            / "reflect.css"
        )
        if not css_path.exists():
            pytest.skip("reflect.css が未作成のためスキップ")
        content = css_path.read_text(encoding="utf-8")
        assert "@keyframes" in content, "スピナー用の @keyframes が含まれること"
        has_spinner_class = (
            "loading-indicator" in content or "spinner" in content or "loading" in content
        )
        assert has_spinner_class, (
            "ローディング/スピナー用の class 名（loading-indicator, spinner, loading のいずれか）が含まれること"
        )

    def test_style_css_exists(self, project_root: Path) -> None:
        css_path = project_root / "app" / "static" / "css" / "style.css"
        platform_css = (
            project_root
            / "framework_drivers"
            / "platform"
            / "static"
            / "css"
            / "style.css"
        )
        assert css_path.exists() or platform_css.exists(), (
            "style.css が app/static または platform/static に存在すること"
        )
