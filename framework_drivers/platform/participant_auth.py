# 仕様: docs/spec/participant-login.md#1-ログインとログアウト
# 仕様: docs/spec/participant-login.md#2-未ログインの要求の拒否fr-51
# 仕様: docs/spec/participant-login.md#6-セッションの安全性の設定
"""参加者のログイン・ログアウト、未ログインの拒否、セッションの設定。"""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Final
from urllib.parse import urlsplit

import flask

from framework_drivers.platform.participant_credentials import (
    STATUS_ACTIVE,
    ParticipantCredential,
    hash_password,
    verify_password,
)
from framework_drivers.platform.research_auth import is_research_path

SECRET_KEY_ENV: Final = "SECRET_KEY"
LEGACY_DEFAULT_SECRET_KEY: Final = "tutor_secret_key"
SESSION_COOKIE_SECURE_DISABLED_ENV: Final = "SESSION_COOKIE_SECURE_DISABLED"
SESSION_LIFETIME: Final = timedelta(hours=12)
LOGIN_PATH: Final = "/login"
LOGOUT_PATH: Final = "/logout"
NEXT_PARAM: Final = "next"
DEFAULT_AFTER_LOGIN_PATH: Final = "/lecture"
LOGIN_FAILURE_MESSAGE: Final[str] = "IDまたはパスワードが正しくありません。"
SESSION_KEY_PARTICIPANT_ID: Final = "participant_id"
SESSION_KEY_LOGIN_AT: Final = "login_at"

_ALLOWED_NEXT_PATHS: Final = ("/lecture", "/reflect")
_STATIC_PREFIX: Final = "/static/"


class StartupConfigError(RuntimeError):
    """SECRET_KEY の不備。文言に SECRET_KEY を含む。"""


def load_secret_key(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    value = env.get(SECRET_KEY_ENV) or ""
    if not value or value == LEGACY_DEFAULT_SECRET_KEY:
        raise StartupConfigError(
            f"環境変数 {SECRET_KEY_ENV} を設定してください"
            f"(未設定・空・{LEGACY_DEFAULT_SECRET_KEY} は使えません)"
        )
    return value


def _is_api_path(path: str) -> bool:
    return path == "/chat" or path == "/api" or path.startswith("/api/")


def _safe_next(raw: str | None) -> str:
    """ログイン後の移動先。サイト内の /lecture か /reflect のときだけ使う。"""
    if not raw:
        return DEFAULT_AFTER_LOGIN_PATH
    parts = urlsplit(raw)
    if parts.scheme or parts.netloc or "\\" in raw or parts.path not in _ALLOWED_NEXT_PATHS:
        return DEFAULT_AFTER_LOGIN_PATH
    return parts.path + (f"?{parts.query}" if parts.query else "")


def current_participant_id() -> str:
    return flask.g.participant_id


def register_participant_auth(
    app: flask.Flask,
    *,
    credentials: Mapping[str, ParticipantCredential],
    clock: Callable[[], datetime],
    environ: Mapping[str, str] | None = None,
) -> None:
    env = os.environ if environ is None else environ
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=env.get(SESSION_COOKIE_SECURE_DISABLED_ENV) != "1",
        PERMANENT_SESSION_LIFETIME=SESSION_LIFETIME,
        SESSION_REFRESH_EACH_REQUEST=False,
    )
    # 未登録 ID でも照合の手間を揃える(ID の有無を応答時間から推測されにくくする)
    dummy = ParticipantCredential("", "", STATUS_ACTIVE, "", hash_password(os.urandom(16).hex()))

    def _logged_in_id() -> str | None:
        participant_id = flask.session.get(SESSION_KEY_PARTICIPANT_ID)
        login_at = flask.session.get(SESSION_KEY_LOGIN_AT)
        if not isinstance(participant_id, str) or not isinstance(login_at, (int, float)):
            return None
        elapsed = clock().timestamp() - login_at
        if elapsed < 0 or elapsed >= SESSION_LIFETIME.total_seconds():
            return None
        return participant_id

    def _login_page(status: int, next_value: str, failed: bool) -> flask.Response:
        html = flask.render_template(
            "login.html",
            next_value=next_value,
            failure_message=LOGIN_FAILURE_MESSAGE if failed else "",
        )
        return flask.make_response(html, status)

    @app.before_request
    def _require_participant_login() -> flask.Response | None:
        path = flask.request.path
        if is_research_path(path) or path.startswith(_STATIC_PREFIX):
            return None
        participant_id = _logged_in_id()
        if path in (LOGIN_PATH, LOGOUT_PATH):
            if path == LOGIN_PATH and flask.request.method == "GET" and participant_id:
                return flask.redirect(DEFAULT_AFTER_LOGIN_PATH, 302)
            return None
        if participant_id is not None:
            flask.g.participant_id = participant_id
            return None
        if _is_api_path(path):
            response = flask.jsonify({"error": "unauthorized"})
            response.status_code = 401
            return response
        target = flask.request.full_path.rstrip("?")
        return flask.redirect(flask.url_for("login", **{NEXT_PARAM: target}), 302)

    @app.after_request
    def _no_store(response: flask.Response) -> flask.Response:
        path = flask.request.path
        if not (is_research_path(path) or path.startswith(_STATIC_PREFIX)):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.route(LOGIN_PATH, methods=["GET", "POST"])
    def login():
        if flask.request.method == "GET":
            return _login_page(200, _safe_next(flask.request.args.get(NEXT_PARAM)), False)
        participant_id = flask.request.form.get("participant_id", "")
        password = flask.request.form.get("password", "")
        next_raw = flask.request.form.get(NEXT_PARAM)
        credential = credentials.get(participant_id)
        password_ok = verify_password(credential or dummy, password)
        if not (credential and password_ok and credential.status == STATUS_ACTIVE and password):
            return _login_page(401, _safe_next(next_raw), True)
        flask.session.clear()
        flask.session.permanent = True
        flask.session[SESSION_KEY_PARTICIPANT_ID] = participant_id
        flask.session[SESSION_KEY_LOGIN_AT] = int(clock().timestamp())
        return flask.redirect(_safe_next(next_raw), 302)

    @app.route(LOGOUT_PATH, methods=["POST"])
    def logout():
        flask.session.clear()
        return flask.redirect(LOGIN_PATH, 302)
