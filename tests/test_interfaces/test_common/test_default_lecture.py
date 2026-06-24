# 仕様: docs/spec/interfaces-layer.md#default_lecture
"""default_lecture の単体テスト。"""
from __future__ import annotations

import os

import pytest

from domain.shared.ids import LectureId
from interfaces.common.default_lecture import (
    DEFAULT_LECTURE_ID_VALUE,
    ENV_VAR_NAME,
    resolve_default_lecture_id,
)


class TestResolveDefaultLectureId:
    """既定講義 ID の解決を検証する。"""

    def test_returns_constant_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(ENV_VAR_NAME, raising=False)

        lecture_id = resolve_default_lecture_id()

        assert lecture_id == LectureId(DEFAULT_LECTURE_ID_VALUE)

    def test_uses_env_var_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "lecture-from-env")

        lecture_id = resolve_default_lecture_id()

        assert lecture_id == LectureId("lecture-from-env")

    def test_strips_env_var_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "  lecture-trimmed  ")

        lecture_id = resolve_default_lecture_id()

        assert lecture_id == LectureId("lecture-trimmed")

    def test_falls_back_to_constant_when_env_is_blank(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "   ")

        lecture_id = resolve_default_lecture_id()

        assert lecture_id == LectureId(DEFAULT_LECTURE_ID_VALUE)
