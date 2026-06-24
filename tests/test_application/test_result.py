# 仕様: docs/spec/application-error-handling.md#共通契約
"""application.common.result の単体テスト。"""
from __future__ import annotations

from application.common.errors import LectureNotFoundError, ValidationError
from application.common.result import Err, Ok, err, ok


class TestOk:
    """Ok の生成と型判別を検証する。"""

    def test_ok_factory_creates_ok_with_value(self) -> None:
        result = ok("success")
        assert isinstance(result, Ok)
        assert result.value == "success"

    def test_ok_is_ok(self) -> None:
        result = ok(42)
        assert result.is_ok is True
        assert result.is_err is False

    def test_ok_with_complex_value(self) -> None:
        payload = {"session_id": "abc-123"}
        result = ok(payload)
        assert result.value == payload


class TestErr:
    """Err の生成と型判別を検証する。"""

    def test_err_factory_creates_err_with_error(self) -> None:
        app_error = ValidationError("入力が不正です")
        result = err(app_error)
        assert isinstance(result, Err)
        assert result.error is app_error

    def test_err_is_err(self) -> None:
        app_error = LectureNotFoundError("講義が見つかりません")
        result = err(app_error)
        assert result.is_ok is False
        assert result.is_err is True

    def test_err_preserves_error_attributes(self) -> None:
        app_error = LectureNotFoundError("講義が見つかりません")
        result = err(app_error)
        assert result.error.message == "講義が見つかりません"
        assert result.error.code.value == "LECTURE_NOT_FOUND"


class TestResultDiscrimination:
    """Ok / Err の判別が相互排他的であることを検証する。"""

    def test_ok_and_err_are_distinct(self) -> None:
        success = ok("value")
        failure = err(ValidationError("失敗"))
        assert success.is_ok and not success.is_err
        assert failure.is_err and not failure.is_ok
