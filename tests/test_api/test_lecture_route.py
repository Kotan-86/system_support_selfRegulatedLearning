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

    # 仕様: docs/spec/subtitle-formatting.md#受入基準 AC11(#36 の AC11 の改訂)
    # 整形済みファイルがあればその各件、なければ元の SRT の各キュー(AC13)。
    lecture_dir = _PROJECT_ROOT / "lectures" / lecture_id
    display = lecture_dir / "subtitles.display.srt"
    segments = parse_srt_file(display if display.is_file() else lecture_dir / "subtitles.srt")
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


# ---------------------------------------------------------------------------
# 字幕の整形 (PBI #44): 整形済みファイルを表示に使う / ないときは元の SRT
# 仕様: docs/spec/subtitle-formatting.md#受入基準 (AC11, AC13)
#
# test-writer が定めた公開IF(tests.md 参照。新しい公開名は作らない):
#   講義の整形済みファイルは、講義の srt_path(Lecture.srt_path)と同じディレクトリの
#   `subtitles.display.srt`。_subtitle_cues_for_lecture はそれがあれば(読めて、件が1つ以上)
#   それを parse_srt_file で読み、なければ・読めなければ・件が0なら srt_path の元の SRT を読む。
#   テストは lecture-1 の srt_path だけを一時ディレクトリの subtitles.srt に差し替えて再現する。
# ---------------------------------------------------------------------------

_TMP_ORIG = [
    (0.0, 4.0, "これは元の字幕の一つ目です"),
    (3.0, 8.0, "これは元の字幕の二つ目です"),
]
_TMP_DISPLAY = [
    (0.0, 5.0, "整形済みの一件目の文"),
    (5.0, 9.5, "整形済みの二件目の文"),
]


def _write_srt(path: Path, cues) -> None:
    def ts(sec: float) -> str:
        ms = round(sec * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    path.write_bytes(
        "\r\n\r\n".join(
            f"{i}\r\n{ts(s)} --> {ts(e)}\r\n{t}" for i, (s, e, t) in enumerate(cues, 1)
        ).encode("utf-8")
    )


def _cues_of(cues) -> list[dict]:
    return [{"start": s, "end": e, "text": t} for s, e, t in cues]


def _use_tmp_lecture_1(monkeypatch, directory: Path, with_srt: bool = True) -> None:
    """lecture-1 の srt_path だけを directory/subtitles.srt に差し替える。"""
    from framework_drivers.platform import main as platform_main

    directory.mkdir(parents=True, exist_ok=True)
    if with_srt:
        _write_srt(directory / "subtitles.srt", _TMP_ORIG)
    catalog = platform_main._STATIC_LECTURE_CATALOG
    patched = dict(catalog._lectures)
    for lid, lecture in catalog._lectures.items():
        if str(lid) == "lecture-1":
            patched[lid] = replace(lecture, srt_path=str(directory / "subtitles.srt"))
    monkeypatch.setattr(catalog, "_lectures", patched)


def _lecture_1_html(client) -> str:
    login_as(client, "1")
    response = client.get("/lecture")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="player"' in html
    assert 'id="quiz-form"' in html
    assert "/static/js/lecture/player.js" in html
    return html


class TestLectureSubtitlesDisplayFile:
    def test_ac11_display_file_is_used_instead_of_original_srt(
        self, phase2_client, monkeypatch, tmp_path: Path
    ) -> None:
        """AC11: 整形済みファイルがあれば、ページの字幕はその各件(開始、終了、文)になる。"""
        # 仕様: docs/spec/subtitle-formatting.md#受入基準 AC11
        _use_tmp_lecture_1(monkeypatch, tmp_path / "lec")
        _write_srt(tmp_path / "lec" / "subtitles.display.srt", _TMP_DISPLAY)
        cues = _embedded_subtitles(_lecture_1_html(phase2_client))
        assert cues == _cues_of(_TMP_DISPLAY)
        assert all("元の字幕" not in c["text"] for c in cues)

    def test_ac11_display_file_of_other_lecture_is_not_used(
        self, phase2_client, monkeypatch, tmp_path: Path
    ) -> None:
        """AC11: 別の講義の整形済みファイルの字幕は含まれない(lecture-1 だけに整形済みがある)。"""
        # 仕様: docs/spec/subtitle-formatting.md#受入基準 AC11
        _use_tmp_lecture_1(monkeypatch, tmp_path / "lec")
        _write_srt(tmp_path / "lec" / "subtitles.display.srt", _TMP_DISPLAY)
        login_as(phase2_client, "2")
        cues = _embedded_subtitles(phase2_client.get("/lecture").get_data(as_text=True))
        assert not any("整形済み" in c["text"] for c in cues)
        assert cues == _expected_cues("lecture-2")

    def test_ac13_without_display_file_original_srt_cues_are_used(
        self, phase2_client, monkeypatch, tmp_path: Path
    ) -> None:
        """AC13: 整形済みファイルがない講義は、元の SRT の各キュー(#36 の AC11)。"""
        # 仕様: docs/spec/subtitle-formatting.md#受入基準 AC13
        _use_tmp_lecture_1(monkeypatch, tmp_path / "lec")
        cues = _embedded_subtitles(_lecture_1_html(phase2_client))
        assert cues == _cues_of(_TMP_ORIG)  # 重なり(0-4 と 3-8)も整理せずそのまま

    @pytest.mark.parametrize(
        "broken", ["invalid_utf8", "zero_blocks", "empty_file", "directory", "no_time_lines"]
    )
    def test_ac13_broken_display_file_falls_back_to_original_srt(
        self, phase2_client, monkeypatch, tmp_path: Path, broken: str
    ) -> None:
        """AC13: 整形済みファイルが読めない・件が1つもないときは、ないときと同じ(元の SRT)。"""
        # 仕様: docs/spec/subtitle-formatting.md#受入基準 AC13 (Q10 の推奨)
        _use_tmp_lecture_1(monkeypatch, tmp_path / "lec")
        target = tmp_path / "lec" / "subtitles.display.srt"
        if broken == "invalid_utf8":
            target.write_bytes(b"1\r\n00:00:00,000 --> 00:00:01,000\r\n\xff\xfe\x80\r\n")
        elif broken == "zero_blocks":
            target.write_bytes(b"\r\n\r\n\r\n")
        elif broken == "empty_file":
            target.write_bytes(b"")
        elif broken == "directory":
            target.mkdir()
        else:
            target.write_text("ただの文章で、SRT ではない\n二行目\n", encoding="utf-8")
        cues = _embedded_subtitles(_lecture_1_html(phase2_client))
        assert cues == _cues_of(_TMP_ORIG)

    def test_ac13_no_srt_and_no_display_file_gives_empty_subtitles(
        self, phase2_client, monkeypatch, tmp_path: Path
    ) -> None:
        """AC13: SRT も整形済みファイルもない講義でも、ページは従来どおりで字幕は空(#36 の AC12)。"""
        # 仕様: docs/spec/subtitle-formatting.md#受入基準 AC13
        _use_tmp_lecture_1(monkeypatch, tmp_path / "lec", with_srt=False)
        assert _embedded_subtitles(_lecture_1_html(phase2_client)) == []

# 文系レベル3講義 lecture-4〜6 の講義ページ (PBI #33)
# 仕様: docs/spec/humanities-lectures.md#受入基準 AC3・AC5・AC7・AC12・AC19(a)
# 期待値は tests/test_lectures/humanities_data.py(仕様のみが出典)。
# ---------------------------------------------------------------------------
from tests.test_lectures.humanities_data import (  # noqa: E402
    HUMANITIES_BY_ID,
    HUMANITIES_IDS,
)

_ALL_VIDEO_IDS = {
    "lecture-1": "Y2HC0I8cTAI",
    "lecture-2": "1MuwwFipX9o",
    "lecture-3": "Sa06YB2oXyw",
    **{lid: lec.video_id for lid, lec in HUMANITIES_BY_ID.items()},
}
_REFLECT_LINK_RE = re.compile(
    r'<a\b[^>]*\bid="quiz-reflect-link"[^>]*>|<a\b[^>]*\bhref="[^"]*"[^>]*\bid="quiz-reflect-link"[^>]*>'
)
_HREF_RE = re.compile(r'href="([^"]*)"')


def _reflect_link_href(html: str) -> str:
    tag = _REFLECT_LINK_RE.search(html)
    assert tag, "ページに id=quiz-reflect-link のリンクがない"
    href = _HREF_RE.search(tag.group(0))
    assert href, "リンクに href がない"
    return href.group(1).replace("&amp;", "&")


class TestHumanitiesLecturePage:
    @pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
    def test_ac3_page_embeds_only_own_video_id(self, phase2_client, lecture_id: str) -> None:
        """AC3: 200 で、その講義の YouTube 動画ID が埋め込まれ、他の講義の動画IDは含まれない。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC3
        login_as(phase2_client, "P01", lecture=lecture_id)  # 講義は選択で決まる(#34)
        response = phase2_client.get(f"/lecture?lecture_id={lecture_id}")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert _ALL_VIDEO_IDS[lecture_id] in html
        for other_id, video_id in _ALL_VIDEO_IDS.items():
            if other_id != lecture_id:
                assert video_id not in html, f"他の講義 {other_id} の動画IDが含まれる"

    @pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
    def test_ac5_page_shows_quiz_title_description_questions_choices(
        self, phase2_client, lecture_id: str
    ) -> None:
        """AC5: 小テストの題名・説明・5 問の問題文・各選択肢がページにある。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC5
        expected = HUMANITIES_BY_ID[lecture_id]
        login_as(phase2_client, "P01", lecture=lecture_id)  # 講義は選択で決まる(#34)
        response = phase2_client.get(f"/lecture?lecture_id={lecture_id}")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert expected.quiz_title in html
        assert expected.quiz_description in html
        assert 'id="quiz-form"' in html
        assert len(expected.questions) == 5
        for question in expected.questions:
            assert question.text in html
            for choice in question.choices:
                assert choice in html

    @pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
    def test_ac5_page_has_no_explanation(self, phase2_client, lecture_id: str) -> None:
        """AC5: ページに解説は含まれない(付録A には解説の文がないため、「解説」の見出し語がないことで確かめる)。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC5 / 実現内容3(解説は表示しない)
        login_as(phase2_client, "P01", lecture=lecture_id)  # 講義は選択で決まる(#34)
        response = phase2_client.get(f"/lecture?lecture_id={lecture_id}")
        assert response.status_code == 200
        assert "解説：" not in response.get_data(as_text=True)
        assert "【解説】" not in response.get_data(as_text=True)
        assert 'class="explanation"' not in response.get_data(as_text=True)

    @pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
    def test_ac7_embedded_subtitles_equal_parse_of_subtitles_srt(
        self, phase2_client, lecture_id: str
    ) -> None:
        """AC7: 埋め込まれる字幕は subtitles.srt を parse_srt_file で読んだ結果(開始・終了・文)と一致する。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC7
        from interfaces.tutoring.srt import parse_srt_file

        srt = _PROJECT_ROOT / "lectures" / lecture_id / "subtitles.srt"
        assert srt.is_file()
        expected = [
            {"start": s["start_sec"], "end": s["end_sec"], "text": s["text"]}
            for s in parse_srt_file(srt)
        ]
        login_as(phase2_client, "P01", lecture=lecture_id)  # 講義は選択で決まる(#34)
        response = phase2_client.get(f"/lecture?lecture_id={lecture_id}")
        assert response.status_code == 200
        cues = _embedded_subtitles(response.get_data(as_text=True))
        assert len(expected) == HUMANITIES_BY_ID[lecture_id].srt_blocks
        assert cues == expected

    def test_ac12_unregistered_lecture_id_is_ignored_for_a_selected_participant(self, phase2_client) -> None:
        """AC12(置き換え): 未登録の講義(lecture-7)を付けても 404 にならず、選択した講義の画面になる。"""
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC15(旧: docs/spec/humanities-lectures.md AC12 の 404)
        login_as(phase2_client, "P01")
        response = phase2_client.get("/lecture?lecture_id=lecture-7")
        assert response.status_code == 200
        assert _ALL_VIDEO_IDS["lecture-1"] in response.get_data(as_text=True)

    @pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
    def test_ac19a_reflect_link_carries_page_lecture_id(
        self, phase2_client, lecture_id: str
    ) -> None:
        """AC19(a): 「振り返り画面へ進む」のリンク先は /reflect?lecture_id=<ページの講義ID>。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC19(a)
        login_as(phase2_client, "P01", lecture=lecture_id)  # 講義は選択で決まる(#34)
        html = phase2_client.get(f"/lecture?lecture_id={lecture_id}").get_data(as_text=True)
        assert _reflect_link_href(html) == f"/reflect?lecture_id={lecture_id}"

    def test_ac19a_reflect_link_without_lecture_id_uses_displayed_lecture(
        self, phase2_client
    ) -> None:
        """AC19(a): P01 が講義IDなしで開いた /lecture のリンク先は /reflect?lecture_id=lecture-1。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC19(a)
        login_as(phase2_client, "P01")
        html = phase2_client.get("/lecture").get_data(as_text=True)
        assert _reflect_link_href(html) == "/reflect?lecture_id=lecture-1"

    @pytest.mark.parametrize(
        ("participant_id", "lecture_id"),
        [("1", "lecture-1"), ("2", "lecture-2"), ("3", "lecture-3")],
    )
    def test_ac19a_reflect_link_for_selected_lecture(
        self, phase2_client, participant_id: str, lecture_id: str
    ) -> None:
        """AC19(a)・AC13(b): 講義を選択済みの参加者のリンク先は、表示している講義のID。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC19(a)
        login_as(phase2_client, participant_id)
        html = phase2_client.get("/lecture").get_data(as_text=True)
        assert _reflect_link_href(html) == f"/reflect?lecture_id={lecture_id}"


class TestLecturePageExistingBehavior:
    """AC13: 講義IDなしの既存の挙動が変わらない。"""

    def test_ac13a_p01_without_lecture_id_shows_lecture_1(self, phase2_client) -> None:
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC13(a)
        login_as(phase2_client, "P01")
        response = phase2_client.get("/lecture")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Y2HC0I8cTAI" in html
        for other_id, video_id in _ALL_VIDEO_IDS.items():
            if other_id != "lecture-1":
                assert video_id not in html

    @pytest.mark.parametrize(
        ("participant_id", "lecture_id"),
        [("1", "lecture-1"), ("2", "lecture-2"), ("3", "lecture-3")],
    )
    def test_ac13b_selected_lecture_pages(
        self, phase2_client, participant_id: str, lecture_id: str
    ) -> None:
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC13(b)
        login_as(phase2_client, participant_id)
        html = phase2_client.get("/lecture").get_data(as_text=True)
        assert _ALL_VIDEO_IDS[lecture_id] in html
