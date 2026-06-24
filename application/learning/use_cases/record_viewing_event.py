# 仕様: docs/spec/application-usecase.md#RecordViewingEvent
# 仕様: docs/spec/application-error-handling.md#RecordViewingEvent
"""RecordViewingEvent ユースケース。"""
from __future__ import annotations

from application.common.errors import AppError, ErrorCode, ValidationError
from application.common.result import Result, err, ok
from application.learning.dto.record_viewing_event import (
    RecordViewingEventRequest,
    RecordViewingEventResponse,
)
from application.learning.dto.start_or_get_learning_session import (
    StartOrGetLearningSessionRequest,
)
from application.learning.ports.id_generators import ViewingEventIdGenerator
from application.learning.ports.learning_session_repository import (
    LearningSessionRepository,
)
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from domain.learning.viewing_event import ViewingAction


def _validate_viewing_invariants(
    video_position: int,
    action: ViewingAction,
    position_delta: int,
) -> Result[None, ValidationError]:
    if video_position < 0:
        return err(
            ValidationError(
                "video_position must be >= 0",
                ErrorCode.INVALID_VIEWING_EVENT,
            )
        )

    if action in (ViewingAction.PLAY, ViewingAction.PAUSE):
        if position_delta != 0:
            return err(
                ValidationError(
                    f"position_delta must be 0 for {action.value}, got {position_delta}",
                    ErrorCode.INVALID_VIEWING_EVENT,
                )
            )
        return ok(None)

    if action in (ViewingAction.FORWARD_SKIP, ViewingAction.FORWARD_SEEK):
        if position_delta < 0:
            return err(
                ValidationError(
                    f"position_delta must be >= 0 for {action.value}, got {position_delta}",
                    ErrorCode.INVALID_VIEWING_EVENT,
                )
            )
        return ok(None)

    if action in (ViewingAction.BACKWARD_SKIP, ViewingAction.BACKWARD_SEEK):
        if position_delta > 0:
            return err(
                ValidationError(
                    f"position_delta must be <= 0 for {action.value}, got {position_delta}",
                    ErrorCode.INVALID_VIEWING_EVENT,
                )
            )
        return ok(None)

    return ok(None)


class RecordViewingEventUseCase:
    """動画操作 1 回を LearningSession 集約に追記する。"""

    def __init__(
        self,
        start_or_get: StartOrGetLearningSessionUseCase,
        viewing_event_id_generator: ViewingEventIdGenerator,
        repository: LearningSessionRepository,
    ) -> None:
        self._start_or_get = start_or_get
        self._viewing_event_id_generator = viewing_event_id_generator
        self._repository = repository

    def execute(
        self, request: RecordViewingEventRequest
    ) -> Result[RecordViewingEventResponse, AppError]:
        validated = request.validate()
        if validated.is_err:
            return validated  # type: ignore[return-value]

        req = validated.value
        viewing_valid = _validate_viewing_invariants(
            req.video_position, req.action, req.position_delta
        )
        if viewing_valid.is_err:
            return viewing_valid  # type: ignore[return-value]

        session_result = self._start_or_get.execute(
            StartOrGetLearningSessionRequest(
                learner_id=req.learner_id,
                lecture_id=req.lecture_id,
                started_at=req.occurred_at,
            )
        )
        if session_result.is_err:
            return session_result  # type: ignore[return-value]

        session = session_result.value.session
        event_id = self._viewing_event_id_generator.next_id()
        updated = session.record_viewing_event(
            event_id=event_id,
            occurred_at=req.occurred_at,
            video_position=req.video_position,
            action=req.action,
            position_delta=req.position_delta,
        )
        self._repository.save(updated)
        return ok(
            RecordViewingEventResponse(
                event_id=event_id,
                session_id=updated.id,
            )
        )
