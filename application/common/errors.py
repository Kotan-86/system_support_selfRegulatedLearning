# 仕様: docs/spec/application-error-handling.md#エラーステータス一覧
"""アプリケーション層の ErrorCode と AppError 階層。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    """機械可読なエラー識別子。interfaces 層が HTTP ステータスへ変換する。"""

    # NotFound（HTTP 404）
    LECTURE_NOT_FOUND = "LECTURE_NOT_FOUND"
    LEARNING_SESSION_NOT_FOUND = "LEARNING_SESSION_NOT_FOUND"
    TUTOR_SESSION_NOT_FOUND = "TUTOR_SESSION_NOT_FOUND"

    # Conflict（HTTP 409）
    DUPLICATE_LEARNING_SESSION = "DUPLICATE_LEARNING_SESSION"
    TUTOR_SESSION_POLICY_VIOLATION = "TUTOR_SESSION_POLICY_VIOLATION"

    # Validation（HTTP 400）
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_VIEWING_EVENT = "INVALID_VIEWING_EVENT"
    UNKNOWN_QUESTION_INDEX = "UNKNOWN_QUESTION_INDEX"
    INVALID_QUIZ_ATTEMPT = "INVALID_QUIZ_ATTEMPT"
    EMPTY_USER_MESSAGE = "EMPTY_USER_MESSAGE"
    EXPORT_DATA_INTEGRITY = "EXPORT_DATA_INTEGRITY"
    EXPORT_FILTER_REQUIRED = "EXPORT_FILTER_REQUIRED"

    # 外部依存障害（HTTP 502 等）
    LLM_GATEWAY_ERROR = "LLM_GATEWAY_ERROR"


VALIDATION_ERROR_CODES: frozenset[ErrorCode] = frozenset(
    {
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.INVALID_VIEWING_EVENT,
        ErrorCode.UNKNOWN_QUESTION_INDEX,
        ErrorCode.INVALID_QUIZ_ATTEMPT,
        ErrorCode.EMPTY_USER_MESSAGE,
        ErrorCode.EXPORT_DATA_INTEGRITY,
        ErrorCode.EXPORT_FILTER_REQUIRED,
    }
)

CONFLICT_ERROR_CODES: frozenset[ErrorCode] = frozenset(
    {
        ErrorCode.DUPLICATE_LEARNING_SESSION,
        ErrorCode.TUTOR_SESSION_POLICY_VIOLATION,
    }
)


@dataclass(frozen=True)
class AppError(Exception):
    """アプリケーション層の失敗を表す基底例外。Result の Err に載せる。"""

    code: ErrorCode
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True, init=False)
class ValidationError(AppError):
    """入力検証・不変条件違反。code で汎用とサブ種別を区別する。"""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.VALIDATION_ERROR,
    ) -> None:
        if code not in VALIDATION_ERROR_CODES:
            raise ValueError(f"{code!r} is not a validation ErrorCode")
        super().__init__(code, message)


@dataclass(frozen=True, init=False)
class LectureNotFoundError(AppError):
    """講義カタログに lecture_id が無い。"""

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.LECTURE_NOT_FOUND, message)


@dataclass(frozen=True, init=False)
class LearningSessionNotFoundError(AppError):
    """learning_session_id 指定で Learning Session が無い。"""

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.LEARNING_SESSION_NOT_FOUND, message)


@dataclass(frozen=True, init=False)
class TutorSessionNotFoundError(AppError):
    """指定 tutor_session_id が無い。"""

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.TUTOR_SESSION_NOT_FOUND, message)


@dataclass(frozen=True, init=False)
class ConflictError(AppError):
    """競合・ポリシー違反。code で重複種別を区別する。"""

    def __init__(self, message: str, code: ErrorCode) -> None:
        if code not in CONFLICT_ERROR_CODES:
            raise ValueError(f"{code!r} is not a conflict ErrorCode")
        super().__init__(code, message)

    @classmethod
    def duplicate_learning_session(cls, message: str) -> ConflictError:
        return cls(message, ErrorCode.DUPLICATE_LEARNING_SESSION)

    @classmethod
    def tutor_session_policy_violation(cls, message: str) -> ConflictError:
        return cls(message, ErrorCode.TUTOR_SESSION_POLICY_VIOLATION)


@dataclass(frozen=True, init=False)
class LlmGatewayError(AppError):
    """LLM 呼び出し失敗・空応答。"""

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.LLM_GATEWAY_ERROR, message)
