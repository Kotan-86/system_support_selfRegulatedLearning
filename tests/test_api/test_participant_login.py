# 仕様: docs/spec/participant-login.md#受入基準
# AC1(ログインの成立と移動先まで)、AC2、AC3、AC4(Location まで)、AC5、AC21、AC22、AC24、AC27
"""参加者のログイン・ログアウト・セッションの設定(30-T1)。

URL は `GET /login`(画面)、`POST /login`(participant_id、password、next)、`POST /logout`。
200 の画面が要るときは `/lecture?participant_id=<ログイン ID>` の形で開く(T3 の前後どちらでも成り立つ)。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest

from framework_drivers.platform.participant_auth import LOGIN_FAILURE_MESSAGE
from tests.login_helpers import (
    CREDENTIALS_ENV,
    SECURE_DISABLED_ENV,
    build_app,
    displayed_participant_id,
    location_host,
    location_path,
    make_entry,
    post_login,
    write_credentials_file,
)

PW_A = "pw-for-A-0123456789abcdef"
PW_B = "pw-for-B-0123456789abcdef"
PW_S = "pw-for-S-0123456789abcdef"
T0 = datetime(2026, 10, 27, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def creds_path(monkeypatch, tmp_path):
    path = write_credentials_file(
        tmp_path / "creds" / "participants.json",
        [
            make_entry("A", PW_A),
            make_entry("B", PW_B),
            make_entry("S", PW_S, status="suspended"),
        ],
    )
    monkeypatch.setenv(CREDENTIALS_ENV, str(path))
    return path


@pytest.fixture
def anon(monkeypatch, tmp_path, creds_path):
    """未ログインのテストクライアント(A・B は有効、S は停止)。"""
    app, _ = build_app(monkeypatch, tmp_path)
    return app.test_client()


def _logged_in(client, pid="A", pw=PW_A):
    response = post_login(client, pid, pw)
    assert response.status_code == 302
    return response


# ---------------------------------------------------------------- AC1


class TestAc1ValidCredentials:
    def test_ac1_valid_login_redirects_and_lecture_shows_the_id(self, anon) -> None:
        response = post_login(anon, "A", PW_A)

        assert response.status_code == 302
        assert location_path(response) == "/lecture"
        page = anon.get("/lecture?participant_id=A")
        assert page.status_code == 200
        assert displayed_participant_id(page.get_data(as_text=True)) == "A"

    def test_ac1_login_page_is_served_with_a_form(self, anon) -> None:
        response = anon.get("/login")

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'name="participant_id"' in html
        assert 'name="password"' in html
        assert 'action="/login"' in html


# ---------------------------------------------------------------- AC2


class TestAc2WrongCredentials:
    @pytest.mark.parametrize(
        ("participant_id", "password"),
        [
            ("A", "wrong-password"),
            ("nobody", PW_A),
            ("", PW_A),
            ("A", ""),
        ],
        ids=["wrong-password", "unknown-id", "empty-id", "empty-password"],
    )
    def test_ac2_failure_is_401_with_the_failure_message_and_no_session(
        self, anon, participant_id, password
    ) -> None:
        response = post_login(anon, participant_id, password)

        assert response.status_code == 401
        assert LOGIN_FAILURE_MESSAGE in response.get_data(as_text=True)
        follow = anon.get("/lecture?participant_id=A")
        assert follow.status_code == 302
        assert location_path(follow) == "/login"

    def test_ac2_the_four_failures_are_indistinguishable(self, anon) -> None:
        cases = [("A", "wrong-password"), ("nobody", PW_A), ("", PW_A), ("A", "")]
        responses = [post_login(anon, pid, pw) for pid, pw in cases]

        assert {r.status_code for r in responses} == {401}
        message_lines = []
        for r in responses:
            html = r.get_data(as_text=True)
            assert LOGIN_FAILURE_MESSAGE in html
            # 区別できる情報(存在しない・停止・パスワード違い)を文言に含めない
            for revealing in ("存在しません", "停止", "見つかりません"):
                assert revealing not in html
            message_lines.append(html.count(LOGIN_FAILURE_MESSAGE))
        assert len(set(message_lines)) == 1


# ---------------------------------------------------------------- AC3


class TestAc3ReissuedPassword:
    def test_ac3_old_password_fails_and_new_password_works_after_reissue(
        self, monkeypatch, tmp_path
    ) -> None:
        path = write_credentials_file(
            tmp_path / "creds" / "participants.json", [make_entry("A", "old-password-0123456789")]
        )
        monkeypatch.setenv(CREDENTIALS_ENV, str(path))
        app_before, _ = build_app(monkeypatch, tmp_path)
        assert post_login(app_before.test_client(), "A", "old-password-0123456789").status_code == 302

        # 再発行: 同じ ID に新しいパスワードのハッシュ。更新後の設定ファイルでアプリを起動し直す
        write_credentials_file(path, [make_entry("A", "new-password-0123456789")])
        app_after, _ = build_app(monkeypatch, tmp_path)
        client = app_after.test_client()

        assert post_login(client, "A", "old-password-0123456789").status_code == 401
        assert post_login(client, "A", "new-password-0123456789").status_code == 302


# ---------------------------------------------------------------- AC4


class TestAc4RedirectTarget:
    def test_ac4_unauthenticated_reflect_goes_to_login_and_back_to_reflect(self, anon) -> None:
        first = anon.get("/reflect")
        assert first.status_code == 302
        assert location_path(first) == "/login"
        next_values = parse_qs(urlsplit(first.headers["Location"]).query).get("next")
        assert next_values and urlsplit(next_values[0]).path == "/reflect"

        login = post_login(anon, "A", PW_A, next_path=next_values[0])

        assert login.status_code == 302
        assert location_path(login) == "/reflect"
        assert location_host(login) in ("", "localhost")

    def test_ac4_unauthenticated_lecture_goes_back_to_lecture(self, anon) -> None:
        first = anon.get("/lecture")
        next_values = parse_qs(urlsplit(first.headers["Location"]).query).get("next")
        assert next_values

        login = post_login(anon, "A", PW_A, next_path=next_values[0])

        assert location_path(login) == "/lecture"

    def test_ac4_direct_login_goes_to_lecture(self, anon) -> None:
        assert anon.get("/login").status_code == 200

        login = post_login(anon, "A", PW_A)

        assert login.status_code == 302
        assert location_path(login) == "/lecture"

    @pytest.mark.parametrize(
        "next_path",
        [
            "https://evil.example/steal",
            "//evil.example/steal",
            "http://evil.example/lecture",
            "/api/last-updated",
            "/research/dialog-logs",
            "/login",
            "javascript:alert(1)",
            "",
        ],
    )
    def test_ac4_outside_or_non_participant_targets_fall_back_to_lecture(
        self, anon, next_path
    ) -> None:
        login = post_login(anon, "A", PW_A, next_path=next_path)

        assert login.status_code == 302
        assert location_host(login) in ("", "localhost")
        assert "evil.example" not in login.headers["Location"]
        assert location_path(login) == "/lecture"


# ---------------------------------------------------------------- AC5


class TestAc5Logout:
    def test_ac5_logout_clears_the_login_state(self, anon) -> None:
        _logged_in(anon)
        assert anon.get("/api/last-updated?participant_id=A").status_code == 200

        response = anon.post("/logout")

        assert response.status_code == 302
        assert location_path(response) == "/login"
        page = anon.get("/lecture?participant_id=A")
        assert page.status_code == 302
        assert location_path(page) == "/login"
        assert anon.get("/api/last-updated?participant_id=A").status_code == 401


# ---------------------------------------------------------------- AC24


class TestAc24AlreadyLoggedIn:
    def test_ac24_root_and_login_page_redirect_to_lecture(self, anon) -> None:
        _logged_in(anon)

        for path in ("/", "/login"):
            response = anon.get(path)
            assert response.status_code == 302, path
            assert location_path(response) == "/lecture", path


# ---------------------------------------------------------------- AC27


class TestAc27SuspendedParticipant:
    def test_ac27_suspended_id_with_correct_password_gets_the_same_401(self, anon) -> None:
        suspended = post_login(anon, "S", PW_S)
        wrong = post_login(anon, "A", "wrong-password")

        assert suspended.status_code == 401 == wrong.status_code
        assert LOGIN_FAILURE_MESSAGE in suspended.get_data(as_text=True)
        # 区別できる情報を出さない
        assert "停止" not in suspended.get_data(as_text=True)
        follow = anon.get("/lecture?participant_id=S")
        assert follow.status_code == 302
        assert location_path(follow) == "/login"


# ---------------------------------------------------------------- AC21


def _session_cookie_headers(response) -> list[str]:
    return response.headers.getlist("Set-Cookie")


class TestAc21CookieAttributes:
    def test_ac21_default_cookie_is_httponly_samesite_lax_and_secure(
        self, monkeypatch, tmp_path, creds_path
    ) -> None:
        monkeypatch.delenv(SECURE_DISABLED_ENV, raising=False)
        app, _ = build_app(monkeypatch, tmp_path)

        response = post_login(app.test_client(), "A", PW_A)

        cookies = _session_cookie_headers(response)
        assert cookies, "ログイン成功の応答でセッション Cookie が発行される"
        for header in cookies:
            lowered = header.lower()
            assert "httponly" in lowered
            assert "samesite=lax" in lowered
            assert "secure" in lowered.replace("samesite", "")

    @pytest.mark.parametrize("value", ["0", "", "true", "yes"])
    def test_ac21_only_the_value_1_removes_secure(
        self, monkeypatch, tmp_path, creds_path, value
    ) -> None:
        monkeypatch.setenv(SECURE_DISABLED_ENV, value)
        app, _ = build_app(monkeypatch, tmp_path)

        response = post_login(app.test_client(), "A", PW_A)

        header = _session_cookie_headers(response)[0].lower()
        assert "secure" in header.replace("samesite", "")

    def test_ac21_env_1_removes_secure_but_keeps_httponly_and_samesite(
        self, monkeypatch, tmp_path, creds_path
    ) -> None:
        monkeypatch.setenv(SECURE_DISABLED_ENV, "1")
        app, _ = build_app(monkeypatch, tmp_path)

        response = post_login(app.test_client(), "A", PW_A)

        cookies = _session_cookie_headers(response)
        assert cookies, "ログイン成功の応答でセッション Cookie が発行される"
        for header in cookies:
            lowered = header.lower()
            assert "httponly" in lowered
            assert "samesite=lax" in lowered
            assert "secure" not in lowered.replace("samesite", "")

    def test_ac21_cookie_value_does_not_contain_password_or_hash(
        self, monkeypatch, tmp_path, creds_path
    ) -> None:
        app, _ = build_app(monkeypatch, tmp_path)
        response = post_login(app.test_client(), "A", PW_A)
        stored_hash = json.loads(creds_path.read_text(encoding="utf-8"))["participants"][0]["password_hash"]

        header = _session_cookie_headers(response)[0]
        value = header.split(";", 1)[0].split("=", 1)[1]
        assert PW_A not in header
        assert stored_hash not in header
        # 署名つきセッションの中身(復号した辞書)にも、パスワードとハッシュは入らない
        serializer = app.session_interface.get_signing_serializer(app)
        payload = json.dumps(serializer.loads(value), ensure_ascii=False)
        assert PW_A not in payload
        assert stored_hash not in payload
        assert "password" not in payload.lower()


# ---------------------------------------------------------------- AC22


class TestAc22LoginExpiry:
    @pytest.fixture
    def timed(self, monkeypatch, tmp_path, creds_path):
        now = [T0]
        app, _ = build_app(monkeypatch, tmp_path, clock=lambda: now[0])
        client = app.test_client()
        return client, now

    def test_ac22_valid_at_11h59m_and_expired_at_12h01m(self, timed) -> None:
        client, now = timed
        _logged_in(client)

        now[0] = T0 + timedelta(hours=11, minutes=59)
        assert client.get("/lecture?participant_id=A").status_code == 200
        assert client.get("/api/last-updated?participant_id=A").status_code == 200

        now[0] = T0 + timedelta(hours=12, minutes=1)
        page = client.get("/lecture?participant_id=A")
        assert page.status_code == 302
        assert location_path(page) == "/login"
        assert client.get("/api/last-updated?participant_id=A").status_code == 401

    def test_ac22_requests_in_between_do_not_extend_the_expiry(self, timed) -> None:
        client, now = timed
        _logged_in(client)

        for hours in (3, 7, 11):
            now[0] = T0 + timedelta(hours=hours)
            assert client.get("/api/last-updated?participant_id=A").status_code == 200

        # 最後の要求(11時間)から1時間1分後でも、ログインから12時間を過ぎていれば期限切れ
        now[0] = T0 + timedelta(hours=12, minutes=1)
        assert client.get("/api/last-updated?participant_id=A").status_code == 401

    def test_ac22_can_log_in_again_after_expiry(self, timed) -> None:
        client, now = timed
        _logged_in(client)
        now[0] = T0 + timedelta(hours=13)
        assert client.get("/api/last-updated?participant_id=A").status_code == 401

        assert post_login(client, "A", PW_A).status_code == 302

        assert client.get("/api/last-updated?participant_id=A").status_code == 200
        # 新しいログインから数え直す
        now[0] = T0 + timedelta(hours=13 + 11, minutes=59)
        assert client.get("/api/last-updated?participant_id=A").status_code == 200
