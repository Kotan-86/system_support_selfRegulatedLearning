# 仕様: docs/spec/research-dialog-download.md#受入基準 (R1 R2 R3 R8)
# 仕様: docs/spec/research-dialog-download.md#url-と資格情報共有if固定済み2026-10-19
"""研究者の Basic 認証: 判定関数、401 応答、フックの登録。"""
from __future__ import annotations

import base64

import pytest
from flask import Flask
from werkzeug.datastructures import Authorization

from framework_drivers.platform.research_auth import (
    RESEARCHER_PASSWORD_ENV,
    RESEARCHER_USER_ENV,
    is_authorized,
    is_research_path,
    register_research_auth,
    unauthorized_response,
)

ENV_OK = {RESEARCHER_USER_ENV: "researcher", RESEARCHER_PASSWORD_ENV: "s3cret"}


def _basic(user, password) -> Authorization:
    return Authorization("basic", {"username": user, "password": password})


def _header(user: str, password: str) -> dict[str, str]:
    raw = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {raw}"}


class TestEnvNames:
    def test_r3_env_var_names_are_fixed(self) -> None:
        assert RESEARCHER_USER_ENV == "RESEARCHER_BASIC_AUTH_USER"
        assert RESEARCHER_PASSWORD_ENV == "RESEARCHER_BASIC_AUTH_PASSWORD"


class TestIsAuthorized:
    def test_r1_correct_credentials_are_authorized(self) -> None:
        # 仕様: R1(正しい資格情報だけが通る)
        assert is_authorized(_basic("researcher", "s3cret"), ENV_OK) is True

    def test_r1_missing_authorization_is_rejected(self) -> None:
        assert is_authorized(None, ENV_OK) is False

    def test_r1_wrong_user_is_rejected(self) -> None:
        assert is_authorized(_basic("other", "s3cret"), ENV_OK) is False

    def test_r1_wrong_password_is_rejected(self) -> None:
        assert is_authorized(_basic("researcher", "wrong"), ENV_OK) is False

    def test_r1_non_basic_scheme_is_rejected(self) -> None:
        bearer = Authorization("bearer", {"token": "s3cret"})
        assert is_authorized(bearer, ENV_OK) is False

    def test_r1_missing_username_or_password_is_rejected(self) -> None:
        assert is_authorized(_basic(None, "s3cret"), ENV_OK) is False
        assert is_authorized(_basic("researcher", None), ENV_OK) is False

    def test_r1_prefix_and_extra_characters_are_rejected(self) -> None:
        assert is_authorized(_basic("researcher", "s3cre"), ENV_OK) is False
        assert is_authorized(_basic("researcher", "s3cret!"), ENV_OK) is False

    @pytest.mark.parametrize(
        "env",
        [
            {},
            {RESEARCHER_USER_ENV: "researcher"},
            {RESEARCHER_PASSWORD_ENV: "s3cret"},
            {RESEARCHER_USER_ENV: "", RESEARCHER_PASSWORD_ENV: "s3cret"},
            {RESEARCHER_USER_ENV: "researcher", RESEARCHER_PASSWORD_ENV: ""},
            {RESEARCHER_USER_ENV: "", RESEARCHER_PASSWORD_ENV: ""},
        ],
    )
    def test_r3_unset_or_empty_env_rejects_every_credential(self, env) -> None:
        # 仕様: R3(未設定・空文字なら、空のユーザー名・空のパスワードを含め常に拒否)
        for user, password in [
            ("researcher", "s3cret"),
            ("", ""),
            ("", "s3cret"),
            ("researcher", ""),
            ("anything", "anything"),
        ]:
            assert is_authorized(_basic(user, password), env) is False

    def test_non_ascii_credentials_do_not_raise(self) -> None:
        # 設計 DR-001 M3: ASCII 以外でも例外にしない(500 にしない)
        env = {RESEARCHER_USER_ENV: "研究者", RESEARCHER_PASSWORD_ENV: "パスワード"}
        assert is_authorized(_basic("研究者", "パスワード"), env) is True
        assert is_authorized(_basic("研究者", "ぱすわーど"), env) is False
        assert is_authorized(_basic("日本", "x"), ENV_OK) is False

    def test_env_is_read_at_each_call(self, monkeypatch) -> None:
        # 設計 DR-001 M3: 環境変数を呼び出しのたびに読む
        monkeypatch.delenv(RESEARCHER_USER_ENV, raising=False)
        monkeypatch.delenv(RESEARCHER_PASSWORD_ENV, raising=False)
        assert is_authorized(_basic("researcher", "s3cret")) is False

        monkeypatch.setenv(RESEARCHER_USER_ENV, "researcher")
        monkeypatch.setenv(RESEARCHER_PASSWORD_ENV, "s3cret")
        assert is_authorized(_basic("researcher", "s3cret")) is True

        monkeypatch.setenv(RESEARCHER_PASSWORD_ENV, "changed")
        assert is_authorized(_basic("researcher", "s3cret")) is False


class TestIsResearchPath:
    @pytest.mark.parametrize(
        "path",
        [
            "/research",
            "/research/",
            "/research/dialog-logs",
            "/research/participants/1/dialog-logs",
            "/research/unknown/path",
        ],
    )
    def test_research_paths_are_protected(self, path: str) -> None:
        assert is_research_path(path) is True

    @pytest.mark.parametrize(
        "path", ["/researcher", "/chat", "/", "/reflect", "/api/dialog-log", "/Research/x"]
    )
    def test_other_paths_are_not_protected(self, path: str) -> None:
        assert is_research_path(path) is False


class TestUnauthorizedResponse:
    def test_r1_r8_status_challenge_and_no_store(self) -> None:
        response = unauthorized_response()

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"].lower().startswith("basic")
        assert response.headers["Cache-Control"] == "no-store"

    def test_r1_body_is_fixed_and_has_no_request_values(self) -> None:
        body = unauthorized_response().get_data(as_text=True)

        assert "participant" not in body.lower()
        assert "/research" not in body
        assert unauthorized_response().get_data(as_text=True) == body


@pytest.fixture
def mini_app(monkeypatch) -> Flask:
    monkeypatch.setenv(RESEARCHER_USER_ENV, "researcher")
    monkeypatch.setenv(RESEARCHER_PASSWORD_ENV, "s3cret")
    app = Flask(__name__)
    register_research_auth(app)

    @app.route("/research/ping")
    def research_ping():
        return "pong"

    @app.route("/public")
    def public():
        return "open"

    @app.route("/researcher")
    def researcher_lookalike():
        return "open-too"

    return app


class TestRegisterResearchAuth:
    def test_r1_unauthenticated_research_request_is_401_with_challenge(self, mini_app) -> None:
        response = mini_app.test_client().get("/research/ping")

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert "pong" not in response.get_data(as_text=True)

    def test_r1_wrong_credentials_is_401(self, mini_app) -> None:
        response = mini_app.test_client().get(
            "/research/ping", headers=_header("researcher", "nope")
        )

        assert response.status_code == 401

    def test_r1_unmatched_research_url_is_also_401(self, mini_app) -> None:
        # DR-001 M4: ルートに一致しない /research/... も 401(存在の有無を外から区別させない)
        response = mini_app.test_client().get("/research/participants//dialog-logs")

        assert response.status_code == 401
        assert response.headers["Cache-Control"] == "no-store"

    def test_r8_authorized_response_also_has_no_store(self, mini_app) -> None:
        response = mini_app.test_client().get(
            "/research/ping", headers=_header("researcher", "s3cret")
        )

        assert response.status_code == 200
        assert response.get_data(as_text=True) == "pong"
        assert response.headers["Cache-Control"] == "no-store"

    def test_r8_unauthorized_response_has_no_store(self, mini_app) -> None:
        response = mini_app.test_client().get("/research/ping")

        assert response.headers["Cache-Control"] == "no-store"

    def test_r3_unset_env_rejects_even_matching_looking_credentials(
        self, mini_app, monkeypatch
    ) -> None:
        monkeypatch.delenv(RESEARCHER_PASSWORD_ENV)

        for user, password in [("researcher", ""), ("", ""), ("researcher", "s3cret")]:
            response = mini_app.test_client().get(
                "/research/ping", headers=_header(user, password)
            )
            assert response.status_code == 401

    def test_non_research_paths_are_unaffected(self, mini_app) -> None:
        client = mini_app.test_client()

        public = client.get("/public")
        lookalike = client.get("/researcher")

        assert public.status_code == 200 and public.get_data(as_text=True) == "open"
        assert lookalike.status_code == 200
        assert "no-store" not in (public.headers.get("Cache-Control") or "")
