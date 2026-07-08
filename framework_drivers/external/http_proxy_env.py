# 仕様: docs/spec/framework-drivers-layer.md#環境変数必須推奨
"""USE_HTTP_PROXY に応じて外部 HTTP クライアント向けのプロキシ環境変数を制御する。"""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
)


def should_use_http_proxy() -> bool:
    """学内プロキシ経由が必要なとき True。"""
    return os.environ.get("USE_HTTP_PROXY", "").lower() in ("1", "true", "yes")


def is_proxy_env_configured() -> bool:
    """HTTP(S)_PROXY 等が環境変数に設定されているか。"""
    return any(os.environ.get(key) for key in _PROXY_ENV_KEYS)


@contextmanager
def http_proxy_environment() -> Iterator[None]:
    """USE_HTTP_PROXY=false のときプロキシ環境変数を一時的に無効化する。"""
    if should_use_http_proxy():
        yield
        return

    saved = {key: os.environ.pop(key) for key in _PROXY_ENV_KEYS if key in os.environ}
    try:
        yield
    finally:
        for key, value in saved.items():
            os.environ[key] = value
