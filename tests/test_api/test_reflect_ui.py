"""
Phase 6: GET /reflect LAD + Chat 統合 UI

/reflect の HTML 構造、/ からのリダイレクト、ログインした本人の画面を検証する。
"""
import pytest

from tests.login_helpers import displayed_participant_id, login_as

LAD_BLOCK_IDS = (
    "lad-block-action-counts",
    "lad-block-video-segments",
    "lad-block-quiz",
    "lad-block-profile",
)

REFLECT_SCRIPT_PATHS = (
    "js/reflect/lad_panel.js",
    "js/reflect/chat_panel.js",
    "js/reflect/reflect_app.js",
)


class TestReflectRoute:
    """GET /reflect のルーティングと HTML 構造。"""

    def test_root_redirects_to_lecture_when_logged_in(self, phase2_client) -> None:
        """AC24(participant-login): ログイン済みの / は /lecture へ 302。(旧: /reflect へ)"""
        # 仕様: docs/spec/participant-login.md#受入基準
        r = phase2_client.get("/")
        assert r.status_code == 302
        assert r.headers.get("Location", "").split("?")[0].endswith("/lecture")

    def test_root_ignores_participant_id_query(self, phase2_client) -> None:
        """AC13/24: / のクエリの participant_id は引き継がない(他人の ID を持ち越さない)。"""
        r = phase2_client.get("/?participant_id=42")
        assert r.status_code == 302
        location = r.headers.get("Location", "")
        assert location.split("?")[0].endswith("/lecture")
        assert "42" not in location

    def test_reflect_without_participant_id_shows_logged_in_participant(
        self, phase2_client
    ) -> None:
        """AC11: participant_id なしの /reflect は、ログインした本人の画面を 200 で返す。(旧: 400)"""
        login_as(phase2_client, "A")
        r = phase2_client.get("/reflect")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert displayed_participant_id(html) == "A"
        assert "lad-panel" in html
        assert "chat-panel" in html

    def test_reflect_with_participant_id_returns_200(self, phase2_client) -> None:
        r = phase2_client.get("/reflect")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "lad-panel" in html
        assert "chat-panel" in html

    def test_reflect_has_four_lad_blocks(self, phase2_client) -> None:
        r = phase2_client.get("/reflect")
        html = r.get_data(as_text=True)
        for block_id in LAD_BLOCK_IDS:
            assert block_id in html, f"LAD ブロック {block_id} が HTML に含まれること"

    def test_reflect_loads_echarts_cdn(self, phase2_client) -> None:
        r = phase2_client.get("/reflect")
        html = r.get_data(as_text=True)
        assert "echarts" in html

    def test_reflect_loads_reflect_scripts(self, phase2_client) -> None:
        r = phase2_client.get("/reflect")
        html = r.get_data(as_text=True)
        for script_path in REFLECT_SCRIPT_PATHS:
            assert script_path in html, f"スクリプト {script_path} が読み込まれること"

    def test_reflect_has_chart_containers(self, phase2_client) -> None:
        r = phase2_client.get("/reflect")
        html = r.get_data(as_text=True)
        assert "action-counts-chart" in html
        assert "video-segments-chart" in html
        assert "quiz-results-table" in html
        assert "learner-profile" in html

    def test_reflect_has_polling_config(self, phase2_client) -> None:
        r = phase2_client.get("/reflect")
        html = r.get_data(as_text=True)
        assert "__REFLECT_POLL_INTERVAL_MS__" in html
        assert "__REFLECT_PARTICIPANT_ID__" in html

    def test_reflect_chat_has_no_learner_id_prompt(self, phase2_client) -> None:
        """チャット初回 ID 入力プロンプトがないこと。"""
        r = phase2_client.get("/reflect")
        html = r.get_data(as_text=True)
        assert "学習者IDを教えてください" not in html
        assert "半角数字のみ" not in html

    def test_reflect_chat_has_post_to_chat(self, phase2_client) -> None:
        r = phase2_client.get("/reflect")
        html = r.get_data(as_text=True)
        assert "/chat" in html or "postChat" in html

    def test_reflect_css_exists(self, project_root) -> None:
        css_path = (
            project_root
            / "framework_drivers"
            / "platform"
            / "static"
            / "css"
            / "reflect.css"
        )
        assert css_path.exists(), "reflect.css が存在すること"
