# 仕様: docs/spec/participant-login.md#受入基準
# AC7(画面)、AC8(API)、AC9(除外の範囲)、AC10(研究者の経路は不変)
"""未ログインの要求の拒否(FR-51)(30-T1)。"""
from __future__ import annotations

import base64

import pytest

from tests.login_helpers import (
    TEST_PASSWORD,
    build_app,
    dump_databases,
    location_path,
    login_as,
    quiz_payload,
    viewing_payload,
)

RESEARCHER = ("researcher", "s3cret-pass")


def _basic(user: str, password: str) -> dict[str, str]:
    raw = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {raw}"}


@pytest.fixture
def app_and_llm(monkeypatch, tmp_path):
    monkeypatch.setenv("RESEARCHER_BASIC_AUTH_USER", RESEARCHER[0])
    monkeypatch.setenv("RESEARCHER_BASIC_AUTH_PASSWORD", RESEARCHER[1])
    return build_app(monkeypatch, tmp_path)


@pytest.fixture
def anon(app_and_llm):
    return app_and_llm[0].test_client()


@pytest.fixture
def seeded(app_and_llm, tmp_path):
    """参加者 "1" のデータ(視聴ログ・小テスト・対話)が入った状態。"""
    app, llm = app_and_llm
    owner = app.test_client()
    login_as(owner, "1")
    assert owner.post("/api/viewing-log", json=viewing_payload("1", current_time=4321)).status_code == 201
    assert owner.post("/api/quiz-attempts", json=quiz_payload("1")).status_code == 201
    assert owner.post("/chat", json={"message": "SECRETBODY-質問", "participant_id": "1"}).status_code == 200
    return owner


# ---------------------------------------------------------------- AC7


class TestAc7ScreensRedirectToLogin:
    @pytest.mark.parametrize(
        "url",
        ["/", "/lecture", "/reflect", "/lecture?participant_id=1", "/reflect?participant_id=1"],
    )
    def test_ac7_unauthenticated_screen_is_302_to_login_without_data(
        self, anon, seeded, url
    ) -> None:
        response = anon.get(url)

        assert response.status_code == 302
        assert location_path(response) == "/login"
        body = response.get_data(as_text=True)
        for leaked in ('id="player"', "lad-panel", "chat-panel", "SECRETBODY", "4321"):
            assert leaked not in body


# ---------------------------------------------------------------- AC8


class TestAc8ApisReturn401:
    def _calls(self, client):
        return [
            ("chat", client.post("/chat", json={"message": "こんにちは", "participant_id": "1"})),
            ("dialog-log", client.post("/api/dialog-log", json={"participant_id": "1", "end_method": "end_button"})),
            ("quiz-attempts", client.post("/api/quiz-attempts", json=quiz_payload("1"))),
            ("viewing-log", client.post("/api/viewing-log", json=viewing_payload("1", current_time=999))),
            ("last-updated", client.get("/api/last-updated?participant_id=1")),
            ("lad", client.get("/api/participants/1/lad")),
        ]

    def test_ac8_all_six_are_401_and_nothing_is_written_or_called(
        self, app_and_llm, anon, seeded, tmp_path
    ) -> None:
        _, llm = app_and_llm
        before = dump_databases(tmp_path)
        llm_calls_before = (len(llm.generate_calls), len(llm.generate_json_calls))

        results = self._calls(anon)

        assert [(name, r.status_code) for name, r in results] == [(n, 401) for n, _ in results]
        assert dump_databases(tmp_path) == before
        assert (len(llm.generate_calls), len(llm.generate_json_calls)) == llm_calls_before

    def test_ac8_responses_contain_no_learning_or_dialog_data(self, anon, seeded) -> None:
        for name, response in self._calls(anon):
            body = response.get_data(as_text=True)
            for leaked in ("SECRETBODY", "スタブ応答", "action_counts", "learner_profile", "4321"):
                assert leaked not in body, name

    def test_ac8_unauthenticated_requests_with_query_participant_are_not_trusted(
        self, anon, seeded
    ) -> None:
        assert anon.get("/api/last-updated?participant_id=1").status_code == 401
        assert anon.get("/api/participants/1/lad?participant_id=1").status_code == 401


# ---------------------------------------------------------------- AC9


class TestAc9ExemptPaths:
    def test_ac9_login_page_and_static_files_are_public(self, anon) -> None:
        assert anon.get("/login").status_code == 200
        for path in (
            "/static/js/common/api_client.js",
            "/static/js/common/participant_context.js",
            "/static/css/style.css",
        ):
            assert anon.get(path).status_code == 200, path


# ---------------------------------------------------------------- AC10


class TestAc10ResearcherRouteUnchanged:
    URLS = ["/research/dialog-logs", "/research/participants/1/dialog-logs"]

    @pytest.mark.parametrize("url", URLS)
    def test_ac10_basic_auth_alone_decides_for_anonymous_participant(self, anon, seeded, url) -> None:
        assert anon.get(url, headers=_basic(*RESEARCHER)).status_code == 200
        no_basic = anon.get(url)
        assert no_basic.status_code == 401
        assert "Location" not in no_basic.headers  # ログイン画面へ誘導しない
        assert no_basic.headers["WWW-Authenticate"].lower().startswith("basic")

    @pytest.mark.parametrize("url", URLS)
    def test_ac10_participant_login_does_not_replace_basic_auth(self, app_and_llm, url) -> None:
        participant = app_and_llm[0].test_client()
        login_as(participant, "1")

        assert participant.get(url).status_code == 401
        assert participant.get(url, headers=_basic("1", TEST_PASSWORD)).status_code == 401
        assert participant.get(url, headers=_basic(*RESEARCHER)).status_code == 200

    def test_ac10_participant_credentials_are_not_accepted_as_researcher(self, anon) -> None:
        response = anon.get("/research/dialog-logs", headers=_basic("1", TEST_PASSWORD))

        assert response.status_code == 401
