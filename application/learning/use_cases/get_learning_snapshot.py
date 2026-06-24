# 仕様: docs/spec/application-usecase.md#GetLearningSnapshot
# 仕様: docs/spec/application-error-handling.md#GetLearningSnapshot
"""GetLearningSnapshot ユースケース。"""
from __future__ import annotations

from datetime import datetime

from application.common.errors import AppError, LectureNotFoundError
from application.common.result import Result, err, ok
from application.learning.dto.get_learning_snapshot import (
    GetLearningSnapshotRequest,
    GetLearningSnapshotResponse,
)
from application.learning.ports.learning_session_repository import (
    LearningSessionRepository,
)
from application.learning.ports.lecture_catalog import LectureCatalog
from domain.learning.learning_session import LearningSession
from domain.learning.learning_snapshot import LearningSnapshot
from domain.learning.services.learning_snapshot_builder import LearningSnapshotBuilder
from domain.shared.ids import LectureId, LearnerId, LearningSessionId

_UNCREATED_SESSION_ID = LearningSessionId("uncreated")


def _empty_snapshot(*, learner_id: LearnerId, lecture_id: LectureId) -> LearningSnapshot:
    return LearningSnapshot(
        session_id=_UNCREATED_SESSION_ID,
        learner_id=learner_id,
        lecture_id=lecture_id,
        viewing_events=(),
        latest_quiz_attempt=None,
        quiz_answers=(),
    )


def _max_event_time(session: LearningSession) -> datetime | None:
    times: list[datetime] = []
    for event in session.viewing_events:
        times.append(event.occurred_at)
    for attempt in session.quiz_attempts:
        times.append(attempt.attempted_at)
    if not times:
        return None
    return max(times)


class GetLearningSnapshotUseCase:
    """LAD と AI 共通の学習コンテキスト Read UC。"""

    def __init__(
        self,
        repository: LearningSessionRepository,
        lecture_catalog: LectureCatalog,
    ) -> None:
        self._repository = repository
        self._lecture_catalog = lecture_catalog

    def execute(
        self, request: GetLearningSnapshotRequest
    ) -> Result[GetLearningSnapshotResponse, AppError]:
        validated = request.validate()
        if validated.is_err:
            return validated  # type: ignore[return-value]

        req = validated.value
        lecture = self._lecture_catalog.find_by_id(req.lecture_id)
        if lecture is None:
            return err(
                LectureNotFoundError(f"lecture not found: {req.lecture_id!s}")
            )

        session = self._repository.find_by_learner_and_lecture(
            req.learner_id, req.lecture_id
        )
        if session is None:
            return ok(
                GetLearningSnapshotResponse(
                    snapshot=_empty_snapshot(
                        learner_id=req.learner_id,
                        lecture_id=req.lecture_id,
                    ),
                    content_updated_at=None,
                )
            )

        snapshot = LearningSnapshotBuilder.build(session=session, lecture=lecture)
        return ok(
            GetLearningSnapshotResponse(
                snapshot=snapshot,
                content_updated_at=_max_event_time(session),
            )
        )
