# 仕様: docs/spec/application-error-handling.md#エラーステータス一覧
"""application.common.errors の単体テスト。"""
from __future__ import annotations

import pytest

from application.common.errors import (
    CONFLICT_ERROR_CODES,
    VALIDATION_ERROR_CODES,
    AppError,
    ConflictError,
    ErrorCode,
    LearningSessionNotFoundError,
    LectureNotFoundError,
    LlmGatewayError,
    TutorSessionNotFoundError,
    ValidationError,
)

ALL_ERROR_CODES: tuple[ErrorCode, ...] = tuple(ErrorCode)

NOT_FOUND_ERROR_CODES: frozenset[ErrorCode] = frozenset(
    {
        ErrorCode.LECTURE_NOT_FOUND,
        ErrorCode.LEARNING_SESSION_NOT_FOUND,
        ErrorCode.TUTOR_SESSION_NOT_FOUND,
    }
)

EXTERNAL_ERROR_CODES: frozenset[ErrorCode] = frozenset({ErrorCode.LLM_GATEWAY_ERROR})

NON_VALIDATION_ERROR_CODES: frozenset[ErrorCode] = frozenset(ALL_ERROR_CODES) - VALIDATION_ERROR_CODES
NON_CONFLICT_ERROR_CODES: frozenset[ErrorCode] = frozenset(ALL_ERROR_CODES) - CONFLICT_ERROR_CODES


class TestErrorCodePartitionExclusivity:
    """ErrorCode 区分が重複なく全件をカバーすることを検証する。"""

    def test_validation_and_conflict_are_disjoint(self) -> None:
        assert VALIDATION_ERROR_CODES.isdisjoint(CONFLICT_ERROR_CODES)

    def test_validation_and_not_found_are_disjoint(self) -> None:
        assert VALIDATION_ERROR_CODES.isdisjoint(NOT_FOUND_ERROR_CODES)

    def test_conflict_and_not_found_are_disjoint(self) -> None:
        assert CONFLICT_ERROR_CODES.isdisjoint(NOT_FOUND_ERROR_CODES)

    def test_external_codes_are_disjoint_from_other_partitions(self) -> None:
        assert EXTERNAL_ERROR_CODES.isdisjoint(VALIDATION_ERROR_CODES)
        assert EXTERNAL_ERROR_CODES.isdisjoint(CONFLICT_ERROR_CODES)
        assert EXTERNAL_ERROR_CODES.isdisjoint(NOT_FOUND_ERROR_CODES)

    def test_partitions_cover_all_error_codes(self) -> None:
        all_partitions = (
            NOT_FOUND_ERROR_CODES
            | CONFLICT_ERROR_CODES
            | VALIDATION_ERROR_CODES
            | EXTERNAL_ERROR_CODES
        )
        assert all_partitions == frozenset(ALL_ERROR_CODES)

    @pytest.mark.parametrize("code", ALL_ERROR_CODES, ids=lambda code: code.value)
    def test_each_error_code_belongs_to_exactly_one_partition(self, code: ErrorCode) -> None:
        memberships = (
            code in NOT_FOUND_ERROR_CODES,
            code in CONFLICT_ERROR_CODES,
            code in VALIDATION_ERROR_CODES,
            code in EXTERNAL_ERROR_CODES,
        )
        assert sum(memberships) == 1


class TestErrorCode:
    """全 ErrorCode が定義されていることを検証する。"""

    def test_all_error_codes_defined(self) -> None:
        """仕様の 13 種類の ErrorCode が列挙可能である。"""
        assert len(ALL_ERROR_CODES) == 13

    @pytest.mark.parametrize(
        ("code", "value"),
        [
            (ErrorCode.LECTURE_NOT_FOUND, "LECTURE_NOT_FOUND"),
            (ErrorCode.LEARNING_SESSION_NOT_FOUND, "LEARNING_SESSION_NOT_FOUND"),
            (ErrorCode.TUTOR_SESSION_NOT_FOUND, "TUTOR_SESSION_NOT_FOUND"),
            (ErrorCode.DUPLICATE_LEARNING_SESSION, "DUPLICATE_LEARNING_SESSION"),
            (ErrorCode.TUTOR_SESSION_POLICY_VIOLATION, "TUTOR_SESSION_POLICY_VIOLATION"),
            (ErrorCode.VALIDATION_ERROR, "VALIDATION_ERROR"),
            (ErrorCode.INVALID_VIEWING_EVENT, "INVALID_VIEWING_EVENT"),
            (ErrorCode.UNKNOWN_QUESTION_INDEX, "UNKNOWN_QUESTION_INDEX"),
            (ErrorCode.INVALID_QUIZ_ATTEMPT, "INVALID_QUIZ_ATTEMPT"),
            (ErrorCode.EMPTY_USER_MESSAGE, "EMPTY_USER_MESSAGE"),
            (ErrorCode.EXPORT_DATA_INTEGRITY, "EXPORT_DATA_INTEGRITY"),
            (ErrorCode.EXPORT_FILTER_REQUIRED, "EXPORT_FILTER_REQUIRED"),
            (ErrorCode.LLM_GATEWAY_ERROR, "LLM_GATEWAY_ERROR"),
        ],
    )
    def test_error_code_string_value(self, code: ErrorCode, value: str) -> None:
        """ErrorCode の値が機械可読な文字列である。"""
        assert code.value == value
        assert code == value


class TestValidationErrorCodes:
    """Validation 系 ErrorCode の集合を検証する。"""

    def test_validation_error_codes_contains_expected(self) -> None:
        assert VALIDATION_ERROR_CODES == frozenset(
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


class TestConflictErrorCodes:
    """Conflict 系 ErrorCode の集合を検証する。"""

    def test_conflict_error_codes_contains_expected(self) -> None:
        assert CONFLICT_ERROR_CODES == frozenset(
            {
                ErrorCode.DUPLICATE_LEARNING_SESSION,
                ErrorCode.TUTOR_SESSION_POLICY_VIOLATION,
            }
        )


class TestAppErrorConcreteClasses:
    """各具象 AppError クラスが正しい ErrorCode を持つことを検証する。"""

    def test_lecture_not_found_error(self) -> None:
        error = LectureNotFoundError("講義が見つかりません")
        assert error.code == ErrorCode.LECTURE_NOT_FOUND
        assert error.message == "講義が見つかりません"
        assert str(error) == "講義が見つかりません"
        assert isinstance(error, AppError)
        assert isinstance(error, Exception)

    def test_learning_session_not_found_error(self) -> None:
        error = LearningSessionNotFoundError("セッションが見つかりません")
        assert error.code == ErrorCode.LEARNING_SESSION_NOT_FOUND
        assert error.message == "セッションが見つかりません"

    def test_tutor_session_not_found_error(self) -> None:
        error = TutorSessionNotFoundError("チューターセッションが見つかりません")
        assert error.code == ErrorCode.TUTOR_SESSION_NOT_FOUND
        assert error.message == "チューターセッションが見つかりません"

    def test_llm_gateway_error(self) -> None:
        error = LlmGatewayError("LLM 呼び出しに失敗しました")
        assert error.code == ErrorCode.LLM_GATEWAY_ERROR
        assert error.message == "LLM 呼び出しに失敗しました"


class TestValidationError:
    """ValidationError の code 規約を検証する。"""

    def test_default_code_is_validation_error(self) -> None:
        error = ValidationError("入力が不正です")
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.message == "入力が不正です"

    @pytest.mark.parametrize("code", sorted(VALIDATION_ERROR_CODES, key=lambda c: c.value))
    def test_accepts_all_validation_codes(self, code: ErrorCode) -> None:
        error = ValidationError("検証エラー", code=code)
        assert error.code == code

    @pytest.mark.parametrize("code", sorted(NON_VALIDATION_ERROR_CODES, key=lambda c: c.value))
    def test_rejects_all_non_validation_codes(self, code: ErrorCode) -> None:
        with pytest.raises(ValueError, match="is not a validation ErrorCode"):
            ValidationError("不正な code", code=code)


class TestConflictError:
    """ConflictError の code 規約を検証する。"""

    def test_duplicate_learning_session_factory(self) -> None:
        error = ConflictError.duplicate_learning_session("既にセッションが存在します")
        assert error.code == ErrorCode.DUPLICATE_LEARNING_SESSION
        assert error.message == "既にセッションが存在します"

    def test_tutor_session_policy_violation_factory(self) -> None:
        error = ConflictError.tutor_session_policy_violation("ポリシー違反です")
        assert error.code == ErrorCode.TUTOR_SESSION_POLICY_VIOLATION
        assert error.message == "ポリシー違反です"

    @pytest.mark.parametrize("code", sorted(CONFLICT_ERROR_CODES, key=lambda c: c.value))
    def test_accepts_all_conflict_codes(self, code: ErrorCode) -> None:
        error = ConflictError("競合エラー", code=code)
        assert error.code == code

    @pytest.mark.parametrize("code", sorted(NON_CONFLICT_ERROR_CODES, key=lambda c: c.value))
    def test_rejects_all_non_conflict_codes(self, code: ErrorCode) -> None:
        with pytest.raises(ValueError, match="is not a conflict ErrorCode"):
            ConflictError("不正な code", code=code)
