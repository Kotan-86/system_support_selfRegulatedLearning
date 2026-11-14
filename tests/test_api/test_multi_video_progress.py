# 仕様: docs/spec/multi-video-learning.md#受入基準 (PBI #56 PBI-A) AC1〜10(A. 回の進行)
"""1人3本の動画の学習の、回の進行(選択 → 学習 → 終了ボタンで回の終了 → 次の回 → 全体の終了)を、
Flask のテストクライアント(一時ディレクトリの DB、偽の LLM)で確かめる。

状態は HTTP の操作だけで作る(tests/multi_video_helpers.py)。
PBI-A の範囲外(PBI-B): 「n本目 / 3本」の表示、選び直し、完了画面の導線、全体の終了の画面の文言。
"""
from __future__ import annotations

import pytest

from tests.login_helpers import build_app, dump_databases, location_path
from tests.multi_video_helpers import (
    SIX_APIS,
    W,
    X,
    Y,
    Z,
    build_progress,
    call_api,
    confirm_round,
    end_screen_path,
    finish_round,
    lectures_of,
    login_follow,
    next_second,
    option_lectures_expected,
    save_dialog_log,
    send_chat,
    shown_lecture,
    tutor_rows,
)
from tests.selection_helpers import (
    CONFIRM_PATH,
    SELECT_PATH,
    all_lecture_ids,
    choose,
    is_selection_redirect,
    option_values,
)

PID = "P02"
OTHER_PID = "A"


@pytest.fixture
def env(monkeypatch, tmp_path):
    app, llm = build_app(monkeypatch, tmp_path)
    return app, llm, tmp_path


def _llm_calls(llm) -> tuple[int, int]:
    return len(llm.generate_calls), len(llm.generate_json_calls)


# ---------------------------------------------------------------- AC1 1本目の選択


class TestAc1FirstSelection:
    def test_ac1_login_without_sessions_goes_to_selection_and_confirm_creates_one_session(
        self, env
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC1(「1本目 / 3本」の表示は PBI-B)
        app, _llm, tmp_path = env
        client = app.test_client()

        landed = login_follow(client, PID)

        assert landed.request.path == SELECT_PATH
        assert landed.status_code == 200
        assert option_values(landed.get_data(as_text=True)) == all_lecture_ids()
        confirm_round(client, X)
        assert lectures_of(tmp_path, PID) == [X]
        page = client.get("/lecture")
        assert page.status_code == 200
        assert shown_lecture(page.get_data(as_text=True)) == X


# ---------------------------------------------------------------- AC2 記録の後は回の途中で選べない


class TestAc2NoSelectionAfterRecord:
    def test_ac2_after_a_viewing_log_selection_screen_and_confirm_redirect_to_lecture(
        self, env
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC2
        app, _llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [], X, record_current=True)

        screen = client.get(SELECT_PATH)
        confirm = choose(client, Y)

        assert screen.status_code == 302 and location_path(screen) == "/lecture"
        assert confirm.status_code == 302 and location_path(confirm) == "/lecture"
        assert lectures_of(tmp_path, PID) == [X]
        assert shown_lecture(client.get("/lecture").get_data(as_text=True)) == X


# ---------------------------------------------------------------- AC3 回の終了は終了ボタンだけ


class TestAc3RoundEndsOnlyByEndButton:
    @pytest.mark.parametrize("with_message", [True, False], ids=["with-message", "zero-messages"])
    def test_ac3_page_leave_keeps_the_round_and_end_button_ends_it(
        self, env, with_message
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC3
        app, _llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [], X)
        if with_message:
            assert send_chat(client, "1本目の質問").status_code == 200

        leave = save_dialog_log(client, "page_leave")
        assert leave.status_code == 200, leave.get_data(as_text=True)
        page = client.get("/lecture")
        assert page.status_code == 200
        assert shown_lecture(page.get_data(as_text=True)) == X

        finish_round(client)

        for path in ("/", "/lecture", "/reflect"):
            response = client.get(path)
            assert is_selection_redirect(response), (
                path, response.status_code, response.headers.get("Location")
            )
        assert lectures_of(tmp_path, PID) == [X]


# ---------------------------------------------------------------- AC4 回の終了は取り消されない


class TestAc4FinishedRoundIsFinal:
    @pytest.mark.parametrize("value", [..., X], ids=["without-lecture-id", "with-X"])
    def test_ac4_page_leave_and_chat_after_the_end_are_409_and_change_nothing(
        self, env, value
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC4
        app, llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [], X)
        assert send_chat(client, "1本目の質問").status_code == 200
        finish_round(client)
        before = dump_databases(tmp_path)
        llm_before = _llm_calls(llm)

        leave = save_dialog_log(client, "page_leave", value)
        chat = send_chat(client, "終えた回への追加の質問", value)

        assert leave.status_code == 409, leave.get_data(as_text=True)
        assert chat.status_code == 409, chat.get_data(as_text=True)
        assert dump_databases(tmp_path) == before
        assert [r["end_method"] for r in tutor_rows(tmp_path, "SELECT end_method FROM dialog_logs")] == [
            "end_button"
        ]
        assert _llm_calls(llm) == llm_before
        assert is_selection_redirect(client.get("/lecture"))


# ---------------------------------------------------------------- AC5 2本目の選択肢


class TestAc5SecondOptions:
    def test_ac5_second_selection_screen_lists_the_catalog_without_the_finished_lecture(
        self, env
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC5(「2本目 / 3本」の表示は PBI-B)
        app, _llm, _tmp = env
        client = app.test_client()
        build_progress(client, PID, [X])

        response = client.get(SELECT_PATH)

        assert response.status_code == 200
        values = option_values(response.get_data(as_text=True))
        assert values == option_lectures_expected([X])
        assert X not in values


# ---------------------------------------------------------------- AC6 重複の拒否


class TestAc6DuplicateRejected:
    @pytest.mark.parametrize("path", [SELECT_PATH, CONFIRM_PATH], ids=["confirmation", "confirm"])
    def test_ac6_finished_lecture_is_400_and_adds_no_session(self, env, path) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC6(確定の前の確認の操作を含む)
        app, _llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [X])
        before = dump_databases(tmp_path)

        response = client.post(path, data={"lecture_id": X})

        assert response.status_code == 400, response.get_data(as_text=True)[:200]
        assert dump_databases(tmp_path) == before
        assert lectures_of(tmp_path, PID) == [X]

    @pytest.mark.parametrize(
        "data",
        [{"lecture_id": "lecture-9"}, {"lecture_id": ""}, {}],
        ids=["not-in-catalog", "empty", "missing"],
    )
    def test_ac6_invalid_confirm_in_the_second_round_is_400_and_saves_nothing(
        self, env, data
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC6(#34 の AC5 と同じ)
        app, _llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [X])
        before = dump_databases(tmp_path)

        response = client.post(CONFIRM_PATH, data=data)

        assert response.status_code == 400
        assert dump_databases(tmp_path) == before
        assert lectures_of(tmp_path, PID) == [X]


# ---------------------------------------------------------------- AC7 2本目の確定


class TestAc7SecondConfirm:
    def test_ac7_confirming_y_after_x_creates_the_second_session_and_double_submit_keeps_two(
        self, env
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC7
        app, _llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [X])
        next_second()

        response = choose(client, Y)

        assert response.status_code == 302 and location_path(response) == "/lecture"
        assert lectures_of(tmp_path, PID) == sorted([X, Y])
        page = client.get("/lecture")
        assert page.status_code == 200
        assert shown_lecture(page.get_data(as_text=True)) == Y

        again = choose(client, Y)

        assert again.status_code == 302 and location_path(again) == "/lecture"
        assert lectures_of(tmp_path, PID) == sorted([X, Y])
        assert shown_lecture(client.get("/lecture").get_data(as_text=True)) == Y


# ---------------------------------------------------------------- AC8 3本目と全体の終了


class TestAc8ThirdAndFinished:
    def test_ac8_third_options_exclude_x_and_y(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC8(選択肢。「3本目 / 3本」の表示は PBI-B)
        app, _llm, _tmp = env
        client = app.test_client()
        build_progress(client, PID, [X, Y])

        response = client.get(SELECT_PATH)

        assert response.status_code == 200
        assert option_values(response.get_data(as_text=True)) == option_lectures_expected([X, Y])

    def test_ac8_after_the_third_round_every_screen_goes_to_the_finished_screen(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC8(全体の終了の画面の URL は共有IF。
        # 「`/` の移動先」を全体の終了の画面とし、既知の画面でないこと・他と同じであることを見る)
        app, _llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [X, Y, Z])
        assert lectures_of(tmp_path, PID) == sorted([X, Y, Z])

        end_path = end_screen_path(client)
        for path in ("/lecture", "/reflect", SELECT_PATH):
            response = client.get(path)
            assert response.status_code == 302, (path, response.status_code)
            assert location_path(response) == end_path, (path, response.headers.get("Location"))
        end_page = client.get(end_path)
        assert end_page.status_code == 200
        assert option_values(end_page.get_data(as_text=True)) == [], "全体の終了の画面に選択肢がある"

        # ログイン後の移動先(ログアウトして同じクライアント、別のクライアント)
        assert client.post("/logout").status_code == 302
        for browser in (client, app.test_client()):
            landed = login_follow(browser, PID)
            assert landed.request.path == end_path and landed.status_code == 200

    def test_ac8_confirming_another_lecture_after_the_end_adds_no_session(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC8(それ以上増えない)・What 2節(状態の移動先へ 302)
        app, _llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [X, Y, Z])
        end_path = end_screen_path(client)
        before = dump_databases(tmp_path)

        response = choose(client, W)

        assert response.status_code == 302 and location_path(response) == end_path
        assert dump_databases(tmp_path) == before
        assert lectures_of(tmp_path, PID) == sorted([X, Y, Z])


# ---------------------------------------------------------------- AC9 全体の終了の後の API


class TestAc9ApisAfterFinished:
    @pytest.mark.parametrize("value", [..., X, Y, Z], ids=["omitted", "X", "Y", "Z"])
    def test_ac9_six_apis_are_409_and_change_nothing(self, env, value) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC9
        app, llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [X, Y, Z])
        before = dump_databases(tmp_path)
        llm_before = _llm_calls(llm)

        statuses = {api: call_api(client, api, PID, Z, value).status_code for api in SIX_APIS}

        assert statuses == {api: 409 for api in SIX_APIS}
        assert dump_databases(tmp_path) == before
        assert _llm_calls(llm) == llm_before


# ---------------------------------------------------------------- AC10 選択待ちの API


def _waiting(client, n: int) -> None:
    """n本目の選択待ちにする(1本目は何も選んでいない)。"""
    build_progress(client, PID, [X, Y][: n - 1])


class TestAc10ApisWhileWaiting:
    @pytest.mark.parametrize("n", [1, 2, 3])
    def test_ac10_six_apis_are_409_and_change_nothing(self, env, n) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC10
        app, llm, tmp_path = env
        client = app.test_client()
        _waiting(client, n)
        assert is_selection_redirect(client.get("/lecture")), "準備: 選択待ちになっていない"
        before = dump_databases(tmp_path)
        llm_before = _llm_calls(llm)

        statuses = {api: call_api(client, api, PID, X).status_code for api in SIX_APIS}

        assert statuses == {api: 409 for api in SIX_APIS}
        assert dump_databases(tmp_path) == before
        assert _llm_calls(llm) == llm_before

    @pytest.mark.parametrize("n", [1, 2, 3])
    def test_ac10_not_logged_in_is_401_not_409(self, env, n) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC10(#30 のとおり 401)
        app, _llm, tmp_path = env
        _waiting(app.test_client(), n)
        anonymous = app.test_client()
        before = dump_databases(tmp_path)

        statuses = {api: call_api(anonymous, api, PID, X).status_code for api in SIX_APIS}

        assert statuses == {api: 401 for api in SIX_APIS}
        assert dump_databases(tmp_path) == before

    @pytest.mark.parametrize("n", [1, 2, 3])
    def test_ac10_another_participants_id_is_403_not_409(self, env, n) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC10(#30 のとおり 403)
        app, llm, tmp_path = env
        client = app.test_client()
        _waiting(client, n)
        before = dump_databases(tmp_path)

        statuses = {api: call_api(client, api, OTHER_PID, X).status_code for api in SIX_APIS}

        assert statuses == {api: 403 for api in SIX_APIS}
        assert dump_databases(tmp_path) == before
        assert len(llm.generate_calls) == 0
