# 仕様: docs/spec/interfaces-layer.md#ErrorViewModel
# 仕様: docs/spec/application-error-handling.md#エラーステータス一覧
"""AppError を ErrorViewModel へ変換する。"""
from __future__ import annotations

from application.common.errors import (
    CONFLICT_ERROR_CODES,
    VALIDATION_ERROR_CODES,
    AppError,
    ErrorCode,
)
from interfaces.learning.view_models.errors import ErrorViewModel, StatusKind

NOT_FOUND_ERROR_CODES: frozenset[ErrorCode] = frozenset(
    {
        ErrorCode.LECTURE_NOT_FOUND,
        ErrorCode.LEARNING_SESSION_NOT_FOUND,
        ErrorCode.TUTOR_SESSION_NOT_FOUND,
    }
)

GATEWAY_ERROR_CODES: frozenset[ErrorCode] = frozenset(
    {
        ErrorCode.LLM_GATEWAY_ERROR,
        ErrorCode.VIDEO_METADATA_GATEWAY_ERROR,
    }
)


def status_kind_for_error_code(code: ErrorCode) -> StatusKind:
    """ErrorCode を status_kind へマッピングする。"""
    if code in NOT_FOUND_ERROR_CODES:
        return StatusKind.NOT_FOUND
    if code in CONFLICT_ERROR_CODES:
        return StatusKind.CONFLICT
    if code in VALIDATION_ERROR_CODES:
        return StatusKind.VALIDATION
    if code in GATEWAY_ERROR_CODES:
        return StatusKind.GATEWAY
    raise ValueError(f"Unknown ErrorCode for status_kind mapping: {code!r}")


def present_error(error: AppError) -> ErrorViewModel:
    """AppError を ErrorViewModel へ変換する。"""
    return ErrorViewModel(
        error_code=error.code.value,
        message=error.message,
        status_kind=status_kind_for_error_code(error.code),
    )
