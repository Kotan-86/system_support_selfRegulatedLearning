# 仕様: docs/spec/multi-video-learning.md#受入基準 (PBI #56 PBI-D 選び直し) AC11〜13・15、AC17・19・22 の選び直しの部分
"""回の選び直し(What 8節、Q4・Q16〜Q18)を、Flask のテストクライアント(一時ディレクトリの DB、偽の LLM)で確かめる。

状態は HTTP の操作だけで作る(tests/multi_video_helpers.py)。内部の IF(ポート・ユースケース)は import しない。

【test-writer が置いた前提】
  - 選び直しの確定の送り先は、既存の確定の送り先(POST /select-lecture/confirm、確認の画面は POST /select-lecture)。
    仕様の共有IF「選び直しの確定の送り先」は PBI-A で別の口を作っておらず、8節は「確定の前の確認は2節と同じ」
    と書くため、2節と同じ送り先とした(別の送り先にするなら、テストの変更が要る)。
  - 選び直しの導線は、講義の画面の、選択の画面への <a href>(has_reselect_link)。
  - AC15 の「変えられなくなる条件」の文言は、1つのブロック要素(p、div など)の本文に「再生」「小テスト」「対話」の
    3語がそろうことで判定する(文言そのものは AC24 で PO が決める)。
  - AC13 では、記録の前に選び直しができること(導線がある、選択の画面が 200)を準備として確かめてから記録する。
    「記録で選び直しができなくなる」ことを見るためで、選び直しが最初から無い実装では準備の確認で失敗する。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.login_helpers import build_app, dump_databases, location_path
from tests.multi_video_helpers import (
    SIX_APIS,
    X,
    Y,
    Z,
    build_progress,
    call_api,
    confirm_round,
    count_records,
    finish_round,
    has_reselect_link,
    lectures_of,
    login_follow,
    next_second,
    option_lectures_expected,
    page_text,
    record_quiz,
    record_viewing,
    round_labels,
    save_dialog_log,
    send_chat,
    session_id_of,
    sessions_of,
    shown_lecture,
    text_blocks,
)
from tests.selection_helpers import (
    CONFIRM_PATH,
    SELECT_PATH,
    WARNING_TEXT,
    catalog_lectures,
    choose,
    login_unselected,
    option_values,
)

PID = "P02"
CONDITION_WORDS = ("再生", "小テスト", "対話")


@pytest.fixture
def env(monkeypatch, tmp_path):
    app, llm = build_app(monkeypatch, tmp_path)
    return app, llm, tmp_path


def _llm_calls(llm) -> tuple[int, int]:
    return len(llm.generate_calls), len(llm.generate_json_calls)


def _title_of(lecture_id: str) -> str:
    return next(str(lec.title) for lec in catalog_lectures() if str(lec.id) == lecture_id)


def _lecture_page(client):
    page = client.get("/lecture")
    assert page.status_code == 200, (page.status_code, page.headers.get("Location"))
    return page.get_data(as_text=True)


def _assert_reselectable(client, n: int, current: str, finished: list[str]) -> None:
    """準備の確認: n本目の学習中(current)で、選び直しができる(導線がある、選択の画面が 200)。"""
    html = _lecture_page(client)
    assert shown_lecture(html) == current
    assert has_reselect_link(html), f"準備: 記録の前の {current} の講義の画面に選び直しの導線が無い"
    screen = client.get(SELECT_PATH)
    assert screen.status_code == 200, (
        f"準備: 記録の前の選択の画面が 200 でない: {screen.status_code} {screen.headers.get('Location')}"
    )


def _reselect(client, lecture_id: str):
    """確定の前の確認の操作を経て、選び直しの確定を送る(応答を返す)。"""
    first = client.post(SELECT_PATH, data={"lecture_id": lecture_id})
    assert first.status_code == 200, (
        f"準備: {lecture_id} への選び直しの確定の前の確認が 200 でない: "
        f"{first.status_code} {first.headers.get('Location')}"
    )
    return choose(client, lecture_id)


# ---------------------------------------------------------------- AC11 選び直しの導線と画面


class TestAc11ReselectLinkAndScreen:
    @pytest.mark.parametrize(
        "n, finished, current",
        [pytest.param(1, [], X, id="round1"), pytest.param(2, [X], Y, id="round2")],
    )
    def test_ac11_lecture_has_the_link_and_selection_screen_lists_the_rest(
        self, env, n, finished, current
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC11、What 8節(導線、選択の画面(選び直し))
        app, _llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, finished, current)
        before = dump_databases(tmp_path)

        html = _lecture_page(client)
        screen = client.get(SELECT_PATH)

        assert shown_lecture(html) == current
        assert has_reselect_link(html), f"{n}本目の学習中(記録なし)の講義の画面に選び直しの導線が無い"
        assert screen.status_code == 200, (screen.status_code, screen.headers.get("Location"))
        screen_html = screen.get_data(as_text=True)
        assert round_labels(screen_html) == {n}, (
            f"選び直しの選択の画面に「{n}本目 / 3本」(だけ)が無い: {sorted(round_labels(screen_html))}"
        )
        assert option_values(screen_html) == option_lectures_expected(finished + [current])
        assert dump_databases(tmp_path) == before, "導線・選択の画面を開いただけで DB が変わった"


# ---------------------------------------------------------------- AC12 選び直しの確定


class TestAc12ReselectConfirm:
    def test_ac12a_reselecting_y_in_round1_replaces_x_and_records_go_to_y(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC12 (a)
        app, _llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [], X)

        response = _reselect(client, Y)

        assert response.status_code == 302 and location_path(response) == "/lecture", (
            response.status_code, response.headers.get("Location")
        )
        sessions = sessions_of(tmp_path, PID)
        assert [lec for _sid, lec in sessions] == [Y], f"学習セッションが Y の1つだけでない: {sessions}"
        assert shown_lecture(_lecture_page(client)) == Y

        viewing = record_viewing(client, "play")

        assert viewing.status_code == 201, viewing.get_data(as_text=True)
        assert count_records(tmp_path, "viewing_logs", session_id_of(tmp_path, PID, Y)) == 1

    def _finished_x_and_current(self, env, current: str):
        """1本目(X)を視聴・小テスト・対話つきで終え、2本目の学習中(current、記録なし)にする。"""
        app, llm, tmp_path = env
        client = app.test_client()
        login_unselected(client, PID)
        confirm_round(client, X)
        assert record_viewing(client, "play").status_code == 201
        assert record_quiz(client, X).status_code == 201
        assert send_chat(client, "1本目の質問").status_code == 200
        finish_round(client)
        next_second()
        confirm_round(client, current)
        return client, llm, tmp_path

    def test_ac12b_reselecting_z_in_round2_keeps_x_and_its_records(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC12 (b)、What 8節(終えた回の学習セッションと記録は変わらない)
        client, _llm, tmp_path = self._finished_x_and_current(env, Y)
        x_row = [row for row in sessions_of(tmp_path, PID) if row[1] == X]
        before = dump_databases(tmp_path)

        response = _reselect(client, Z)

        assert response.status_code == 302 and location_path(response) == "/lecture"
        assert lectures_of(tmp_path, PID) == sorted([X, Z])
        assert [row for row in sessions_of(tmp_path, PID) if row[1] == X] == x_row
        after = dump_databases(tmp_path)
        # X の記録(視聴ログ、小テスト)と、tutor.db(対話セッション、発言、対話ログ)は確定の前と同じ。
        # Y には記録がないので、learning.db の学習セッション以外の表と tutor.db は全体が同じになる。
        for table, rows in before["learning"].items():
            if table != "learning_sessions":
                assert after["learning"][table] == rows, f"learning.db の {table} が変わった"
        assert after["tutor"] == before["tutor"], "tutor.db が変わった"
        assert before["learning"]["viewing_logs"] and before["tutor"]["dialog_logs"], "準備: X の記録が無い"
        assert shown_lecture(_lecture_page(client)) == Z

    def test_ac12c_finished_x_is_400_and_current_z_is_302_without_change(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC12 (c)、What 8節
        client, _llm, tmp_path = self._finished_x_and_current(env, Y)
        assert _reselect(client, Z).status_code == 302
        assert lectures_of(tmp_path, PID) == sorted([X, Z]), "準備: Z への選び直しが成立していない"
        before = dump_databases(tmp_path)

        finished_x = client.post(CONFIRM_PATH, data={"lecture_id": X})
        current_z = client.post(CONFIRM_PATH, data={"lecture_id": Z})

        assert finished_x.status_code == 400, finished_x.get_data(as_text=True)[:200]
        assert current_z.status_code == 302 and location_path(current_z) == "/lecture"
        assert dump_databases(tmp_path) == before
        assert shown_lecture(_lecture_page(client)) == Z


# ---------------------------------------------------------------- AC13 記録ができたら選び直せない


def _do_record(client, kind: str):
    if kind.startswith("viewing-"):
        return record_viewing(client, kind.removeprefix("viewing-"))
    if kind == "quiz":
        return record_quiz(client, X)
    if kind == "chat":
        return send_chat(client, "最初の質問")
    return save_dialog_log(client, "page_leave")  # 発言0件の対話ログ(page_leave)


RECORD_KINDS = [
    pytest.param("viewing-play", id="a-play"),
    pytest.param("viewing-pause", id="a-pause"),
    pytest.param("viewing-forward_skip", id="a-forward_skip"),
    pytest.param("viewing-forward_seek", id="a-forward_seek"),
    pytest.param("quiz", id="b-quiz"),
    pytest.param("chat", id="c-chat"),
    pytest.param("dialog-log-page-leave", id="d-zero-message-page-leave"),
]


class TestAc13NoReselectAfterRecord:
    @pytest.mark.parametrize("kind", RECORD_KINDS)
    def test_ac13_after_one_record_the_round_cannot_be_reselected(self, env, kind) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC13、What 8節(選び直せなくなった後)、用語「回の記録」(Q16)
        app, _llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [], X)
        _assert_reselectable(client, 1, X, [])
        recorded = _do_record(client, kind)
        assert recorded.status_code in (200, 201), (
            f"準備: 記録({kind})が成功しない: {recorded.status_code} {recorded.get_data(as_text=True)[:200]}"
        )
        before = dump_databases(tmp_path)

        html = _lecture_page(client)
        screen = client.get(SELECT_PATH)
        confirm = choose(client, Y)

        assert not has_reselect_link(html), f"記録({kind})の後も選び直しの導線がある"
        assert screen.status_code == 302 and location_path(screen) == "/lecture", (
            screen.status_code, screen.headers.get("Location")
        )
        assert confirm.status_code == 302 and location_path(confirm) == "/lecture", (
            confirm.status_code, confirm.headers.get("Location")
        )
        assert dump_databases(tmp_path) == before
        assert lectures_of(tmp_path, PID) == [X]
        assert shown_lecture(_lecture_page(client)) == X


# ---------------------------------------------------------------- AC15 確定の前の確認の表示(条件の文言)


class TestAc15ConfirmConditionText:
    @pytest.mark.parametrize(
        "n, finished, current, chosen",
        [
            pytest.param(1, [], None, X, id="round1"),
            pytest.param(2, [X], None, Y, id="round2"),
            pytest.param(1, [], X, Y, id="round1-reselect"),
        ],
    )
    def test_ac15_confirm_shows_the_condition_and_not_the_34_text(
        self, env, n, finished, current, chosen
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC15、What 2節(Q4 の文言の置き換え)、
        #       What 8節(選び直しの確定の前の確認は2節と同じ)
        app, _llm, tmp_path = env
        client = app.test_client()
        if finished or current:
            build_progress(client, PID, finished, current)
        else:
            login_unselected(client, PID)
        before = sessions_of(tmp_path, PID)

        confirm = client.post(SELECT_PATH, data={"lecture_id": chosen})

        assert confirm.status_code == 200, (confirm.status_code, confirm.headers.get("Location"))
        html = confirm.get_data(as_text=True)
        text = page_text(html)
        assert _title_of(chosen) in text
        assert round_labels(html) == {n}, sorted(round_labels(html))
        condition = [b for b in text_blocks(html) if all(w in b for w in CONDITION_WORDS)]
        assert condition, (
            f"「再生」「小テスト」「対話」を含む変えられなくなる条件の文言が無い。本文: {text[:500]}"
        )
        assert WARNING_TEXT not in text, f"#34 の「{WARNING_TEXT}」が残っている"
        assert sessions_of(tmp_path, PID) == before, "確定の前の確認で学習セッションが変わった"


# ---------------------------------------------------------------- AC17 再開の後の導線の有無


class TestAc17ResumeKeepsTheLink:
    @pytest.mark.parametrize("interruption", ["logout-relogin", "another-client", "login-expired"])
    @pytest.mark.parametrize(
        "record, link", [(False, True), (True, False)], ids=["round1-no-record", "round1-recorded"]
    )
    def test_ac17_link_presence_is_the_same_after_resuming(
        self, monkeypatch, tmp_path, record, link, interruption
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC17(1本目の学習中の記録なしは導線を含み、記録ありは含まない)
        now = [datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc)]
        app, _llm = build_app(monkeypatch, tmp_path, clock=lambda: now[0])
        client = app.test_client()
        build_progress(client, PID, [], X, record_current=record)
        assert has_reselect_link(_lecture_page(client)) is link, "中断の前の導線の有無"

        if interruption == "logout-relogin":
            assert client.post("/logout").status_code == 302
            browser = client
        elif interruption == "another-client":
            browser = app.test_client()
        else:
            now[0] += timedelta(hours=13)
            assert location_path(client.get("/lecture")) == "/login"
            browser = client
        landed = login_follow(browser, PID)

        assert landed.request.path == "/lecture" and landed.status_code == 200
        html = landed.get_data(as_text=True)
        assert shown_lecture(html) == X
        assert has_reselect_link(html) is link, f"再開の後の導線の有無が中断の前({link})と異なる"


# ---------------------------------------------------------------- AC19 選び直しの前の講義の指定は拒否


class TestAc19LectureBeforeReselectIsRejected:
    def test_ac19_six_apis_with_the_lecture_before_reselect_are_403(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC19(1本目の学習中に X から Y へ選び直した後)、What 4節
        app, llm, tmp_path = env
        client = app.test_client()
        build_progress(client, PID, [], X)
        assert _reselect(client, Y).status_code == 302
        assert lectures_of(tmp_path, PID) == [Y], "準備: Y への選び直しが成立していない"
        before = dump_databases(tmp_path)
        llm_before = _llm_calls(llm)

        statuses = {api: call_api(client, api, PID, X, X).status_code for api in SIX_APIS}

        assert statuses == {api: 403 for api in SIX_APIS}
        assert dump_databases(tmp_path) == before
        assert _llm_calls(llm) == llm_before


# ---------------------------------------------------------------- AC22 B の選び直しは A を変えない


class TestAc22ReselectIsPerParticipant:
    def test_ac22_b_reselect_does_not_change_a(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC22(B の選び直しは A の学習セッションを変えない)
        app, _llm, tmp_path = env
        a, b = app.test_client(), app.test_client()
        build_progress(a, "A", [X], Y, record_current=True)  # A: 2本目(Y)の学習中
        build_progress(b, "B", [], X)  # B: 1本目(X)の学習中、記録なし
        a_sessions = sessions_of(tmp_path, "A")
        a_lad = a.get("/api/participants/A/lad").get_json()

        response = _reselect(b, Y)  # A の今の回と同じ講義へ(異なる回)

        assert response.status_code == 302 and location_path(response) == "/lecture"
        assert lectures_of(tmp_path, "B") == [Y]
        assert sessions_of(tmp_path, "A") == a_sessions
        assert a.get("/api/participants/A/lad").get_json() == a_lad
        assert shown_lecture(_lecture_page(a)) == Y
        assert shown_lecture(_lecture_page(b)) == Y

