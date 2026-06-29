"""
Phase 6: GET /reflect LAD + Chat 統合 UI

/reflect の HTML 構造、/ からのリダイレクト、participant_id 必須を検証する。
"""
import pytest

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

    def test_root_redirects_to_reflect(self, phase2_client) -> None:
        r = phase2_client.get("/")
        assert r.status_code == 302
        assert "/reflect" in r.headers.get("Location", "")

    def test_root_redirect_preserves_query_string(self, phase2_client) -> None:
        r = phase2_client.get("/?participant_id=42")
        assert r.status_code == 302
        location = r.headers.get("Location", "")
        assert "participant_id=42" in location

    def test_reflect_without_participant_id_returns_400(self, phase2_client) -> None:
        r = phase2_client.get("/reflect")
        assert r.status_code == 400
        html = r.get_data(as_text=True)
        assert "participant_id" in html

    def test_reflect_with_participant_id_returns_200(self, phase2_client) -> None:
        r = phase2_client.get("/reflect?participant_id=1")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "lad-panel" in html
        assert "chat-panel" in html

    def test_reflect_has_four_lad_blocks(self, phase2_client) -> None:
        r = phase2_client.get("/reflect?participant_id=1")
        html = r.get_data(as_text=True)
        for block_id in LAD_BLOCK_IDS:
            assert block_id in html, f"LAD ブロック {block_id} が HTML に含まれること"

    def test_reflect_loads_echarts_cdn(self, phase2_client) -> None:
        r = phase2_client.get("/reflect?participant_id=1")
        html = r.get_data(as_text=True)
        assert "echarts" in html

    def test_reflect_loads_reflect_scripts(self, phase2_client) -> None:
        r = phase2_client.get("/reflect?participant_id=1")
        html = r.get_data(as_text=True)
        for script_path in REFLECT_SCRIPT_PATHS:
            assert script_path in html, f"スクリプト {script_path} が読み込まれること"

    def test_reflect_has_chart_containers(self, phase2_client) -> None:
        r = phase2_client.get("/reflect?participant_id=1")
        html = r.get_data(as_text=True)
        assert "action-counts-chart" in html
        assert "video-segments-chart" in html
        assert "quiz-results-table" in html
        assert "learner-profile" in html

    def test_reflect_has_polling_config(self, phase2_client) -> None:
        r = phase2_client.get("/reflect?participant_id=1")
        html = r.get_data(as_text=True)
        assert "__REFLECT_POLL_INTERVAL_MS__" in html
        assert "__REFLECT_PARTICIPANT_ID__" in html

    def test_reflect_chat_has_no_learner_id_prompt(self, phase2_client) -> None:
        """チャット初回 ID 入力プロンプトがないこと。"""
        r = phase2_client.get("/reflect?participant_id=1")
        html = r.get_data(as_text=True)
        assert "学習者IDを教えてください" not in html
        assert "半角数字のみ" not in html

    def test_reflect_chat_has_post_to_chat(self, phase2_client) -> None:
        r = phase2_client.get("/reflect?participant_id=1")
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
