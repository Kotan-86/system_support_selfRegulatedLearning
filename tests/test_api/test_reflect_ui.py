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


# ---------------------------------------------------------------------------
# 振り返りページへの講義IDの引き継ぎ (PBI #33)
# 仕様: docs/spec/humanities-lectures.md#受入基準 AC19(b)(c)(d)
#
# test-writer が定めた公開IF(tests.md 参照):
#   reflect.html は <script> の中に `window.__REFLECT_LECTURE_ID__ = <JSON>;` を埋め込む。
#   URL に lecture_id があり登録済みならその文字列、なければ null。
#   (講義IDなしのとき、選択済みの講義IDを URL 由来として埋め込まない = JS が /chat 等に講義IDを付けない。)
# ---------------------------------------------------------------------------
import json  # noqa: E402
import re  # noqa: E402

_REFLECT_LECTURE_RE = re.compile(r"window\.__REFLECT_LECTURE_ID__\s*=\s*(.+?);\s*$", re.M)


def _embedded_reflect_lecture_id(html: str):
    """埋め込まれた講義ID。代入が無いときは None(= 講義IDなし)。"""
    match = _REFLECT_LECTURE_RE.search(html)
    return json.loads(match.group(1)) if match else None


class TestReflectLectureIdCarryOver:
    @pytest.mark.parametrize("lecture_id", ["lecture-4", "lecture-5", "lecture-6", "lecture-2"])
    def test_ac19b_reflect_with_lecture_id_embeds_it(self, phase2_client, lecture_id: str) -> None:
        """AC19(b): 選択した講義と一致する /reflect?lecture_id= は 200 で、ページがその講義IDを埋め込む。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC19(b) / docs/spec/lecture-selection.md#受入基準 AC15
        login_as(phase2_client, "P01", lecture=lecture_id)
        response = phase2_client.get(f"/reflect?lecture_id={lecture_id}")
        assert response.status_code == 200
        assert _embedded_reflect_lecture_id(response.get_data(as_text=True)) == lecture_id

    @pytest.mark.parametrize("participant_id", ["P01", "2"])
    def test_ac19c_reflect_without_lecture_id_embeds_selected_lecture(
        self, phase2_client, participant_id: str
    ) -> None:
        """AC19(c)(置き換え): 講義IDなしの /reflect は、選択した講義の講義IDを埋め込む。"""
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC15(旧: humanities-lectures.md AC19(c) は埋め込まない)
        login_as(phase2_client, participant_id)  # P01 は lecture-1、"2" は lecture-2 を選択済み
        response = phase2_client.get("/reflect")
        assert response.status_code == 200
        expected = "lecture-2" if participant_id == "2" else "lecture-1"
        assert _embedded_reflect_lecture_id(response.get_data(as_text=True)) == expected

    @pytest.mark.parametrize("query", ["lecture_id=lecture-7", "lecture_id=lecture-99", "lecture_id=%E3%81%82"])
    def test_ac19d_reflect_with_unregistered_lecture_id_is_403(
        self, phase2_client, query: str
    ) -> None:
        """AC19(d)(置き換え): 選択済みで、選択と異なる(未登録の)講義IDを付けた /reflect は 403。"""
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC15(旧: humanities-lectures.md AC19(d) は 404)
        login_as(phase2_client, "P01")
        assert phase2_client.get(f"/reflect?{query}").status_code == 403

    def test_ac19d_reflect_with_empty_lecture_id_is_404(self, phase2_client) -> None:
        """AC19(d): 空文字の lecture_id を付けた /reflect は 404。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC19(d)
        login_as(phase2_client, "P01")
        assert phase2_client.get("/reflect?lecture_id=").status_code == 404

    def test_ac19b_embedded_lecture_id_is_declared_before_reflect_scripts(self, phase2_client) -> None:
        """AC19(b): 講義IDの埋め込みは、それを読む JS(chat_panel.js, reflect_app.js)より前にある。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC19(b)
        login_as(phase2_client, "P01", lecture="lecture-4")
        html = phase2_client.get("/reflect?lecture_id=lecture-4").get_data(as_text=True)
        declared = html.find("__REFLECT_LECTURE_ID__")
        assert declared != -1
        assert declared < html.find("js/reflect/chat_panel.js")
        assert declared < html.find("js/reflect/reflect_app.js")
