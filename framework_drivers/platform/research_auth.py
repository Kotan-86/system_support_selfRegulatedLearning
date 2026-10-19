# 仕様: docs/spec/research-dialog-download.md#url-と資格情報共有if固定済み2026-10-19
"""研究者の Basic 認証(/research 配下の保護と no-store)。"""
from __future__ import annotations

import hmac
import os
from collections.abc import Mapping
from typing import Final

import flask
from werkzeug.datastructures import Authorization

RESEARCHER_USER_ENV: Final = "RESEARCHER_BASIC_AUTH_USER"
RESEARCHER_PASSWORD_ENV: Final = "RESEARCHER_BASIC_AUTH_PASSWORD"
RESEARCH_PATH_PREFIX: Final = "/research/"


def is_research_path(path: str) -> bool:
    return path == "/research" or path.startswith(RESEARCH_PATH_PREFIX)


def _equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def is_authorized(
    authorization: Authorization | None, environ: Mapping[str, str] | None = None
) -> bool:
    env = os.environ if environ is None else environ
    expected_user = env.get(RESEARCHER_USER_ENV) or ""
    expected_password = env.get(RESEARCHER_PASSWORD_ENV) or ""
    if not expected_user or not expected_password:
        return False
    if authorization is None or authorization.type != "basic":
        return False
    user = authorization.parameters.get("username")
    password = authorization.parameters.get("password")
    if not isinstance(user, str) or not isinstance(password, str):
        return False
    # 両方を必ず比較する(短絡させない)
    user_ok = _equal(user, expected_user)
    password_ok = _equal(password, expected_password)
    return user_ok and password_ok


def unauthorized_response() -> flask.Response:
    response = flask.Response("Unauthorized", status=401, mimetype="text/plain")
    response.headers["WWW-Authenticate"] = 'Basic realm="research", charset="UTF-8"'
    response.headers["Cache-Control"] = "no-store"
    return response


def register_research_auth(app: flask.Flask) -> None:
    @app.before_request
    def _require_researcher() -> flask.Response | None:
        if not is_research_path(flask.request.path):
            return None
        if is_authorized(flask.request.authorization):
            return None
        return unauthorized_response()

    @app.after_request
    def _no_store(response: flask.Response) -> flask.Response:
        if is_research_path(flask.request.path):
            response.headers["Cache-Control"] = "no-store"
        return response
