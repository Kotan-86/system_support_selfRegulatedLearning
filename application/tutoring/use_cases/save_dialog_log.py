# 仕様: docs/spec/dialog-log-save.md#PBI-A-1-対話ログの保存サーバー側
"""SaveDialogLog ユースケース。"""
from __future__ import annotations

from application.common.errors import AppError, TutorSessionNotFoundError
from application.common.result import Result, err, ok
from application.learning.dto.start_or_get_learning_session import (
    StartOrGetLearningSessionRequest,
)
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from application.tutoring.dto.save_dialog_log import (
    DialogLog,
    SaveDialogLogRequest,
    SaveDialogLogResponse,
)
from application.tutoring.dto.start_or_get_tutor_session import (
    StartOrGetTutorSessionRequest,
)
from application.tutoring.ports.dialog_log_repository import DialogLogRepository
from application.tutoring.ports.tutor_session_repository import TutorSessionRepository
from application.tutoring.use_cases.start_or_get_tutor_session import (
    StartOrGetTutorSessionUseCase,
)


class SaveDialogLogUseCase:
    """対話セッションの全発言を対話ログとして保存する(上書き)。"""

    def __init__(
        self,
        start_or_get_learning: StartOrGetLearningSessionUseCase,
        start_or_get_tutor: StartOrGetTutorSessionUseCase,
        tutor_repository: TutorSessionRepository,
        dialog_log_repository: DialogLogRepository,
    ) -> None:
        self._start_or_get_learning = start_or_get_learning
        self._start_or_get_tutor = start_or_get_tutor
        self._tutor_repository = tutor_repository
        self._dialog_log_repository = dialog_log_repository

    def execute(
        self, request: SaveDialogLogRequest
    ) -> Result[SaveDialogLogResponse, AppError]:
        # 学習セッション・対話セッションは、無ければここで作る(N2)
        learning_result = self._start_or_get_learning.execute(
            StartOrGetLearningSessionRequest(
                learner_id=request.learner_id,
                lecture_id=request.lecture_id,
                started_at=request.received_at,
            )
        )
        if learning_result.is_err:
            return learning_result  # type: ignore[return-value]
        learning_session_id = learning_result.value.session_id

        tutor_result = self._start_or_get_tutor.execute(
            StartOrGetTutorSessionRequest(
                learning_session_id=learning_session_id,
                started_at=request.received_at,
            )
        )
        if tutor_result.is_err:
            return tutor_result  # type: ignore[return-value]
        tutor_session_id = tutor_result.value.tutor_session_id

        session = self._tutor_repository.find_by_id(tutor_session_id)
        if session is None:
            return err(
                TutorSessionNotFoundError(
                    f"tutor session not found: {tutor_session_id!s}"
                )
            )

        self._dialog_log_repository.save(
            DialogLog(
                participant_id=str(request.learner_id),
                lecture_id=str(request.lecture_id),
                learning_session_id=str(learning_session_id),
                tutor_session_id=str(tutor_session_id),
                ended_at=request.received_at,
                end_method=request.end_method,
                messages=session.messages,
            )
        )
        return ok(
            SaveDialogLogResponse(
                tutor_session_id=tutor_session_id,
                ended_at=request.received_at,
                end_method=request.end_method,
            )
        )
