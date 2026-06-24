# 仕様: docs/spec/application-usecase.md#StartOrGetLearningSession
# 仕様: docs/spec/application-error-handling.md#StartOrGetLearningSession
"""StartOrGetLearningSession ユースケース。"""
from __future__ import annotations

from application.common.errors import AppError, ConflictError
from application.common.result import Result, err, ok
from application.common.start_or_get_outcome import StartOrGetOutcome
from application.learning.dto.start_or_get_learning_session import (
    StartOrGetLearningSessionRequest,
    StartOrGetLearningSessionResponse,
)
from application.learning.ports.id_generators import LearningSessionIdGenerator
from application.learning.ports.learning_session_repository import (
    LearningSessionRepository,
)
from domain.learning.learning_session import LearningSession


class StartOrGetLearningSessionUseCase:
    """1 学習者 × 1 講義の LearningSession を確保する。"""

    def __init__(
        self,
        repository: LearningSessionRepository,
        id_generator: LearningSessionIdGenerator,
    ) -> None:
        self._repository = repository
        self._id_generator = id_generator

    def execute(
        self, request: StartOrGetLearningSessionRequest
    ) -> Result[StartOrGetLearningSessionResponse, AppError]:
        validated = request.validate()
        if validated.is_err:
            return validated  # type: ignore[return-value]

        req = validated.value
        existing = self._repository.find_by_learner_and_lecture(
            req.learner_id, req.lecture_id
        )
        if existing is not None:
            return ok(
                StartOrGetLearningSessionResponse(
                    session_id=existing.id,
                    session=existing,
                    outcome=StartOrGetOutcome.RETRIEVED,
                )
            )

        existing_sessions = self._repository.list_by_learner(req.learner_id)
        for session in existing_sessions:
            if session.lecture_id == req.lecture_id:
                return err(
                    ConflictError.duplicate_learning_session(
                        "LearningSession already exists for (learner_id, lecture_id)"
                    )
                )

        new_id = self._id_generator.next_id()
        session = LearningSession.start(
            id=new_id,
            learner_id=req.learner_id,
            lecture_id=req.lecture_id,
            started_at=req.started_at,
            existing_sessions=existing_sessions,
        )
        self._repository.save(session)
        return ok(
            StartOrGetLearningSessionResponse(
                session_id=session.id,
                session=session,
                outcome=StartOrGetOutcome.CREATED,
            )
        )
