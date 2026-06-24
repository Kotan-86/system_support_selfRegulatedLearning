# 仕様: docs/spec/application-usecase.md#StartOrGetTutorSession
# 仕様: docs/spec/application-error-handling.md#StartOrGetTutorSession
"""StartOrGetTutorSession ユースケース。"""
from __future__ import annotations

from application.common.errors import AppError, ConflictError
from application.common.result import Result, err, ok
from application.common.start_or_get_outcome import StartOrGetOutcome
from application.tutoring.dto.start_or_get_tutor_session import (
    StartOrGetTutorSessionRequest,
    StartOrGetTutorSessionResponse,
)
from application.tutoring.ports.id_generators import TutorSessionIdGenerator
from application.tutoring.ports.tutor_session_repository import TutorSessionRepository
from domain.tutoring.services.near_term_experiment_policy import (
    NearTermExperimentPolicy,
    TutorSessionStartRequest,
)
from domain.tutoring.tutor_session import TutorSession


class StartOrGetTutorSessionUseCase:
    """1 LearningSession に TutorSession を 1 本確保する。"""

    def __init__(
        self,
        repository: TutorSessionRepository,
        id_generator: TutorSessionIdGenerator,
    ) -> None:
        self._repository = repository
        self._id_generator = id_generator

    def execute(
        self, request: StartOrGetTutorSessionRequest
    ) -> Result[StartOrGetTutorSessionResponse, AppError]:
        validated = request.validate()
        if validated.is_err:
            return validated  # type: ignore[return-value]

        req = validated.value
        existing = self._repository.find_by_learning_session_id(req.learning_session_id)
        if existing is not None:
            return ok(
                StartOrGetTutorSessionResponse(
                    tutor_session_id=existing.id,
                    session=existing,
                    outcome=StartOrGetOutcome.RETRIEVED,
                )
            )

        all_sessions = self._repository.list_all()
        new_id = self._id_generator.next_id()
        policy_request = TutorSessionStartRequest(
            id=new_id,
            learning_session_id=req.learning_session_id,
        )
        if not NearTermExperimentPolicy.can_start_tutor_session(
            existing_sessions=all_sessions,
            request=policy_request,
        ):
            return err(
                ConflictError.tutor_session_policy_violation(
                    "Near-term experiment allows only one TutorSession per LearningSession"
                )
            )

        for session in all_sessions:
            if session.learning_session_id == req.learning_session_id:
                return err(
                    ConflictError.tutor_session_policy_violation(
                        "TutorSession already exists for learning_session_id"
                    )
                )

        session = TutorSession.start(
            id=new_id,
            learning_session_id=req.learning_session_id,
            started_at=req.started_at,
        )
        self._repository.save(session)
        return ok(
            StartOrGetTutorSessionResponse(
                tutor_session_id=session.id,
                session=session,
                outcome=StartOrGetOutcome.CREATED,
            )
        )
