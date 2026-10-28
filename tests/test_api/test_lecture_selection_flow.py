# 仕様: docs/spec/lecture-selection.md#受入基準 (PBI #34) AC1〜6・8・9・15・16(A. 選択の画面と導線、B. 選択の固定)
"""講義の選択の画面・確認・確定・固定と、画面(/lecture、/reflect)の導線を、Flask のテストクライアントで確かめる。

URL とフォームの項目名は tests/selection_helpers.py の先頭に定めた公開IF。
AC7(画面の操作)は PO 確認。ここでは、そのうち自動で確かめられる範囲(AC2・3 の表示内容)だけをテストにする。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from tests.login_helpers import (
    TEST_PASSWORD,
    build_app,
    dump_databases,
    location_path,
    login_as,
    post_login,
)
from tests.selection_helpers import (
    CONFIRM_PATH,
    QUIZ_TITLES,
    SELECT_PATH,
    TRACK_OF,
    WARNING_TEXT,
    all_lecture_ids,
    catalog_lectures,
    choose,
    count_rows,
    embedded_reflect_lecture_id,
    is_selection_redirect,
    learning_sessions,
    lecture_page_has_no_other,
    lecture_page_shows,
    login_and_choose,
    login_unselected,
    option_values,
    started_at_of,
)

ALL_IDS = all_lecture_ids()
PID = "P02"


def _viewing(current_time: int = 3) -> dict:
    return {
        "time_stamp": "2026-10-28T11:18:42",
        "current_time": current_time,
        "action": "play",
        "duration": 0,
    }


@pytest.fixture
def app_env(monkeypatch, tmp_path):
    app, _llm = build_app(monkeypatch, tmp_path)
    return app


@pytest.fixture
def unselected(app_env):
    """未選択の P02 でログイン済みのクライアント。"""
    client = app_env.test_client()
    login_unselected(client, PID)
    return client


# ---------------------------------------------------------------- AC1 未選択の導線


class TestAc1UnselectedRedirects:
    @pytest.mark.parametrize(
        "path",
        ["/", "/lecture", "/reflect", "/reflect?lecture_id=lecture-2", "/reflect?lecture_id=lecture-9"],
    )
    def test_ac1_unselected_screens_redirect_to_selection_and_save_nothing(
        self, unselected, tmp_path, path
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC1
        response = unselected.get(path)

        assert is_selection_redirect(response), (response.status_code, response.headers.get("Location"))
        assert count_rows(tmp_path, "learning.db", "learning_sessions") == 0

    def test_ac1_login_with_next_reflect_ends_at_the_selection_screen(self, app_env, tmp_path) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC1(ログインの移動先に /reflect を指定したとき)
        client = app_env.test_client()
        response = client.post(
            "/login",
            data={"participant_id": PID, "password": TEST_PASSWORD, "next": "/reflect"},
            follow_redirects=True,
        )

        assert response.request.path == SELECT_PATH
        assert response.status_code == 200
        assert learning_sessions(tmp_path) == []

    def test_selection_screen_and_confirm_require_login(self, app_env, tmp_path) -> None:
        # 仕様: docs/spec/lecture-selection.md#実現内容 2(選択の画面と選択の確定は、ログインが必要。FR-51)
        client = app_env.test_client()
        before = dump_databases(tmp_path)

        screen = client.get(SELECT_PATH)
        confirm = choose(client, "lecture-2")

        assert screen.status_code == 302 and location_path(screen) == "/login"
        assert confirm.status_code == 302 and location_path(confirm) == "/login"
        assert dump_databases(tmp_path) == before


# ---------------------------------------------------------------- AC2 選択肢の表示


class TestAc2Options:
    def test_ac2_options_are_the_catalog_in_order_with_title_and_track(self, unselected) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC2
        lectures = catalog_lectures()

        response = unselected.get(SELECT_PATH)

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert option_values(html) == [str(lec.id) for lec in lectures]
        assert len(lectures) >= 6
        positions = []
        for lecture in lectures:
            assert lecture.title in html, lecture.title
            positions.append(html.index(lecture.title))
        assert positions == sorted(positions), "題名がカタログの順に並んでいない"
        # 各講義の題名から次の講義の題名までの間に、その講義の系統(だけ)が表示される
        for index, lecture in enumerate(lectures):
            end = positions[index + 1] if index + 1 < len(lectures) else len(html)
            segment = html[positions[index]:end]
            track = TRACK_OF[str(lecture.id)]
            other = "文系" if track == "理系" else "理系"
            assert track in segment, f"{lecture.id} の系統 {track} が表示されていない"
            if index + 1 < len(lectures):
                assert other not in segment, f"{lecture.id} に別の系統 {other} が表示されている"

    def test_ac2_lectures_not_in_the_catalog_are_not_listed(self, unselected) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC2(カタログにない講義は並ばない)
        html = unselected.get(SELECT_PATH).get_data(as_text=True)

        assert option_values(html), "選択肢がない"
        assert "lecture-7" not in html and "lecture-9" not in html


# ---------------------------------------------------------------- AC3 確定の前の確認


class TestAc3Confirmation:
    @pytest.mark.parametrize("lecture_id", ALL_IDS)
    def test_ac3_first_operation_shows_title_warning_and_confirm_but_saves_nothing(
        self, unselected, tmp_path, lecture_id
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC3
        title = next(str(lec.title) for lec in catalog_lectures() if str(lec.id) == lecture_id)

        response = unselected.post(SELECT_PATH, data={"lecture_id": lecture_id})

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert title in html
        assert WARNING_TEXT in html
        assert CONFIRM_PATH in html, "確定の操作(action が /select-lecture/confirm のフォーム)がない"
        assert learning_sessions(tmp_path) == []
        assert is_selection_redirect(unselected.get("/lecture"))


# ---------------------------------------------------------------- AC4 選択の確定


class TestAc4Confirm:
    @pytest.mark.parametrize("lecture_id", ALL_IDS)
    def test_ac4_confirm_saves_a_learning_session_and_shows_the_lecture(
        self, unselected, tmp_path, lecture_id
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC4(カタログの全講義で繰り返す)
        unselected.post(SELECT_PATH, data={"lecture_id": lecture_id})  # AC3 に続けて
        started_after = datetime.now(timezone.utc)

        response = choose(unselected, lecture_id)

        assert response.status_code == 302
        assert location_path(response) == "/lecture"
        assert learning_sessions(tmp_path) == [(PID, lecture_id)]
        for table in ("viewing_logs", "quiz_attempts"):
            assert count_rows(tmp_path, "learning.db", table) == 0
        page = unselected.get("/lecture")
        assert page.status_code == 200
        html = page.get_data(as_text=True)
        assert lecture_page_shows(html, lecture_id)
        assert lecture_page_has_no_other(html, lecture_id)
        assert QUIZ_TITLES[lecture_id] in html and 'id="quiz-form"' in html
        # 開始時刻は、選択を確定した時刻
        started = datetime.fromisoformat(started_at_of(tmp_path, PID, lecture_id))
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        assert started_after - timedelta(seconds=5) <= started <= datetime.now(timezone.utc) + timedelta(seconds=5)

    def test_ac4_selected_participant_does_not_see_the_selection_screen(self, unselected) -> None:
        # 仕様: docs/spec/lecture-selection.md#実現内容 2(選択済みは、選択の画面を経ずに講義の画面)
        assert choose(unselected, "lecture-5").status_code == 302

        for path in ("/", "/lecture"):
            response = unselected.get(path, follow_redirects=True)
            assert response.request.path == "/lecture"
            assert response.status_code == 200
            assert lecture_page_shows(response.get_data(as_text=True), "lecture-5")


# ---------------------------------------------------------------- AC5 拒否


class TestAc5Rejection:
    @pytest.mark.parametrize(
        "data",
        [{"lecture_id": "lecture-9"}, {"lecture_id": ""}, {}],
        ids=["not-in-catalog", "empty", "missing"],
    )
    def test_ac5_invalid_confirm_is_400_and_saves_nothing(self, unselected, tmp_path, data) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC5
        before = dump_databases(tmp_path)

        response = unselected.post(CONFIRM_PATH, data=data)

        assert response.status_code == 400
        assert dump_databases(tmp_path) == before
        assert learning_sessions(tmp_path) == []
        assert is_selection_redirect(unselected.get("/lecture"))


# ---------------------------------------------------------------- AC6 選択済みの導線


class TestAc6SelectedFlow:
    def test_ac6_relogin_and_other_browser_show_the_selected_lecture(self, app_env, tmp_path) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC6
        client = app_env.test_client()
        login_and_choose(client, PID, "lecture-5")
        assert client.post("/logout").status_code == 302

        for browser in (client, app_env.test_client()):
            login = post_login(browser, PID)
            assert login.status_code == 302
            assert location_path(login) == "/lecture"
            page = browser.get("/lecture")
            assert page.status_code == 200
            assert lecture_page_shows(page.get_data(as_text=True), "lecture-5")
        assert learning_sessions(tmp_path) == [(PID, "lecture-5")]

    def test_ac6_selection_screen_for_a_selected_participant_redirects_to_the_lecture(
        self, app_env
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC6
        client = app_env.test_client()
        login_and_choose(client, PID, "lecture-2")

        response = client.get(SELECT_PATH)

        assert response.status_code == 302
        assert location_path(response) == "/lecture"


# ---------------------------------------------------------------- AC8 固定


class TestAc8Fixed:
    def test_ac8_confirming_another_lecture_does_not_change_the_selection(
        self, app_env, tmp_path
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC8(2つのタブ・送信の二重化)
        client = app_env.test_client()
        login_and_choose(client, PID, "lecture-2")

        response = choose(client, "lecture-5")

        assert response.status_code == 302
        assert location_path(response) == "/lecture"
        assert learning_sessions(tmp_path) == [(PID, "lecture-2")]
        assert lecture_page_shows(client.get("/lecture").get_data(as_text=True), "lecture-2")
        again = choose(client, "lecture-2")
        assert again.status_code == 302
        assert learning_sessions(tmp_path) == [(PID, "lecture-2")]

    def test_ac8_selection_survives_the_12_hour_login_expiry(self, monkeypatch, tmp_path) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC8(時刻を進める)
        now = [datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)]
        app, _ = build_app(monkeypatch, tmp_path, clock=lambda: now[0])
        client = app.test_client()
        login_and_choose(client, PID, "lecture-5")

        now[0] += timedelta(hours=13)
        expired = client.get("/lecture")
        assert expired.status_code == 302 and location_path(expired) == "/login"
        login_as(client, PID, lecture=None)
        page = client.get("/lecture")

        assert page.status_code == 200
        assert lecture_page_shows(page.get_data(as_text=True), "lecture-5")
        assert learning_sessions(tmp_path) == [(PID, "lecture-5")]


# ---------------------------------------------------------------- AC9 協力者ごとの独立


class TestAc9Independent:
    def test_ac9_each_participant_has_their_own_selection(self, app_env, tmp_path) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC9
        a, b, c = app_env.test_client(), app_env.test_client(), app_env.test_client()
        login_and_choose(a, "A", "lecture-2")
        login_and_choose(b, "B", "lecture-5")
        login_and_choose(c, "P03", "lecture-2")  # 同じ講義を複数の ID が選べる

        assert learning_sessions(tmp_path) == [("A", "lecture-2"), ("B", "lecture-5"), ("P03", "lecture-2")]
        for client, lecture_id in ((a, "lecture-2"), (b, "lecture-5"), (c, "lecture-2")):
            assert lecture_page_shows(client.get("/lecture").get_data(as_text=True), lecture_id)
        assert a.post("/api/viewing-log", json=_viewing(3)).status_code == 201
        assert b.post("/api/viewing-log", json=_viewing(4)).status_code == 201
        conn = sqlite3.connect(str(tmp_path / "learning.db"))
        try:
            rows = conn.execute(
                "SELECT s.learner_id, s.lecture_id FROM viewing_logs v "
                "JOIN learning_sessions s ON s.id = v.learning_session_id ORDER BY 1"
            ).fetchall()
        finally:
            conn.close()
        assert [tuple(r) for r in rows] == [("A", "lecture-2"), ("B", "lecture-5")]


# ---------------------------------------------------------------- AC15 画面の lecture_id


class TestAc15ScreenLectureId:
    @pytest.fixture
    def selected(self, app_env):
        client = app_env.test_client()
        login_and_choose(client, PID, "lecture-2")
        return client

    @pytest.mark.parametrize("value", ["lecture-5", "lecture-9", "lecture-1"])
    def test_ac15_lecture_with_other_value_is_ignored_and_shows_the_selected_lecture(
        self, selected, value
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC15
        response = selected.get(f"/lecture?lecture_id={value}")

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert lecture_page_shows(html, "lecture-2")
        assert lecture_page_has_no_other(html, "lecture-2")

    @pytest.mark.parametrize("path", ["/reflect", "/reflect?lecture_id=lecture-2"])
    def test_ac15_reflect_embeds_the_selected_lecture_id(self, selected, path) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC15
        response = selected.get(path)

        assert response.status_code == 200
        assert embedded_reflect_lecture_id(response.get_data(as_text=True)) == "lecture-2"

    @pytest.mark.parametrize("value", ["lecture-5", "lecture-9"])
    def test_ac15_reflect_with_other_value_is_403(self, selected, value) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC15
        assert selected.get(f"/reflect?lecture_id={value}").status_code == 403

    @pytest.mark.parametrize("path", ["/lecture?lecture_id=", "/reflect?lecture_id="])
    def test_ac15_empty_value_is_404_for_a_selected_participant(self, selected, path) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC15(DR-003: 現状の維持)
        assert selected.get(path).status_code == 404

    @pytest.mark.parametrize(
        "path", ["/lecture?lecture_id=lecture-2", "/lecture?lecture_id=", "/reflect?lecture_id="]
    )
    def test_ac15_unselected_participant_is_redirected_and_nothing_is_saved(
        self, unselected, tmp_path, path
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC15
        response = unselected.get(path)

        assert is_selection_redirect(response)
        assert learning_sessions(tmp_path) == []
        assert is_selection_redirect(unselected.get("/lecture"))


# ---------------------------------------------------------------- AC16 固定対応の廃止


class TestAc16FixedMappingRemoved:
    @pytest.mark.parametrize("participant_id", ["1", "2", "3", "P01", "P30"])
    def test_ac16_unselected_ids_go_to_selection_not_to_a_fixed_lecture(
        self, app_env, tmp_path, participant_id
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC16
        client = app_env.test_client()
        login_unselected(client, participant_id)

        for path in ("/", "/lecture", "/reflect"):
            response = client.get(path)
            assert is_selection_redirect(response), (participant_id, path, response.status_code)
        assert learning_sessions(tmp_path) == []

    def test_ac16_participant_2_selects_lecture_5_and_gets_it(self, app_env, tmp_path) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC16
        client = app_env.test_client()
        login_and_choose(client, "2", "lecture-5")

        html = client.get("/lecture").get_data(as_text=True)

        assert lecture_page_shows(html, "lecture-5")
        assert lecture_page_has_no_other(html, "lecture-5")
        assert client.post("/api/viewing-log", json=_viewing()).status_code == 201
        assert learning_sessions(tmp_path) == [("2", "lecture-5")]

    @pytest.mark.parametrize("default_lecture", ["lecture-3", "lecture-5"])
    def test_ac16_default_lecture_env_does_not_change_ac1_ac4_ac10(
        self, monkeypatch, tmp_path, default_lecture
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC16(DEFAULT_LECTURE_ID を設定しても結果は変わらない)
        monkeypatch.setenv("DEFAULT_LECTURE_ID", default_lecture)
        app, _ = build_app(monkeypatch, tmp_path)
        client = app.test_client()
        login_unselected(client, "P01")
        assert is_selection_redirect(client.get("/lecture"))  # AC1

        assert choose(client, "lecture-2").status_code == 302  # AC4
        assert lecture_page_shows(client.get("/lecture").get_data(as_text=True), "lecture-2")
        assert client.post("/api/viewing-log", json=_viewing()).status_code == 201  # AC10(lecture_id なし)
        assert learning_sessions(tmp_path) == [("P01", "lecture-2")]
