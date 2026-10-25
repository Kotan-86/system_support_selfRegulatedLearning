# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-5-講義動画フロント
# 仕様: docs/spec/interfaces-layer.md#ingress-規約
"""GET /lecture と視聴ログ payload 契約の API テスト。"""
from __future__ import annotations

import pytest

from tests.login_helpers import displayed_participant_id, login_as


class TestLectureRoute:
    """GET /lecture の HTML 配信。"""

    def test_lecture_without_participant_id_shows_logged_in_participant(
        self, phase2_client
    ) -> None:
        """AC11(participant-login): participant_id なしでも、ログインした本人の講義画面が 200 で出る。
        (旧: participant_id なしは 400。ログイン導入で仕様が変わった。)
        """
        # 仕様: docs/spec/participant-login.md#受入基準
        login_as(phase2_client, "A")
        response = phase2_client.get("/lecture")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert displayed_participant_id(html) == "A"
        assert 'id="player"' in html

    def test_lecture_with_participant_id_returns_200(self, phase2_client) -> None:
        """ログインした ID の講義画面は 200 とプレイヤー要素を返す。"""
        login_as(phase2_client, "learner-42")
        response = phase2_client.get("/lecture")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert displayed_participant_id(html) == "learner-42"
        assert 'id="player"' in html
        assert "youtube.com/iframe_api" in html
        assert "/static/js/lecture/player.js" in html

    def test_lecture_participant_2_shows_lecture_2_video(self, phase2_client) -> None:
        """ログイン ID "2" は lecture-2 の YouTube 動画 ID を埋め込む。"""
        login_as(phase2_client, "2")
        response = phase2_client.get("/lecture")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "lecture-2" in html
        assert "1MuwwFipX9o" in html

    def test_lecture_static_js_is_served(self, phase2_client) -> None:
        """講義用 JS が static から配信される。"""
        for path in (
            "/static/js/common/participant_context.js",
            "/static/js/common/api_client.js",
            "/static/js/lecture/player.js",
            "/static/js/lecture/quiz.js",
        ):
            response = phase2_client.get(path)
            assert response.status_code == 200, path

    @pytest.mark.parametrize(
        ("participant_id", "q1_snippet", "quiz_title"),
        [
            (
                "1",
                "動画では、球の表面積は、同じ半径 r、高さ 2r の円柱のどの部分の面積と等しいと説明されていますか。",
                "球の表面積に関する理解度テスト",
            ),
            (
                "2",
                "標準的なモンティ・ホール問題で、司会者がハズレの扉を1つ開けた後、",
                "モンティ・ホール問題：直感と論理のクイズ",
            ),
            (
                "3",
                "A・B・Cのうち1人だけが恩赦を受けます。",
                "3囚人問題：確率のパラドックスに挑戦",
            ),
        ],
    )
    def test_lecture_embedded_quiz_for_each_participant(
        self,
        phase2_client,
        participant_id: str,
        q1_snippet: str,
        quiz_title: str,
    ) -> None:
        """participant_id=1/2/3 で講義別の埋め込み小テストが表示される。"""
        login_as(phase2_client, participant_id)
        response = phase2_client.get("/lecture")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert q1_snippet in html
        assert quiz_title in html
        assert 'id="quiz-form"' in html
        assert "/static/js/lecture/quiz.js" in html
        assert "forms.gle" not in html
        assert "docs.google.com/forms" not in html


def _gas_viewing_log_payload(*, participant_id: str, action: str, duration: float):
    """player.js / api_client.js buildViewingLogPayload と同一形状。"""
    return {
        "participant_id": participant_id,
        "time_stamp": "2026-02-23T11:18:42.000Z",
        "current_time": 120,
        "action": action,
        "duration": duration,
    }


class TestLectureViewingLogActions:
    """play / pause / skip / seek が API 契約 payload で 201 を返す。"""

    @pytest.mark.parametrize(
        ("action", "duration"),
        [
            ("play", 0.0),
            ("pause", 0.0),
            ("forward_skip", 5.0),
            ("backward_skip", -5.0),
            ("forward_seek", 10.0),
            ("backward_seek", -10.0),
        ],
    )
    def test_viewing_action_returns_201(
        self, phase2_client, action: str, duration: float
    ) -> None:
        payload = _gas_viewing_log_payload(
            participant_id="1",
            action=action,
            duration=duration,
        )
        response = phase2_client.post(
            "/api/viewing-log",
            json=payload,
            content_type="application/json",
        )
        assert response.status_code == 201, (
            f"action={action!r} の payload は 201 を返すこと"
        )


# ---------------------------------------------------------------------------
# 字幕の表示・非表示 (PBI #36)
# 仕様: docs/spec/subtitle-display.md#受入基準 (AC11, AC12)
#
# test-writer が定めた公開IF(tests.md 参照):
#   講義ページは <script> の中に `window.__LECTURE_SUBTITLES__ = <JSON>;` を1行で埋め込む。
#   JSON は [{"start": 秒, "end": 秒, "text": 文}, ...] で、SRT の各キューを
#   重なりの整理なしにファイルの順で並べたもの(interfaces/tutoring/srt.py の parse_srt_file と同じ値)。
#   SRT が読めないときは [] 。
# ---------------------------------------------------------------------------

import json
import re
from dataclasses import replace
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SUBTITLES_RE = re.compile(r"window\.__LECTURE_SUBTITLES__\s*=\s*(.+?);?\s*$", re.M)


def _embedded_subtitles(html: str) -> list[dict]:
    match = _SUBTITLES_RE.search(html)
    assert match, "ページに window.__LECTURE_SUBTITLES__ の埋め込みがない"
    return json.loads(match.group(1))


def _expected_cues(lecture_id: str) -> list[dict]:
    from interfaces.tutoring.srt import parse_srt_file

    segments = parse_srt_file(_PROJECT_ROOT / "lectures" / lecture_id / "subtitles.srt")
    return [
        {"start": s["start_sec"], "end": s["end_sec"], "text": s["text"]}
        for s in segments
    ]


class TestLectureSubtitlesRoute:
    """字幕データの配信(AC11)と SRT がない講義(AC12)。"""

    @pytest.mark.parametrize(
        ("participant_id", "lecture_id"),
        [("1", "lecture-1"), ("2", "lecture-2"), ("3", "lecture-3")],
    )
    def test_ac11_embedded_subtitles_match_lecture_srt(
        self, phase2_client, participant_id: str, lecture_id: str
    ) -> None:
        """AC11: 講義 X のページの字幕は lectures/X/subtitles.srt の内容。"""
        # 仕様: docs/spec/subtitle-display.md#受入基準 AC11
        login_as(phase2_client, participant_id)  # 講義は本人のログインで決まる(#30)
        html = phase2_client.get("/lecture").get_data(as_text=True)
        cues = _embedded_subtitles(html)
        expected = _expected_cues(lecture_id)
        assert len(expected) > 100
        assert cues == expected

    def test_ac11_other_lecture_subtitles_are_not_embedded(self, phase2_client) -> None:
        """AC11: 別の講義の字幕は表示されない(講義ごとに内容が異なる)。"""
        # 仕様: docs/spec/subtitle-display.md#受入基準 AC11
        by_lecture = {}
        for pid in ("1", "2", "3"):
            login_as(phase2_client, pid)  # 講義は本人のログインで決まる(#30)
            by_lecture[pid] = _embedded_subtitles(
                phase2_client.get("/lecture").get_data(as_text=True)
            )
        texts = {pid: {c["text"] for c in cues} for pid, cues in by_lecture.items()}
        assert by_lecture["1"] != by_lecture["2"] != by_lecture["3"]
        # 各講義の先頭付近の文が、他の講義のデータに入っていない
        for pid, other in (("1", "2"), ("1", "3"), ("2", "1"), ("3", "1")):
            own_unique = {c["text"] for c in by_lecture[pid][1:4]} - texts[other]
            assert own_unique, f"講義(参加者{pid})の字幕が参加者{other}と区別できない"

    def test_wiring_subtitle_elements_and_script_order(self, phase2_client) -> None:
        """配線(AC2〜6 の前提): 表示領域・ボタン・subtitles.js が player.js より前にある。"""
        # 仕様: docs/spec/subtitle-display.md#受入基準 AC1(配線のみ。見た目はPO確認)
        html = phase2_client.get("/lecture").get_data(as_text=True)
        assert 'id="subtitle-area"' in html
        assert 'id="subtitle-toggle"' in html
        sub = html.find("/static/js/lecture/subtitles.js")
        ply = html.find("/static/js/lecture/player.js")
        assert sub != -1, "subtitles.js が読み込まれていない"
        assert sub < ply
        assert phase2_client.get("/static/js/lecture/subtitles.js").status_code == 200

    @pytest.mark.parametrize("mode", ["missing", "directory", "invalid_utf8"])
    def test_ac12_missing_or_unreadable_srt_keeps_page_working(
        self, phase2_client, monkeypatch, tmp_path: Path, mode: str
    ) -> None:
        """AC12: SRT がない・読めない講義でも、講義ページは従来どおり表示される。"""
        # 仕様: docs/spec/subtitle-display.md#受入基準 AC12
        from framework_drivers.platform import main as platform_main

        if mode == "missing":
            bad_path = tmp_path / "no-such" / "subtitles.srt"
        elif mode == "directory":
            bad_path = tmp_path / "dir"
            bad_path.mkdir()
        else:
            bad_path = tmp_path / "broken.srt"
            bad_path.write_bytes(b"1\n00:00:00,000 --> 00:00:01,000\n\xff\xfe\x80\n")

        catalog = platform_main._STATIC_LECTURE_CATALOG
        broken = {
            lid: replace(lecture, srt_path=str(bad_path))
            for lid, lecture in catalog._lectures.items()
        }
        monkeypatch.setattr(catalog, "_lectures", broken)

        response = phase2_client.get("/lecture")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'id="player"' in html
        assert 'id="quiz-form"' in html
        assert "/static/js/lecture/player.js" in html
        assert "1MuwwFipX9o" not in html  # lecture-2 の動画ではない(参加者1=lecture-1)
        assert _embedded_subtitles(html) == []
