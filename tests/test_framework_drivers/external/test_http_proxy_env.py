# 仕様: docs/spec/framework-drivers-layer.md#環境変数必須推奨
from __future__ import annotations

import os

from framework_drivers.external.http_proxy_env import (
    http_proxy_environment,
    is_proxy_env_configured,
    should_use_http_proxy,
)


def test_should_use_http_proxy_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("USE_HTTP_PROXY", "true")
    assert should_use_http_proxy() is True


def test_should_not_use_http_proxy_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("USE_HTTP_PROXY", "false")
    assert should_use_http_proxy() is False


def test_http_proxy_environment_clears_proxy_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("USE_HTTP_PROXY", "false")
    monkeypatch.setenv("HTTPS_PROXY", "http://gw.example:8080")
    monkeypatch.setenv("HTTP_PROXY", "http://gw.example:8080")

    assert is_proxy_env_configured() is True

    with http_proxy_environment():
        assert is_proxy_env_configured() is False

    assert os.environ["HTTPS_PROXY"] == "http://gw.example:8080"
    assert os.environ["HTTP_PROXY"] == "http://gw.example:8080"


def test_http_proxy_environment_keeps_proxy_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("USE_HTTP_PROXY", "true")
    monkeypatch.setenv("HTTPS_PROXY", "http://gw.example:8080")

    with http_proxy_environment():
        assert os.environ["HTTPS_PROXY"] == "http://gw.example:8080"
