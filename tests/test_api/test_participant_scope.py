# 仕様: docs/spec/participant-login.md#受入基準
# AC1(画面)、AC4(画面)、AC11、AC12、AC13、AC14、AC30。(AC25 は講義の選択 #34 の AC16 に置き換え)AC16 は既存テストの再実行で確かめる。
"""参加者の特定(FR-52)と、本人のデータだけを扱うこと(30-T3)。

ログインした本人 = "A"。他人 = "truncate-test"(画面の本文に偶然含まれにくい文字列にして、漏れの検査を確かにする)。
"""
from __future__ import annotations

import pytest

from framework_drivers.platform.participant_scope import resolve_claimed_participant_id
from tests.login_helpers import (
    build_app,
    displayed_participant_id,
    dump_databases,
    learners_of,
    location_path,
    login_as,
    post_login,
    quiz_payload,
    select_lecture_directly,
    row_counts,
    viewing_payload,
    TEST_PASSWORD,
)

ME = "A"
OTHER = "truncate-test"


@pytest.fixture
def app_and_llm(monkeypatch, tmp_path):
    return build_app(monkeypatch, tmp_path)


@pytest.fixture
def me(app_and_llm):
    client = app_and_llm[0].test_client()
    login_as(client, ME)
    return client


@pytest.fixture
def other(app_and_llm):
    client = app_and_llm[0].test_client()
    login_as(client, OTHER)
    return client


# ---------------------------------------------------------------- 照合の単体(participant_scope)


class TestResolveClaimedParticipantId:
    @pytest.mark.parametrize(
        "claimed",
        [None, "", "A", 1, "1"],
        ids=["none", "empty", "same-str", "int-same", "str-1"],
    )
    def test_ac30_acceptable_values_return_none(self, claimed) -> None:
        logged_in = "1" if claimed in (1, "1") else "A"
        assert resolve_claimed_participant_id(claimed, logged_in) is None

    @pytest.mark.parametrize("claimed", ["B", 2, "2", "a"])
    def test_ac12_ac30_a_different_id_is_403(self, claimed) -> None:
        assert resolve_claimed_participant_id(claimed, "A" if isinstance(claimed, str) else "1") == 403

    @pytest.mark.parametrize("claimed", [True, False, ["1"], {"id": "1"}])
    def test_ac30_bool_list_and_object_are_400(self, claimed) -> None:
        assert resolve_claimed_participant_id(claimed, "1") == 400

    @pytest.mark.parametrize("claimed", ["  ", " ", "\t", 1.0], ids=["two-spaces", "space", "tab", "float-1.0"])
    def test_ac30_whitespace_only_and_float_not_matching_are_403(self, claimed) -> None:
        # 空白だけは「空」ではない。1.0 は "1.0" になり本人の "1" と一致しない
        assert resolve_claimed_participant_id(claimed, "1") == 403

    def test_ac30_bool_is_not_a_number(self) -> None:
        # True を数値 1 とみなして、ログイン ID "1" と一致させてはならない
        assert resolve_claimed_participant_id(True, "1") == 400


# ---------------------------------------------------------------- AC1 / AC4 / AC11 画面


class TestScreensShowTheLoggedInParticipant:
    @pytest.mark.parametrize("path", ["/lecture", "/reflect"])
    def test_ac11_screens_without_query_show_the_logged_in_participant(self, me, path) -> None:
        response = me.get(path)

        assert response.status_code == 200
        assert displayed_participant_id(response.get_data(as_text=True)) == ME

    def test_ac1_ac4_login_then_redirect_target_shows_own_screen_without_query(self, app_and_llm) -> None:
        client = app_and_llm[0].test_client()
        first = client.get("/reflect")
        assert location_path(first) == "/login"
        from urllib.parse import parse_qs, urlsplit

        next_value = parse_qs(urlsplit(first.headers["Location"]).query)["next"][0]

        login = post_login(client, ME, TEST_PASSWORD, next_path=next_value)
        select_lecture_directly(ME, "lecture-1")  # 選択前は 302(講義の選択 AC)なので、選択済みにする

        assert location_path(login) == "/reflect"
        page = client.get(login.headers["Location"])
        assert page.status_code == 200
        assert displayed_participant_id(page.get_data(as_text=True)) == ME

    def test_ac1_direct_login_lands_on_own_lecture(self, app_and_llm) -> None:
        client = app_and_llm[0].test_client()
        login = post_login(client, ME, TEST_PASSWORD)
        select_lecture_directly(ME, "lecture-1")  # 選択前は 302(講義の選択 AC)なので、選択済みにする
        page = client.get(login.headers["Location"])

        assert page.status_code == 200
        assert displayed_participant_id(page.get_data(as_text=True)) == ME

    def test_ac13_query_participant_id_is_ignored_on_screens(self, me, other) -> None:
        # OTHER にデータがある状態
        assert other.post("/api/viewing-log", json=viewing_payload(OTHER, current_time=777)).status_code == 201

        for path in ("/reflect", "/lecture"):
            response = me.get(f"{path}?participant_id={OTHER}")
            assert response.status_code == 200, path
            html = response.get_data(as_text=True)
            assert displayed_participant_id(html) == ME, path
            assert OTHER not in html, path

    def test_ac1_screens_have_logout_form_and_no_participant_id_guidance(self, me) -> None:
        for path in ("/lecture", "/reflect"):
            html = me.get(path).get_data(as_text=True)
            assert 'action="/logout"' in html, path
            assert "?participant_id=" not in html, path

    def test_ac1_front_end_gets_the_logged_in_id_from_the_page(self, me) -> None:
        html = me.get("/lecture").get_data(as_text=True)

        assert "__PARTICIPANT_ID__" in html
        assert f'"{ME}"' in html


# ---------------------------------------------------------------- AC12 他人の ID を指定した書き込み


class TestAc12WritesForAnotherParticipant:
    def _seed_own_data(self, me) -> None:
        assert me.post("/api/viewing-log", json=viewing_payload(ME, current_time=11)).status_code == 201
        assert me.post("/api/quiz-attempts", json=quiz_payload(ME)).status_code == 201
        assert me.post("/chat", json={"message": "最初の質問", "participant_id": ME}).status_code == 200

    def test_ac12_four_writes_for_another_participant_are_403_and_leave_the_dbs_untouched(
        self, app_and_llm, me, tmp_path
    ) -> None:
        _, llm = app_and_llm
        self._seed_own_data(me)
        before = dump_databases(tmp_path)
        llm_before = (len(llm.generate_calls), len(llm.generate_json_calls))

        responses = {
            "viewing-log": me.post("/api/viewing-log", json=viewing_payload(OTHER)),
            "quiz-attempts": me.post("/api/quiz-attempts", json=quiz_payload(OTHER)),
            "dialog-log": me.post("/api/dialog-log", json={"participant_id": OTHER, "end_method": "end_button"}),
            "chat": me.post("/chat", json={"message": "なりすまし", "participant_id": OTHER}),
        }

        assert {k: r.status_code for k, r in responses.items()} == {k: 403 for k in responses}
        assert dump_databases(tmp_path) == before
        assert (len(llm.generate_calls), len(llm.generate_json_calls)) == llm_before


# ---------------------------------------------------------------- AC13 他人の ID を指定した読み出し


class TestAc13ReadsForAnotherParticipant:
    @pytest.fixture
    def other_data(self, other):
        assert other.post("/api/viewing-log", json=viewing_payload(OTHER, current_time=777)).status_code == 201
        assert other.post("/api/quiz-attempts", json=quiz_payload(OTHER)).status_code == 201
        return other.get(f"/api/last-updated?participant_id={OTHER}").get_json()["last_updated"]

    def test_ac13_lad_and_last_updated_of_another_participant_are_403_without_their_data(
        self, me, other_data
    ) -> None:
        assert other_data is not None
        lad = me.get(f"/api/participants/{OTHER}/lad")
        updated = me.get(f"/api/last-updated?participant_id={OTHER}")

        assert lad.status_code == 403
        assert updated.status_code == 403
        for response in (lad, updated):
            body = response.get_data(as_text=True)
            assert other_data not in body
            assert "action_counts" not in body

    def test_ac13_own_lad_does_not_include_the_other_participants_records(self, me, other_data) -> None:
        lad = me.get(f"/api/participants/{ME}/lad")

        assert lad.status_code == 200
        assert lad.get_json()["action_counts"] == {} or sum(lad.get_json()["action_counts"].values()) == 0


# ---------------------------------------------------------------- AC14 participant_id の省略


class TestAc14OmittedParticipantId:
    def test_ac14_writes_without_participant_id_are_recorded_as_the_logged_in_participant(
        self, me, tmp_path
    ) -> None:
        assert me.post("/api/viewing-log", json=viewing_payload()).status_code == 201
        assert me.post("/api/quiz-attempts", json=quiz_payload()).status_code == 201
        chat = me.post("/chat", json={"message": "省略した質問"})
        assert chat.status_code == 200
        assert me.post("/api/dialog-log", json={"end_method": "end_button"}).status_code == 200

        assert learners_of(tmp_path, "viewing_logs") == [ME]
        assert learners_of(tmp_path, "quiz_attempts") == [ME]
        import sqlite3

        learning = sqlite3.connect(str(tmp_path / "learning.db"))
        tutor = sqlite3.connect(str(tmp_path / "tutor.db"))
        try:
            assert {r[0] for r in learning.execute("SELECT learner_id FROM learning_sessions")} == {ME}
            assert {r[0] for r in tutor.execute("SELECT participant_id FROM dialog_logs")} == {ME}
        finally:
            learning.close()
            tutor.close()

    def test_ac14_last_updated_and_lad_without_participant_id_are_the_own_data(self, me) -> None:
        assert me.post("/api/viewing-log", json=viewing_payload(ME, current_time=5)).status_code == 201
        explicit = me.get(f"/api/last-updated?participant_id={ME}").get_json()["last_updated"]
        assert explicit is not None

        omitted = me.get("/api/last-updated")

        assert omitted.status_code == 200
        assert omitted.get_json()["last_updated"] == explicit

    def test_ac14_own_participant_id_is_processed_as_before(self, me, tmp_path) -> None:
        assert me.post("/api/viewing-log", json=viewing_payload(ME)).status_code == 201
        assert me.get(f"/api/participants/{ME}/lad").status_code == 200
        assert learners_of(tmp_path, "viewing_logs") == [ME]


# ---------------------------------------------------------------- AC25 講義割当の維持(置き換え済み)
#
# 旧 AC25(P01〜P31 は講義IDなしで lecture-1、明示の lecture_id が勝つ)は、講義の選択(#34)で置き換わった。
# 仕様: docs/spec/lecture-selection.md#受入基準 AC16(固定対応の廃止)・AC15(画面の lecture_id)
# 新しい検証は tests/test_api/test_lecture_selection_flow.py にある。


# ---------------------------------------------------------------- AC30 値の形


class TestAc30ValueShapes:
    @pytest.fixture
    def one(self, app_and_llm):
        client = app_and_llm[0].test_client()
        login_as(client, "1")
        return client

    def test_ac30_empty_null_and_number_of_own_id_are_recorded_for_the_participant(
        self, one, tmp_path
    ) -> None:
        for claimed in ("", None, 1):
            response = one.post("/api/viewing-log", json=viewing_payload(claimed))
            assert response.status_code == 201, claimed

        assert learners_of(tmp_path, "viewing_logs") == ["1", "1", "1"]

    def test_ac30_a_number_of_another_id_is_403_and_nothing_changes(self, one, tmp_path) -> None:
        assert one.post("/api/viewing-log", json=viewing_payload("1")).status_code == 201
        before = dump_databases(tmp_path)

        response = one.post("/api/viewing-log", json=viewing_payload(2))

        assert response.status_code == 403
        assert dump_databases(tmp_path) == before

    def test_ac30_empty_query_value_returns_the_own_last_updated(self, one) -> None:
        assert one.post("/api/viewing-log", json=viewing_payload("1")).status_code == 201
        explicit = one.get("/api/last-updated?participant_id=1").get_json()["last_updated"]

        response = one.get("/api/last-updated?participant_id=")

        assert response.status_code == 200
        assert explicit is not None
        assert response.get_json()["last_updated"] == explicit

    @pytest.mark.parametrize("claimed", ["  ", 1.0], ids=["whitespace-only", "float-1.0"])
    def test_ac30_whitespace_only_and_non_matching_float_are_403_on_all_writes(
        self, app_and_llm, one, tmp_path, claimed
    ) -> None:
        _, llm = app_and_llm
        assert one.post("/api/viewing-log", json=viewing_payload("1")).status_code == 201
        assert one.post("/chat", json={"message": "最初の質問", "participant_id": "1"}).status_code == 200
        before = dump_databases(tmp_path)
        counts_before = row_counts(tmp_path)
        llm_before = (len(llm.generate_calls), len(llm.generate_json_calls))

        responses = {
            "viewing-log": one.post("/api/viewing-log", json=viewing_payload(claimed)),
            "quiz-attempts": one.post("/api/quiz-attempts", json=quiz_payload(claimed)),
            "dialog-log": one.post("/api/dialog-log", json={"participant_id": claimed, "end_method": "end_button"}),
            "chat": one.post("/chat", json={"message": "なりすまし", "participant_id": claimed}),
        }

        assert {k: r.status_code for k, r in responses.items()} == {k: 403 for k in responses}
        assert row_counts(tmp_path) == counts_before
        assert dump_databases(tmp_path) == before
        assert (len(llm.generate_calls), len(llm.generate_json_calls)) == llm_before

    @pytest.mark.parametrize(
        "claimed",
        [True, False, ["1"], {"id": "1"}],
        ids=["true", "false", "array", "object"],
    )
    def test_ac30_bool_array_and_object_are_400_and_nothing_changes(
        self, one, tmp_path, claimed
    ) -> None:
        assert one.post("/api/viewing-log", json=viewing_payload("1")).status_code == 201
        before = row_counts(tmp_path)

        response = one.post("/api/viewing-log", json=viewing_payload(claimed))

        assert response.status_code == 400
        assert row_counts(tmp_path) == before
