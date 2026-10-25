# 仕様: docs/spec/https-enforcement.md#受入基準
"""HTTPS の強制(元の方式が https でない要求を処理しない。https の応答に HSTS を付ける)。

元の方式は前段(Cloud Run)の X-Forwarded-Proto で判定する。ヘッダがなければ http とみなす。
複数の値(`http, https`)は最後の値で決める。解除は環境変数 HTTPS_ENFORCEMENT_DISABLED=1 のときだけ。
"""
from __future__ import annotations

import os
from typing import Final
from urllib.parse import quote

import flask

HTTPS_ENFORCEMENT_DISABLED_ENV: Final = "HTTPS_ENFORCEMENT_DISABLED"
HSTS_VALUE: Final = "max-age=31536000"
_FORWARDED_PROTO: Final = "X-Forwarded-Proto"


def is_enforcement_disabled(environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(HTTPS_ENFORCEMENT_DISABLED_ENV) == "1"


def is_https_request(request: flask.Request) -> bool:
    raw = request.headers.get(_FORWARDED_PROTO, "")
    last = raw.split(",")[-1].strip().lower()
    return last == "https"


def register_https_enforcement(app: flask.Flask) -> None:
    """他のどの before_request よりも先に登録すること(認証・DB の前に判定する)。"""
    if is_enforcement_disabled():
        return

    @app.before_request
    def _reject_non_https() -> flask.Response | None:
        request = flask.request
        if is_https_request(request):
            return None
        if request.method in ("GET", "HEAD"):
            location = f"https://{request.host}{quote(request.path, safe='/')}"
            query = request.query_string.decode("latin-1")
            if query:
                location += f"?{query}"
            response = flask.Response("", status=301)
            response.headers["Location"] = location
            return response
        return flask.Response("HTTPS required", status=400, mimetype="text/plain")

    @app.after_request
    def _add_hsts(response: flask.Response) -> flask.Response:
        if is_https_request(flask.request):
            response.headers["Strict-Transport-Security"] = HSTS_VALUE
        return response
