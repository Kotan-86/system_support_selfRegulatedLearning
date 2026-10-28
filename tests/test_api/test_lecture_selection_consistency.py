# 仕様: docs/spec/lecture-selection.md#受入基準 (PBI #34) AC10〜14・17(C. 講義 ID の一貫)
"""選んだ講義で、視聴ログ・小テスト・LAD・最終更新・AI 対話・対話ログが一貫して動くこと、
API の lecture_id の扱い(403・400・409、検査の順序)を、Flask のテストクライアント(偽の LLM)で確かめる。

講義は、画面の確定の操作(POST /select-lecture/confirm)で選ぶ(tests/selection_helpers.py)。
AC10・12・13 は、lecture_id を含めない形と、画面が送る形(lecture_id に選択した講義を付けた形)の両方で確かめる(DR-002)。
"""
from __future__ import annotations

import base64
import importlib
import json
import sqlite3
from pathlib import Path
from urllib.parse import quote

import pytest

from interfaces.tutoring.srt import parse_srt_file
from tests.login_helpers import build_app, dump_databases
from tests.selection_helpers import (
    all_lecture_ids,
    count_rows,
    learning_sessions,
    login_and_choose,
    login_unselected,
    quiz_payload_for,
    viewing_body,
)

ROOT = Path(__file__).resolve().parent.parent.parent
ALL_IDS = all_lecture_ids()
PID = "P02"
OTHER_PID = "A"
POSITION_SEC = 15
FORMS = ["without-lecture-id", "with-lecture-id"]
RESEARCHER = ("researcher", "s3cret-pass")


def _form_value(form: str, lecture_id: str):
    """form が with-lecture-id なら lecture_id を、そうでなければ「含めない」を表す ... を返す。"""
    return lecture_id if form == "with-lecture-id" else ...


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("RESEARCHER_BASIC_AUTH_USER", RESEARCHER[0])
    monkeypatch.setenv("RESEARCHER_BASIC_AUTH_PASSWORD", RESEARCHER[1])
    app, llm = build_app(monkeypatch, tmp_path)
    return app, llm, tmp_path


def _selected(app, lecture_id: str, participant_id: str = PID):
    client = app.test_client()
    login_and_choose(client, participant_id, lecture_id)
    return client


def _chat_body(message: str, lecture_field=...) -> dict:
    body = {"message": message, "participant_id": PID}
    if lecture_field is not ...:
        body["lecture_id"] = lecture_field
    return body


def _dialog_body(end_method: str, lecture_field=...) -> dict:
    body = {"participant_id": PID, "end_method": end_method}
    if lecture_field is not ...:
        body["lecture_id"] = lecture_field
    return body


def _session_ids_of_recorded(tmp_path: Path, table: str) -> list[tuple[str, str]]:
    """viewing_logs / quiz_attempts の各行の (学習者, 講義)。"""
    conn = sqlite3.connect(str(tmp_path / "learning.db"))
    try:
        return sorted(
            (r[0], r[1])
            for r in conn.execute(
                f"SELECT s.learner_id, s.lecture_id FROM {table} t "
                "JOIN learning_sessions s ON s.id = t.learning_session_id"
            )
        )
    finally:
        conn.close()


# ---------------------------------------------------------------- AC10 学習データの記録


class TestAc10Recording:
    @pytest.mark.parametrize("form", FORMS)
    @pytest.mark.parametrize("lecture_id", ALL_IDS)
    def test_ac10_viewing_and_quiz_go_to_the_selected_learning_session(
        self, env, lecture_id, form
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC10(カタログの全講義 × 2つの形)
        app, _llm, tmp_path = env
        client = _selected(app, lecture_id)
        field = _form_value(form, lecture_id)

        viewing = client.post("/api/viewing-log", json=viewing_body(field))
        quiz = client.post("/api/quiz-attempts", json=quiz_payload_for(lecture_id, field))

        assert viewing.status_code == 201, viewing.get_data(as_text=True)
        assert quiz.status_code == 201, quiz.get_data(as_text=True)
        assert learning_sessions(tmp_path) == [(PID, lecture_id)]
        assert _session_ids_of_recorded(tmp_path, "viewing_logs") == [(PID, lecture_id)]
        assert _session_ids_of_recorded(tmp_path, "quiz_attempts") == [(PID, lecture_id)]


# ---------------------------------------------------------------- AC11 LAD と最終更新


class TestAc11LadAndLastUpdated:
    @pytest.mark.parametrize("lecture_id", ALL_IDS)
    def test_ac11_empty_right_after_selection_then_the_selected_lectures_records(
        self, env, lecture_id
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC11
        app, _llm, tmp_path = env
        client = _selected(app, lecture_id)

        lad = client.get(f"/api/participants/{PID}/lad")
        updated = client.get(f"/api/last-updated?participant_id={PID}")

        assert lad.status_code == 200 and updated.status_code == 200
        data = lad.get_json()
        assert not any(data["action_counts"].values())
        assert data["quiz_results"] == []
        assert data["content_updated_at"] is None
        assert updated.get_json() == {"last_updated": None}

        payload = quiz_payload_for(lecture_id)
        assert client.post("/api/viewing-log", json=viewing_body()).status_code == 201
        assert client.post("/api/quiz-attempts", json=payload).status_code == 201

        lad = client.get(f"/api/participants/{PID}/lad").get_json()
        updated = client.get(f"/api/last-updated?participant_id={PID}").get_json()
        assert lad["action_counts"].get("play") == 1
        assert len(lad["quiz_results"]) == len(payload["answers"])
        assert lad["content_updated_at"] is not None
        assert updated["last_updated"] is not None
        assert learning_sessions(tmp_path) == [(PID, lecture_id)]  # 記録は選択した講義の学習セッション


# ---------------------------------------------------------------- AC12 AI 対話


def _cue_text_at(lecture_id: str, position: float) -> str:
    path = ROOT / "lectures" / lecture_id / "subtitles.srt"
    assert path.is_file(), f"{path} が無い"
    segments = parse_srt_file(path)
    for seg in segments:
        if seg["start_sec"] <= position <= seg["end_sec"]:
            return seg["text"].strip()
    for seg in segments:
        if seg["start_sec"] >= position:
            return seg["text"].strip()
    raise AssertionError("位置に対応するキューが無い")


def _outline_titles(lecture_id: str) -> list[str]:
    number = lecture_id.split("-")[1]
    module = importlib.import_module(
        f"framework_drivers.db.learning.lecture_outlines.lecture_{number}"
    )
    return [section.title for section in module.build_lecture_outline().sections]


class TestAc12Chat:
    @pytest.mark.parametrize("form", FORMS)
    @pytest.mark.parametrize("lecture_id", ALL_IDS)
    def test_ac12_chat_uses_the_selected_lectures_session_and_context(
        self, env, lecture_id, form
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC12(LLM は偽物。渡された内容を観察する)
        app, llm, tmp_path = env
        client = _selected(app, lecture_id)
        field = _form_value(form, lecture_id)
        assert client.post(
            "/api/viewing-log", json=viewing_body(field, current_time=POSITION_SEC)
        ).status_code == 201
        llm.generate_calls.clear()

        response = client.post("/chat", json=_chat_body("このあたりの説明がわかりません", field))

        assert response.status_code == 200, response.get_data(as_text=True)
        # 対話セッションは (その ID, X) の学習セッションに紐づく
        learning = sqlite3.connect(str(tmp_path / "learning.db"))
        tutor = sqlite3.connect(str(tmp_path / "tutor.db"))
        try:
            ls_id = learning.execute(
                "SELECT id FROM learning_sessions WHERE learner_id=? AND lecture_id=?", (PID, lecture_id)
            ).fetchone()[0]
            linked = [r[0] for r in tutor.execute("SELECT learning_session_id FROM sessions")]
        finally:
            learning.close()
            tutor.close()
        assert linked == [ls_id]
        assert learning_sessions(tmp_path) == [(PID, lecture_id)]
        # AI に渡す内容: X の講義の文脈があり、X 以外の講義の文脈がない
        assert llm.generate_calls, "偽の LLM が呼ばれていない"
        prompt = llm.generate_calls[-1]
        own_text = _cue_text_at(lecture_id, POSITION_SEC)
        own_titles = _outline_titles(lecture_id)
        assert own_text in prompt, "X の字幕のその位置の文がプロンプトにない"
        for title in own_titles:
            assert title in prompt, f"X の講義情報の章の題 {title!r} がプロンプトにない"
        for other in ALL_IDS:
            if other == lecture_id:
                continue
            other_text = _cue_text_at(other, POSITION_SEC)
            if other_text != own_text and other_text not in own_text and len(other_text) >= 6:
                assert other_text not in prompt, f"{other} の字幕がプロンプトに入っている"
            for title in _outline_titles(other):
                if title not in own_titles and title not in own_text:
                    assert title not in prompt, f"{other} の講義情報 {title!r} がプロンプトに入っている"


# ---------------------------------------------------------------- AC13 対話ログ


def _basic(user: str, password: str) -> dict[str, str]:
    raw = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {raw}"}


class TestAc13DialogLog:
    @pytest.mark.parametrize("end_method", ["end_button", "page_leave"])
    @pytest.mark.parametrize("form", FORMS)
    @pytest.mark.parametrize("lecture_id", ALL_IDS)
    def test_ac13_saved_log_has_the_selected_lecture_and_the_chat_session(
        self, env, lecture_id, form, end_method
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC13(AC12 に続けて。2つの形 × 2つの終了方法)
        app, _llm, tmp_path = env
        client = _selected(app, lecture_id)
        field = _form_value(form, lecture_id)
        assert client.post("/chat", json=_chat_body("質問1", field)).status_code == 200
        tutor = sqlite3.connect(str(tmp_path / "tutor.db"))
        try:
            chat_session = [r[0] for r in tutor.execute("SELECT id FROM sessions")]
        finally:
            tutor.close()
        assert len(chat_session) == 1

        response = client.post("/api/dialog-log", json=_dialog_body(end_method, field))

        assert response.status_code == 200, response.get_data(as_text=True)
        assert response.get_json()["tutor_session_id"] == chat_session[0]
        tutor = sqlite3.connect(str(tmp_path / "tutor.db"))
        tutor.row_factory = sqlite3.Row
        try:
            rows = tutor.execute("SELECT * FROM dialog_logs").fetchall()
        finally:
            tutor.close()
        assert len(rows) == 1
        log = json.loads(rows[0]["log_json"])
        assert rows[0]["lecture_id"] == lecture_id == log["lecture_id"]
        assert rows[0]["session_id"] == chat_session[0] == log["tutor_session_id"]
        assert rows[0]["end_method"] == end_method
        assert learning_sessions(tmp_path) == [(PID, lecture_id)]
        # 研究者のダウンロードに出る講義 ID
        download = client.get(
            f"/research/participants/{PID}/dialog-logs", headers=_basic(*RESEARCHER)
        )
        assert download.status_code == 200
        assert [item["lecture_id"] for item in download.get_json()] == [lecture_id]


# ---------------------------------------------------------------- AC14 API の lecture_id

BODY_APIS = ["viewing-log", "quiz-attempts", "chat", "dialog-log"]
GET_APIS = ["lad", "last-updated"]
ALL_APIS = BODY_APIS + GET_APIS
OK_STATUS = {
    "viewing-log": 201, "quiz-attempts": 201, "chat": 200,
    "dialog-log": 200, "lad": 200, "last-updated": 200,
}
SELECTION_CASES = [("lecture-2", "lecture-3"), ("lecture-5", "lecture-2")]  # (選択した講義 X, 別の講義)


def _call(client, api: str, lecture_id: str, value=..., participant: str = PID):
    """api を呼ぶ。value=... なら lecture_id を含めない。GET では value を文字列にしてクエリに付ける。"""
    if api == "viewing-log":
        body = viewing_body(value)
        body["participant_id"] = participant
        return client.post("/api/viewing-log", json=body)
    if api == "quiz-attempts":
        body = quiz_payload_for(lecture_id, value)
        body["participant_id"] = participant
        return client.post("/api/quiz-attempts", json=body)
    if api == "chat":
        body = _chat_body("質問", value)
        body["participant_id"] = participant
        return client.post("/chat", json=body)
    if api == "dialog-log":
        body = _dialog_body("end_button", value)
        body["participant_id"] = participant
        return client.post("/api/dialog-log", json=body)
    query = "" if value is ... else f"lecture_id={quote(str(value))}"
    if api == "lad":
        return client.get(f"/api/participants/{participant}/lad" + (f"?{query}" if query else ""))
    separator = "&" if query else ""
    return client.get(f"/api/last-updated?participant_id={participant}{separator}{query}")


def _bad_value(api: str, value):
    """GET の API ではクエリに載せられる値(文字列)だけにする。"""
    return str(value) if api in GET_APIS else value


class TestAc14ApiLectureId:
    @pytest.fixture
    def prepared(self, env):
        """X を選び、記録と対話が1件ずつある状態(「変わらない」の検査が空振りしないため)。"""
        app, llm, tmp_path = env

        def make(lecture_id: str):
            client = _selected(app, lecture_id)
            assert _call(client, "viewing-log", lecture_id).status_code == 201
            assert _call(client, "chat", lecture_id).status_code == 200
            return client, llm, tmp_path

        return make

    @pytest.mark.parametrize("api", ALL_APIS)
    @pytest.mark.parametrize(("lecture_id", "other"), SELECTION_CASES)
    def test_ac14_same_lecture_and_null_behave_like_omitted(self, prepared, api, lecture_id, other) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC14(X・null は送らないときと同じ)
        client, _llm, tmp_path = prepared(lecture_id)

        omitted = _call(client, api, lecture_id)
        same = _call(client, api, lecture_id, lecture_id)

        assert omitted.status_code == OK_STATUS[api], omitted.get_data(as_text=True)
        assert same.status_code == OK_STATUS[api], same.get_data(as_text=True)
        if api in GET_APIS:
            assert same.get_json() == omitted.get_json()
        if api in BODY_APIS:
            null = _call(client, api, lecture_id, None)
            assert null.status_code == OK_STATUS[api], null.get_data(as_text=True)
        assert learning_sessions(tmp_path) == [(PID, lecture_id)]

    @pytest.mark.parametrize("api", ALL_APIS)
    @pytest.mark.parametrize(("lecture_id", "other"), SELECTION_CASES)
    @pytest.mark.parametrize("kind", ["other-lecture", "not-in-catalog", "number"])
    def test_ac14_different_value_is_403_and_nothing_changes(
        self, prepared, api, lecture_id, other, kind
    ) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC14(別の講義・カタログにない値・数値 → 403)
        client, llm, tmp_path = prepared(lecture_id)
        value = {"other-lecture": other, "not-in-catalog": "lecture-9", "number": 2}[kind]
        before = dump_databases(tmp_path)
        llm_before = (len(llm.generate_calls), len(llm.generate_json_calls))

        response = _call(client, api, lecture_id, _bad_value(api, value))

        assert response.status_code == 403, response.get_data(as_text=True)
        assert dump_databases(tmp_path) == before
        assert (len(llm.generate_calls), len(llm.generate_json_calls)) == llm_before

    @pytest.mark.parametrize("api", ALL_APIS)
    @pytest.mark.parametrize(("lecture_id", "other"), SELECTION_CASES)
    def test_ac14_empty_string_is_400_and_nothing_changes(self, prepared, api, lecture_id, other) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC14(空文字 → 400。DR-003)
        client, llm, tmp_path = prepared(lecture_id)
        before = dump_databases(tmp_path)
        llm_before = (len(llm.generate_calls), len(llm.generate_json_calls))

        response = _call(client, api, lecture_id, "")

        assert response.status_code == 400, response.get_data(as_text=True)
        assert dump_databases(tmp_path) == before
        assert (len(llm.generate_calls), len(llm.generate_json_calls)) == llm_before

    @pytest.mark.parametrize("api", BODY_APIS)
    @pytest.mark.parametrize("value", [True, False, [], ["lecture-2"], {}, {"id": "lecture-2"}],
                             ids=["true", "false", "empty-array", "array", "empty-object", "object"])
    def test_ac14_bool_array_object_in_body_is_400_and_nothing_changes(self, prepared, api, value) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC14(真偽値・配列・オブジェクト → 400)
        client, llm, tmp_path = prepared("lecture-2")
        before = dump_databases(tmp_path)
        llm_before = (len(llm.generate_calls), len(llm.generate_json_calls))

        response = _call(client, api, "lecture-2", value)

        assert response.status_code == 400, response.get_data(as_text=True)
        assert dump_databases(tmp_path) == before
        assert (len(llm.generate_calls), len(llm.generate_json_calls)) == llm_before

    @pytest.mark.parametrize("api", ["viewing-log", "chat"])
    def test_not_in_catalog_value_is_403_not_404(self, prepared, api) -> None:
        # 仕様: docs/spec/lecture-selection.md#実現内容 4(検査の順序。参加者の API はカタログにないことを理由とする 404 を返さない)
        client, _llm, _tmp = prepared("lecture-2")

        statuses = {_call(client, api, "lecture-2", v).status_code for v in ("lecture-9", "lecture-99")}

        assert statuses == {403}


# ---------------------------------------------------------------- AC17 未選択の API


class TestAc17Unselected:
    @pytest.fixture
    def unselected(self, env):
        app, llm, tmp_path = env
        client = app.test_client()
        login_unselected(client, PID)
        return client, llm, tmp_path

    @pytest.mark.parametrize("api", ALL_APIS)
    @pytest.mark.parametrize("value", [..., "lecture-2", "lecture-5"], ids=["omitted", "lecture-2", "lecture-5"])
    def test_ac17_unselected_is_409_and_nothing_changes(self, unselected, api, value) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC17
        client, llm, tmp_path = unselected
        before = dump_databases(tmp_path)

        response = _call(client, api, "lecture-2", value)

        assert response.status_code == 409, response.get_data(as_text=True)
        assert dump_databases(tmp_path) == before
        assert (len(llm.generate_calls), len(llm.generate_json_calls)) == (0, 0)
        assert learning_sessions(tmp_path) == []

    @pytest.mark.parametrize("api", ALL_APIS)
    @pytest.mark.parametrize("value", ["lecture-9", "", 2], ids=["not-in-catalog", "empty", "number"])
    def test_unselected_is_409_whatever_the_lecture_id_value_is(self, unselected, api, value) -> None:
        # 仕様: docs/spec/lecture-selection.md#実現内容 4(検査の順序: 409 は lecture_id の値によらない。DR-004)
        client, llm, tmp_path = unselected
        before = dump_databases(tmp_path)

        response = _call(client, api, "lecture-2", _bad_value(api, value))

        assert response.status_code == 409, response.get_data(as_text=True)
        assert dump_databases(tmp_path) == before
        assert len(llm.generate_calls) == 0

    @pytest.mark.parametrize("api", ALL_APIS)
    def test_ac17_not_logged_in_is_401_not_409(self, env, api) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC17(#30 のとおり 401)
        app, _llm, _tmp = env

        response = _call(app.test_client(), api, "lecture-2")

        assert response.status_code == 401

    @pytest.mark.parametrize("api", ALL_APIS)
    def test_ac17_another_participants_id_is_403_not_409(self, unselected, api) -> None:
        # 仕様: docs/spec/lecture-selection.md#受入基準 AC17(#30 のとおり 403)
        client, llm, tmp_path = unselected
        before = dump_databases(tmp_path)

        response = _call(client, api, "lecture-2", participant=OTHER_PID)

        assert response.status_code == 403, response.get_data(as_text=True)
        assert dump_databases(tmp_path) == before
        assert len(llm.generate_calls) == 0
