# 仕様: docs/spec/multi-video-learning.md#受入基準 (PBI #56 PBI-A) AC17〜23(C. 中断と再開、D. 今の回の講義の一貫、E. スキーマ)
"""1人3本の動画の学習の、再開・今の回の講義の一貫・AI の文脈・対話ログ・協力者ごとの独立・スキーマを、
Flask のテストクライアント(一時ディレクトリの DB、偽の LLM)で確かめる。

状態は HTTP の操作だけで作る(tests/multi_video_helpers.py)。
PBI-A の範囲外(PBI-B): 選び直し(AC17 の「選び直しの導線」、AC19 の「選び直した後」、AC22 の「B の選び直し」)。
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
    cue_text_at,
    end_screen_path,
    finish_round,
    lectures_of,
    login_follow,
    next_second,
    option_lectures_expected,
    outline_titles,
    quiz_question_texts,
    record_quiz,
    record_viewing,
    schema_of,
    send_chat,
    session_id_of,
    shown_lecture,
    tutor_rows,
)
from tests.selection_helpers import (
    SELECT_PATH,
    all_lecture_ids,
    embedded_reflect_lecture_id,
    is_selection_redirect,
    login_unselected,
    option_values,
)

PID = "P02"
RESEARCHER = ("researcher", "s3cret-pass")
POSITION_SEC = 15
BASELINE = Path(__file__).resolve().parent / "data" / "multi_video_schema_baseline.json"


def _basic(user: str, password: str) -> dict[str, str]:
    raw = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {raw}"}


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("RESEARCHER_BASIC_AUTH_USER", RESEARCHER[0])
    monkeypatch.setenv("RESEARCHER_BASIC_AUTH_PASSWORD", RESEARCHER[1])
    app, llm = build_app(monkeypatch, tmp_path)
    return app, llm, tmp_path


def _llm_calls(llm) -> tuple[int, int]:
    return len(llm.generate_calls), len(llm.generate_json_calls)


def _all_prompts(llm) -> str:
    return "\n".join(llm.generate_calls + [p for p, _hint in llm.generate_json_calls])


# ---------------------------------------------------------------- AC17 続きから再開

# 状態 → (終えた回, 今の回, 今の回の記録)
RESUME_STATES = {
    "round1-no-record": ([], X, False),
    "round1-recorded": ([], X, True),
    "round2-waiting": ([X], None, False),
    "round2-learning": ([X], Y, False),
    "finished": ([X, Y, Z], None, False),
}
INTERRUPTIONS = ["logout-relogin", "another-client", "login-expired"]


def _lecture_result(response) -> tuple:
    """/lecture の結果(状態コード、移動先、表示している講義)。"""
    if response.status_code == 302:
        return (302, location_path(response), None)
    return (response.status_code, None, shown_lecture(response.get_data(as_text=True)))


class TestAc17Resume:
    @pytest.mark.parametrize("interruption", INTERRUPTIONS)
    @pytest.mark.parametrize("state", list(RESUME_STATES))
    def test_ac17_landing_and_lecture_are_the_same_after_resuming(
        self, monkeypatch, tmp_path, state, interruption
    ) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC17(時刻を進める。選び直しの導線の有無は PBI-B)
        now = [datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc)]
        app, _llm = build_app(monkeypatch, tmp_path, clock=lambda: now[0])
        client = app.test_client()
        finished, current, record = RESUME_STATES[state]
        build_progress(client, PID, finished, current, record_current=record)
        if state == "round2-learning":
            # 2本目(Y)の記録。X の回の記録(play)と区別できる種類にする
            assert record_viewing(client, "pause").status_code == 201
        before_home = client.get("/", follow_redirects=True)
        before_lecture = _lecture_result(client.get("/lecture"))

        if interruption == "logout-relogin":
            assert client.post("/logout").status_code == 302
            browser = client
        elif interruption == "another-client":
            browser = app.test_client()
        else:
            now[0] += timedelta(hours=13)
            expired = client.get("/lecture")
            assert expired.status_code == 302 and location_path(expired) == "/login"
            browser = client
        landed = login_follow(browser, PID)
        after_lecture = _lecture_result(browser.get("/lecture"))

        # 中断の前と同じ
        assert landed.status_code == 200
        assert landed.request.path == before_home.request.path
        assert after_lecture == before_lecture
        # 状態ごとの期待(仕様の AC17 の各状態)
        if current is not None:
            assert landed.request.path == "/lecture"
            assert after_lecture == (200, None, current)
        elif state == "round2-waiting":
            assert landed.request.path == SELECT_PATH
            assert option_values(landed.get_data(as_text=True)) == option_lectures_expected([X])
            assert after_lecture == (302, SELECT_PATH, None)
        else:
            end_path = end_screen_path(browser)
            assert landed.request.path == end_path
            assert after_lecture == (302, end_path, None)
        if state == "round2-learning":
            lad = browser.get(f"/api/participants/{PID}/lad")
            assert lad.status_code == 200
            counts = lad.get_json()["action_counts"]
            assert counts.get("pause") == 1, counts
            assert not counts.get("play"), f"X の回の play が LAD に混ざっている: {counts}"


# ---------------------------------------------------------------- AC18 記録と LAD は今の回


class TestAc18RecordsAndLadAreTheCurrentRound:
    def test_ac18_records_go_to_y_and_lad_and_last_updated_show_only_y(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC18
        app, _llm, tmp_path = env
        client = app.test_client()
        login_unselected(client, PID)
        confirm_round(client, X)
        assert record_viewing(client, "play").status_code == 201
        assert record_quiz(client, X).status_code == 201
        finish_round(client)
        next_second()
        confirm_round(client, Y)
        x_id, y_id = session_id_of(tmp_path, PID, X), session_id_of(tmp_path, PID, Y)

        # 選んだ直後: Y の記録はまだないので、LAD・最終更新は空(X の記録を含まない)
        lad = client.get(f"/api/participants/{PID}/lad")
        updated = client.get(f"/api/last-updated?participant_id={PID}")
        assert lad.status_code == 200 and updated.status_code == 200
        assert not any(lad.get_json()["action_counts"].values()), lad.get_json()["action_counts"]
        assert lad.get_json()["quiz_results"] == []
        assert lad.get_json()["content_updated_at"] is None
        assert updated.get_json() == {"last_updated": None}

        for field in (..., Y):
            viewing = record_viewing(client, "pause", field)
            quiz = record_quiz(client, Y, field)
            assert viewing.status_code == 201, viewing.get_data(as_text=True)
            assert quiz.status_code == 201, quiz.get_data(as_text=True)

        assert count_records(tmp_path, "viewing_logs", y_id) == 2
        assert count_records(tmp_path, "quiz_attempts", y_id) == 2
        assert count_records(tmp_path, "viewing_logs", x_id) == 1
        assert count_records(tmp_path, "quiz_attempts", x_id) == 1
        data = client.get(f"/api/participants/{PID}/lad").get_json()
        assert data["action_counts"].get("pause") == 2
        assert not data["action_counts"].get("play"), "X の視聴ログが LAD に混ざっている"
        assert data["quiz_results"], "Y の小テストが LAD にない"
        y_texts, x_only = quiz_question_texts(Y), quiz_question_texts(X) - quiz_question_texts(Y)
        assert all(row["question_text"] in y_texts for row in data["quiz_results"])
        assert not any(row["question_text"] in x_only for row in data["quiz_results"])
        assert data["content_updated_at"] is not None
        assert client.get(f"/api/last-updated?participant_id={PID}").get_json()["last_updated"] is not None


# ---------------------------------------------------------------- AC19 終えた回の講義の指定は拒否


def _second_round(env):
    """1本目(X)を記録・対話つきで終え、2本目(Y)の学習中(Y にも記録あり)にする。

    準備の失敗をテストの失敗(FAILED)として報告するため、フィクスチャではなくテストの中で呼ぶ。
    """
    app, llm, tmp_path = env
    client = app.test_client()
    login_unselected(client, PID)
    confirm_round(client, X)
    assert record_viewing(client, "play").status_code == 201
    assert send_chat(client, "1本目の質問").status_code == 200
    finish_round(client)
    next_second()
    confirm_round(client, Y)
    assert record_viewing(client, "play").status_code == 201
    return client, llm, tmp_path


class TestAc19FinishedLectureIsRejected:
    def test_ac19_six_apis_with_x_are_403_and_change_nothing(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC19(選び直した後の X の指定は PBI-B)
        client, llm, tmp_path = _second_round(env)
        before = dump_databases(tmp_path)
        llm_before = _llm_calls(llm)

        statuses = {api: call_api(client, api, PID, X, X).status_code for api in SIX_APIS}

        assert statuses == {api: 403 for api in SIX_APIS}
        assert dump_databases(tmp_path) == before
        assert _llm_calls(llm) == llm_before

    def test_ac19_screens_with_x(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC19・What 4節(画面は今の回の講義)
        client, _llm, _tmp = _second_round(env)

        assert client.get(f"/reflect?lecture_id={X}").status_code == 403
        lecture = client.get(f"/lecture?lecture_id={X}")
        assert lecture.status_code == 200
        assert shown_lecture(lecture.get_data(as_text=True)) == Y
        reflect = client.get("/reflect")
        assert reflect.status_code == 200
        assert embedded_reflect_lecture_id(reflect.get_data(as_text=True)) == Y


# ---------------------------------------------------------------- AC20 AI の文脈は今の回だけ


class TestAc20ChatContextIsTheCurrentRound:
    def test_ac20_second_round_chat_uses_a_new_session_and_only_y_context(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC20(講義ごとに区別できる文字列で判定)
        app, llm, tmp_path = env
        client = app.test_client()
        login_unselected(client, PID)
        confirm_round(client, X)
        assert record_viewing(client, "play", current_time=POSITION_SEC).status_code == 201
        x_message, x_reply = "1本目だけの質問-MARK-X-7c1e", "1本目だけの応答-MARK-X-7c1e"
        llm.set_response(x_reply)
        first = send_chat(client, x_message)
        assert first.status_code == 200
        x_tutor_session = first.get_json()["session_id"]
        finish_round(client)
        next_second()
        confirm_round(client, Y)
        assert record_viewing(client, "play", current_time=POSITION_SEC).status_code == 201
        llm.set_response("2本目の応答")
        llm.generate_calls.clear()
        llm.generate_json_calls.clear()

        second = send_chat(client, "2本目の質問")

        assert second.status_code == 200, second.get_data(as_text=True)
        y_tutor_session = second.get_json()["session_id"]
        assert y_tutor_session != x_tutor_session
        linked = {
            r["id"]: r["learning_session_id"]
            for r in tutor_rows(tmp_path, "SELECT id, learning_session_id FROM sessions")
        }
        assert linked[y_tutor_session] == session_id_of(tmp_path, PID, Y)
        assert linked[x_tutor_session] == session_id_of(tmp_path, PID, X)
        assert llm.generate_calls, "偽の LLM が呼ばれていない"
        prompt = llm.generate_calls[-1]
        everything = _all_prompts(llm)
        own_text, own_titles = cue_text_at(Y, POSITION_SEC), outline_titles(Y)
        assert own_text in prompt, "Y の字幕のその位置の文がプロンプトにない"
        for title in own_titles:
            assert title in prompt, f"Y の講義情報の章の題 {title!r} がプロンプトにない"
        x_text = cue_text_at(X, POSITION_SEC)
        if x_text != own_text and x_text not in own_text and len(x_text) >= 6:
            assert x_text not in everything, "X の字幕がプロンプトに入っている"
        for title in outline_titles(X):
            if title not in own_titles and title not in own_text:
                assert title not in everything, f"X の講義情報 {title!r} がプロンプトに入っている"
        assert x_message not in everything, "1本目の発言がプロンプトに入っている"
        assert x_reply not in everything, "1本目の AI の応答がプロンプトに入っている"


# ---------------------------------------------------------------- AC21 対話ログは回ごと


class TestAc21DialogLogsPerRound:
    def test_ac21_three_rounds_give_three_logs_and_three_downloaded_sessions(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC21
        from tests.test_api.test_research_dialog_download_api import TOP_KEYS

        app, _llm, tmp_path = env
        client = app.test_client()
        login_unselected(client, PID)
        texts = {}
        for index, lecture_id in enumerate((X, Y, Z)):
            if index > 0:
                next_second()
            confirm_round(client, lecture_id)
            texts[lecture_id] = f"{lecture_id} の回の質問"
            assert send_chat(client, texts[lecture_id]).status_code == 200
            finish_round(client)

        rows = tutor_rows(tmp_path, "SELECT * FROM dialog_logs WHERE participant_id=?", (PID,))
        assert len(rows) == 3
        by_lecture = {row["lecture_id"]: row for row in rows}
        assert set(by_lecture) == {X, Y, Z}
        for lecture_id, row in by_lecture.items():
            log = json.loads(row["log_json"])
            assert row["learning_session_id"] == session_id_of(tmp_path, PID, lecture_id)
            assert log["lecture_id"] == lecture_id
            assert log["learning_session_id"] == row["learning_session_id"]
            assert row["end_method"] == "end_button"
            users = [m["content"] for m in log["messages"] if m["role"] == "user"]
            assert users == [texts[lecture_id]], (lecture_id, users)

        response = client.get(
            f"/research/participants/{PID}/dialog-logs", headers=_basic(*RESEARCHER)
        )
        assert response.status_code == 200
        parsed = json.loads(response.get_data(as_text=True), object_pairs_hook=lambda p: p)
        assert len(parsed) == 3
        assert all([k for k, _ in item] == TOP_KEYS for item in parsed)
        body = response.get_json()
        assert [item["lecture_id"] for item in body] == [X, Y, Z]
        assert all(item["format_version"] == 1 for item in body)
        for item in body:
            assert item["learning_session_id"] == session_id_of(tmp_path, PID, item["lecture_id"])
            assert [m["content"] for m in item["messages"] if m["role"] == "user"] == [
                texts[item["lecture_id"]]
            ]


# ---------------------------------------------------------------- AC22 協力者ごとの独立


class TestAc22Independent:
    def test_ac22_participants_in_different_rounds_do_not_affect_each_other(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC22(B の選び直しは PBI-B)
        app, _llm, tmp_path = env
        a, b, c = app.test_client(), app.test_client(), app.test_client()
        build_progress(a, "A", [X], Y, record_current=True)  # A: 2本目(Y)の学習中
        build_progress(b, "B", [], Y)  # B: 1本目(Y。A の2本目と同じ講義、異なる回)
        build_progress(c, "P03", [], X)  # P03: 1本目(X。A の1本目と同じ講義、同じ回)
        a_y = session_id_of(tmp_path, "A", Y)
        a_lad_before = a.get("/api/participants/A/lad").get_json()

        assert lectures_of(tmp_path, "A") == sorted([X, Y])
        assert lectures_of(tmp_path, "B") == [Y]
        assert lectures_of(tmp_path, "P03") == [X]
        for client, lecture_id in ((a, Y), (b, Y), (c, X)):
            assert shown_lecture(client.get("/lecture").get_data(as_text=True)) == lecture_id

        # B の記録・回の終了は、A の記録・状態・選択肢を変えない
        assert record_viewing(b, "pause").status_code == 201
        assert count_records(tmp_path, "viewing_logs", session_id_of(tmp_path, "B", Y)) == 1
        assert count_records(tmp_path, "viewing_logs", a_y) == 1
        finish_round(b)
        b_options = b.get(SELECT_PATH)
        assert b_options.status_code == 200
        assert option_values(b_options.get_data(as_text=True)) == option_lectures_expected([Y])

        assert shown_lecture(a.get("/lecture").get_data(as_text=True)) == Y
        assert a.get("/api/participants/A/lad").get_json() == a_lad_before
        assert lectures_of(tmp_path, "A") == sorted([X, Y])
        assert shown_lecture(c.get("/lecture").get_data(as_text=True)) == X
        assert is_selection_redirect(b.get("/lecture"))
        # A が2本目を終えると、A の3本目の選択肢は A の終えた回だけを除く(B・P03 の選択によらない)
        finish_round(a)
        a_options = a.get(SELECT_PATH)
        assert a_options.status_code == 200
        assert option_values(a_options.get_data(as_text=True)) == option_lectures_expected([X, Y])
        assert len(all_lecture_ids()) >= 4


# ---------------------------------------------------------------- AC23 スキーマを変えない


class TestAc23SchemaUnchanged:
    def test_ac23_sqlite_master_is_the_same_as_before_the_feature(self, env) -> None:
        # 仕様: docs/spec/multi-video-learning.md#受入基準 AC23
        # 基準: この機能の前のコード(8f097c4 = develop 31d1baf + 仕様)で、1回分の学習(選択・視聴・小テスト・
        # 対話・終了ボタン)の後に取った sqlite_master の内容(tests/test_api/data/multi_video_schema_baseline.json)
        app, _llm, tmp_path = env
        client = app.test_client()
        login_unselected(client, PID)
        for index, lecture_id in enumerate((X, Y, Z)):
            if index > 0:
                next_second()
            confirm_round(client, lecture_id)
            assert record_viewing(client, "play").status_code == 201
            assert record_quiz(client, lecture_id).status_code == 201
            assert send_chat(client, "質問").status_code == 200
            finish_round(client)

        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

        for name in ("learning.db", "tutor.db"):
            assert [list(r) for r in schema_of(tmp_path / name)] == baseline[name], name
