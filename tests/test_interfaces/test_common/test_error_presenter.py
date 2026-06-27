# 仕様: docs/spec/interfaces-layer.md#ErrorViewModel
# 仕様: docs/spec/application-error-handling.md#エラーステータス一覧
"""error_presenter の単体テスト。"""
from __future__ import annotations

import pytest

from application.common.errors import (
    CONFLICT_ERROR_CODES,
    VALIDATION_ERROR_CODES,
    ConflictError,
    ErrorCode,
    LearningSessionNotFoundError,
    LectureNotFoundError,
    LlmGatewayError,
    TutorSessionNotFoundError,
    ValidationError,
    VideoMetadataGatewayError,
)
from interfaces.common.error_presenter import present_error, status_kind_for_error_code
from interfaces.learning.view_models.errors import StatusKind

ALL_ERROR_CODES: tuple[ErrorCode, ...] = tuple(ErrorCode)

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


class TestStatusKindForErrorCode:
    """ErrorCode → status_kind のマッピングを検証する。"""

    @pytest.mark.parametrize("code", sorted(NOT_FOUND_ERROR_CODES, key=lambda c: c.value))
    def test_not_found_codes_map_to_not_found(self, code: ErrorCode) -> None:
        assert status_kind_for_error_code(code) == StatusKind.NOT_FOUND

    @pytest.mark.parametrize("code", sorted(CONFLICT_ERROR_CODES, key=lambda c: c.value))
    def test_conflict_codes_map_to_conflict(self, code: ErrorCode) -> None:
        assert status_kind_for_error_code(code) == StatusKind.CONFLICT

    @pytest.mark.parametrize("code", sorted(VALIDATION_ERROR_CODES, key=lambda c: c.value))
    def test_validation_codes_map_to_validation(self, code: ErrorCode) -> None:
        assert status_kind_for_error_code(code) == StatusKind.VALIDATION

    @pytest.mark.parametrize("code", sorted(GATEWAY_ERROR_CODES, key=lambda c: c.value))
    def test_gateway_codes_map_to_gateway(self, code: ErrorCode) -> None:
        assert status_kind_for_error_code(code) == StatusKind.GATEWAY

    def test_all_error_codes_have_status_kind(self) -> None:
        for code in ALL_ERROR_CODES:
            status_kind_for_error_code(code)


class TestPresentError:
    """代表 AppError の ErrorViewModel 変換を検証する。"""

    def test_lecture_not_found_error(self) -> None:
        error = LectureNotFoundError("講義が見つかりません")

        view_model = present_error(error)

        assert view_model.error_code == "LECTURE_NOT_FOUND"
        assert view_model.message == "講義が見つかりません"
        assert view_model.status_kind == StatusKind.NOT_FOUND

    def test_learning_session_not_found_error(self) -> None:
        error = LearningSessionNotFoundError("セッションが見つかりません")

        view_model = present_error(error)

        assert view_model.error_code == "LEARNING_SESSION_NOT_FOUND"
        assert view_model.status_kind == StatusKind.NOT_FOUND

    def test_tutor_session_not_found_error(self) -> None:
        error = TutorSessionNotFoundError("チューターセッションが見つかりません")

        view_model = present_error(error)

        assert view_model.error_code == "TUTOR_SESSION_NOT_FOUND"
        assert view_model.status_kind == StatusKind.NOT_FOUND

    def test_conflict_error(self) -> None:
        error = ConflictError.duplicate_learning_session("既にセッションが存在します")

        view_model = present_error(error)

        assert view_model.error_code == "DUPLICATE_LEARNING_SESSION"
        assert view_model.status_kind == StatusKind.CONFLICT

    def test_validation_error(self) -> None:
        error = ValidationError("participant_id must not be empty")

        view_model = present_error(error)

        assert view_model.error_code == "VALIDATION_ERROR"
        assert view_model.status_kind == StatusKind.VALIDATION

    def test_invalid_viewing_event_validation_error(self) -> None:
        error = ValidationError("invalid event", code=ErrorCode.INVALID_VIEWING_EVENT)

        view_model = present_error(error)

        assert view_model.error_code == "INVALID_VIEWING_EVENT"
        assert view_model.status_kind == StatusKind.VALIDATION

    def test_llm_gateway_error(self) -> None:
        error = LlmGatewayError("LLM 呼び出しに失敗しました")

        view_model = present_error(error)

        assert view_model.error_code == "LLM_GATEWAY_ERROR"
        assert view_model.status_kind == StatusKind.GATEWAY

    def test_video_metadata_gateway_error(self) -> None:
        error = VideoMetadataGatewayError("動画メタデータ API が利用できません")

        view_model = present_error(error)

        assert view_model.error_code == "VIDEO_METADATA_GATEWAY_ERROR"
        assert view_model.status_kind == StatusKind.GATEWAY
