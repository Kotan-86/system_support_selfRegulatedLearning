# 仕様: docs/spec/https-enforcement.md#受入基準 (AC1〜AC10)
# AC11(ドキュメント)は AI実行、AC12(本番での確認)は PO確認。ここでは検証しない。
"""HTTPS の強制を、create_app 経由で Flask のテストクライアントから確かめる。

「http の要求」は X-Forwarded-Proto: http、または X-Forwarded-Proto なし。
「https の要求」は X-Forwarded-Proto: https。共通設定が与える解除の環境変数
(HTTPS_ENFORCEMENT_DISABLED)は、このファイルのアプリでは外してから作る(AC8 を除く)。
共有する名前は環境変数 HTTPS_ENFORCEMENT_DISABLED だけで、アプリの内部の名前には依存しない。
"""
from __future__ import annotations

import base64
from pathlib import Path

import pytest

from tests.login_helpers import (
    TEST_PASSWORD,
    build_app,
    location_path,
    post_login,
    quiz_payload,
    row_counts,
    select_lecture_directly,
    viewing_payload,
)

DISABLED_ENV = "HTTPS_ENFORCEMENT_DISABLED"
SECURE_DISABLED_ENV = "SESSION_COOKIE_SECURE_DISABLED"
USER_ENV = "RESEARCHER_BASIC_AUTH_USER"
PASSWORD_ENV = "RESEARCHER_BASIC_AUTH_PASSWORD"
RESEARCHER = ("researcher", "s3cret-pass")
PID = "P01"
HSTS = "max-age=31536000"
PROTO = "X-Forwarded-Proto"
SECRET_TEXT = "SECRETBODY-質問"


def basic(user: str, password: str) -> dict[str, str]:
    raw = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {raw}"}


AUTH = basic(*RESEARCHER)


def send(client, method: str, url: str, proto: str | None = "https", *, headers=None, **kwargs):
    """proto: "https" / "http" / None(ヘッダなし)。"""
    merged = dict(headers or {})
    if proto is not None:
        merged[PROTO] = proto
    return getattr(client, method)(url, headers=merged, **kwargs)


@pytest.fixture
def enforced(monkeypatch, tmp_path: Path):
    """強制が有効(解除の環境変数なし)のアプリ。戻り値は (app, llm)。"""
    monkeypatch.delenv(DISABLED_ENV, raising=False)
    monkeypatch.setenv(USER_ENV, RESEARCHER[0])
    monkeypatch.setenv(PASSWORD_ENV, RESEARCHER[1])
    return build_app(monkeypatch, tmp_path, propagate=False)


@pytest.fixture
def app(enforced):
    return enforced[0]


@pytest.fixture
def llm(enforced):
    return enforced[1]


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in(client):
    """https でログイン済みのクライアント。"""
    response = send(client, "post", "/login", "https", data={"participant_id": PID, "password": TEST_PASSWORD})
    assert response.status_code == 302
    select_lecture_directly(PID, "lecture-1")  # 選択前は 409/302(講義の選択 AC)なので、選択済みにする
    return client


# ---------------------------------------------------------------- AC1

GET_URLS = [
    "/lecture?lecture_id=lecture-2",
    "/login",
    "/",
    "/static/js/common/api_client.js",
]


class TestAc1HttpGetRedirects:
    @pytest.mark.parametrize("url", GET_URLS)
    @pytest.mark.parametrize("login", [False, True], ids=["anonymous", "logged-in"])
    def test_ac1_http_get_is_301_to_https_same_host_path_query(self, request, client, url, login) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC1
        if login:
            request.getfixturevalue("logged_in")
        response = send(client, "get", url, "http")
        assert response.status_code == 301
        assert response.headers["Location"] == f"https://localhost{url}"
        body = response.get_data(as_text=True)
        assert PID not in body
        assert "<form" not in body
        assert "youtube" not in body.lower()

    def test_ac1_http_head_is_301(self, logged_in) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC1(HEAD)
        response = send(logged_in, "head", "/lecture", "http")
        assert response.status_code == 301
        assert response.headers["Location"] == "https://localhost/lecture"


# ---------------------------------------------------------------- AC2


class TestAc2NoHeader:
    def test_ac2_get_without_forwarded_proto_is_301(self, client) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC2
        response = send(client, "get", "/lecture", None)
        assert response.status_code == 301
        assert response.headers["Location"] == "https://localhost/lecture"

    def test_ac2_login_page_without_header_is_301_not_200(self, client) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC2(元の方式が分からない要求を https とみなさない)
        response = send(client, "get", "/login", None)
        assert response.status_code == 301
        assert "<form" not in response.get_data(as_text=True)


# ---------------------------------------------------------------- AC3


class TestAc3HttpWritesRejected:
    @pytest.mark.parametrize("proto", ["http", None], ids=["http", "no-header"])
    def test_ac3_login_post_is_400_and_does_not_log_in(self, client, proto) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC3
        response = send(
            client, "post", "/login", proto,
            data={"participant_id": PID, "password": TEST_PASSWORD},
        )
        assert response.status_code == 400
        assert response.headers.getlist("Set-Cookie") == []
        follow = send(client, "get", "/lecture", "https")
        assert follow.status_code == 302
        assert location_path(follow) == "/login"

    @pytest.mark.parametrize("proto", ["http", None], ids=["http", "no-header"])
    def test_ac3_api_posts_are_400_and_change_no_rows_and_call_no_llm(
        self, logged_in, tmp_path, llm, proto
    ) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC3
        before = row_counts(tmp_path)
        llm_before = (len(llm.generate_calls), len(llm.generate_json_calls))
        requests = [
            ("/api/viewing-log", viewing_payload(PID, current_time=777)),
            ("/api/quiz-attempts", quiz_payload(PID)),
            ("/api/dialog-log", {"participant_id": PID, "end_method": "end_button"}),
            ("/chat", {"message": "こんにちは", "participant_id": PID}),
        ]
        for url, body in requests:
            response = send(logged_in, "post", url, proto, json=body)
            assert response.status_code == 400, url
        assert row_counts(tmp_path) == before
        assert (len(llm.generate_calls), len(llm.generate_json_calls)) == llm_before


# ---------------------------------------------------------------- AC4


class TestAc4Research:
    @pytest.fixture
    def seeded(self, logged_in):
        chat = send(logged_in, "post", "/chat", "https", json={"message": SECRET_TEXT, "participant_id": PID})
        assert chat.status_code == 200
        saved = send(logged_in, "post", "/api/dialog-log", "https", json={"participant_id": PID, "end_method": "end_button"})
        assert saved.status_code == 200
        return logged_in

    @pytest.mark.parametrize("proto", ["http", None], ids=["http", "no-header"])
    @pytest.mark.parametrize(
        "url,headers",
        [
            ("/research/dialog-logs", AUTH),
            ("/research/participants/P01/dialog-logs", AUTH),
            ("/research/dialog-logs", None),
        ],
        ids=["all-valid-auth", "participant-valid-auth", "all-no-auth"],
    )
    def test_ac4_http_research_is_301_before_basic_auth(self, seeded, url, headers, proto) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC4
        response = send(seeded, "get", url, proto, headers=headers)
        assert response.status_code == 301
        assert response.headers["Location"] == f"https://localhost{url}"
        body = response.get_data(as_text=True)
        assert SECRET_TEXT not in body
        assert "スタブ応答" not in body


# ---------------------------------------------------------------- AC5


class TestAc5HttpsPassesThrough:
    def test_ac5_full_flow_over_https_is_unchanged(self, client, tmp_path) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC5
        login = send(client, "post", "/login", "https", data={"participant_id": PID, "password": TEST_PASSWORD})
        assert login.status_code == 302
        assert not login.headers["Location"].startswith("http://")
        select_lecture_directly(PID, "lecture-1")  # 選択前は 302(講義の選択 AC)なので、選択済みにする
        assert send(client, "get", "/lecture", "https").status_code == 200
        before = row_counts(tmp_path)
        posted = send(client, "post", "/api/viewing-log", "https", json=viewing_payload(PID, current_time=55))
        assert posted.status_code == 201
        assert row_counts(tmp_path) != before
        assert send(client, "get", f"/api/participants/{PID}/lad", "https").status_code == 200

    def test_ac5_anonymous_lecture_redirects_to_login_not_http(self, client) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC5
        response = send(client, "get", "/lecture", "https")
        assert response.status_code == 302
        assert not response.headers["Location"].startswith("http://")
        assert location_path(response) == "/login"

    def test_ac5_research_over_https_keeps_basic_auth(self, client) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC5
        assert send(client, "get", "/research/dialog-logs", "https", headers=AUTH).status_code == 200
        assert send(client, "get", "/research/dialog-logs", "https").status_code == 401


# ---------------------------------------------------------------- AC6


class TestAc6MultipleValues:
    def test_ac6_last_value_https_is_treated_as_https(self, client) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC6
        response = send(client, "get", "/login", "http, https")
        assert response.status_code == 200

    def test_ac6_last_value_http_is_treated_as_http(self, client) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC6(最後の値で決まる)
        response = send(client, "get", "/login", "https, http")
        assert response.status_code == 301


# ---------------------------------------------------------------- AC7


class TestAc7Hsts:
    def test_ac7_https_responses_carry_hsts(self, client) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC7
        cases = [
            (send(client, "get", "/login", "https"), 200),
            (send(client, "get", "/lecture", "https"), 302),
            (send(client, "get", "/research/dialog-logs", "https"), 401),
        ]
        for response, status in cases:
            assert response.status_code == status
            assert response.headers.get("Strict-Transport-Security") == HSTS

    def test_ac7_hsts_has_no_includesubdomains_or_preload(self, client) -> None:
        # 仕様: docs/spec/https-enforcement.md#2-https-の応答に-hsts-を付ける論点3
        value = send(client, "get", "/login", "https").headers.get("Strict-Transport-Security", "")
        assert value
        assert "includeSubDomains" not in value
        assert "preload" not in value

    def test_ac7_http_redirect_and_rejection_have_no_hsts(self, client) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC7
        redirect = send(client, "get", "/lecture", "http")
        rejected = send(client, "post", "/login", "http", data={"participant_id": PID, "password": TEST_PASSWORD})
        assert redirect.status_code == 301
        assert rejected.status_code == 400
        assert "Strict-Transport-Security" not in redirect.headers
        assert "Strict-Transport-Security" not in rejected.headers


# ---------------------------------------------------------------- AC8


@pytest.fixture
def make_app(monkeypatch, tmp_path: Path):
    def _make(value: str | None):
        if value is None:
            monkeypatch.delenv(DISABLED_ENV, raising=False)
        else:
            monkeypatch.setenv(DISABLED_ENV, value)
        monkeypatch.setenv(USER_ENV, RESEARCHER[0])
        monkeypatch.setenv(PASSWORD_ENV, RESEARCHER[1])
        app, _ = build_app(monkeypatch, tmp_path, propagate=False)
        return app

    return _make


class TestAc8Disable:
    def test_ac8_value_1_disables_enforcement(self, make_app) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC8
        client = make_app("1").test_client()
        page = send(client, "get", "/login", "http")
        assert page.status_code == 200
        assert "Strict-Transport-Security" not in page.headers
        login = send(client, "post", "/login", "http", data={"participant_id": PID, "password": TEST_PASSWORD})
        assert login.status_code == 302
        select_lecture_directly(PID, "lecture-1")  # 選択前は 302(講義の選択 AC)なので、選択済みにする
        assert send(client, "get", "/lecture", "http").status_code == 200

    def test_ac8_value_1_also_works_without_header(self, make_app) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC8
        client = make_app("1").test_client()
        assert send(client, "get", "/login", None).status_code == 200

    @pytest.mark.parametrize("value", [None, "", "0", "true"], ids=["unset", "empty", "zero", "true"])
    def test_ac8_other_values_keep_enforcing(self, make_app, value) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC8
        client = make_app(value).test_client()
        response = send(client, "get", "/login", "http")
        assert response.status_code == 301
        assert response.headers["Location"] == "https://localhost/login"


# ---------------------------------------------------------------- AC9
# 既存テストの回帰は、conftest.py / login_helpers.py が解除の環境変数を与えた状態で
# `PYTHONUTF8=1 uv run pytest tests/ -v` の全体が成功することで確かめる(tests.md 参照)。


class TestAc9SharedSetupDisablesEnforcement:
    def test_ac9_shared_setup_gives_disable_env(self) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC9
        # このテストは autouse の共通設定の下で動く(enforced フィクスチャを使わない)。
        import os

        assert os.environ.get(DISABLED_ENV) == "1"

    def test_ac9_default_test_client_works_over_plain_http(self, app_client) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC9(既存の app_client は http のまま通る)
        assert app_client.get("/lecture").status_code == 200


# ---------------------------------------------------------------- AC10


class TestAc10CookieSecureIndependent:
    @pytest.mark.parametrize("proto", ["http", "https"])
    def test_ac10_session_cookie_is_secure_when_only_https_check_is_disabled(
        self, monkeypatch, make_app, proto
    ) -> None:
        # 仕様: docs/spec/https-enforcement.md#受入基準 AC10 (#30 AC21 の挙動を変えない)
        monkeypatch.delenv(SECURE_DISABLED_ENV, raising=False)
        client = make_app("1").test_client()
        response = send(client, "post", "/login", proto, data={"participant_id": PID, "password": TEST_PASSWORD})
        assert response.status_code == 302
        cookies = response.headers.getlist("Set-Cookie")
        assert cookies
        assert all("Secure" in c for c in cookies)
