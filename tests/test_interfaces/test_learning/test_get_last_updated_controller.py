# 仕様: docs/spec/interfaces-layer.md#既存-API-対応表
"""GetLastUpdatedController の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.common.errors import ErrorCode
from application.learning.dto.record_quiz_attempt import RecordQuizAttemptRequest
from application.learning.dto.record_viewing_event import RecordViewingEventRequest
from application.learning.use_cases.get_learning_snapshot import GetLearningSnapshotUseCase
from domain.learning.quiz_attempt import QuizAnswer
from domain.learning.viewing_event import ViewingAction
from domain.shared.ids import LectureId, LearnerId
from interfaces.learning.controllers.get_last_updated_controller import (
    GetLastUpdatedController,
)
from interfaces.learning.presenters.last_updated_presenter import LastUpdatedPresenter
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.learning.view_models.last_updated import LastUpdatedViewModel
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)
from tests.test_application.test_learning.test_get_learning_snapshot import (
    _get_snapshot_use_case,
    _record_quiz_use_case,
    _record_viewing_use_case,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
QUIZ_AT = datetime(2026, 6, 21, 13, 0, 0, tzinfo=timezone.utc)


def _controller(use_case: GetLearningSnapshotUseCase) -> GetLastUpdatedController:
    return GetLastUpdatedController(
        use_case=use_case,
        presenter=LastUpdatedPresenter(),
    )


class TestGetLastUpdatedController:
    """Controller の ingress と UC 連携を検証する。"""

    def test_empty_participant_id_returns_validation_error_view_model(self) -> None:
        controller = _controller(_get_snapshot_use_case())

        result = controller.execute("")

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.VALIDATION_ERROR.value
        assert result.status_kind.value == "validation"

    def test_no_session_returns_null_last_updated(self) -> None:
        controller = _controller(_get_snapshot_use_case())

        result = controller.execute("learner-1", lecture_id="lecture-1")

        assert isinstance(result, LastUpdatedViewModel)
        assert result.last_updated is None

    def test_after_viewing_event_returns_max_occurred_at(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _get_snapshot_use_case(repository=repository)
        controller = _controller(use_case)
        record_viewing = _record_viewing_use_case(repository)
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                occurred_at=FIXED_NOW,
                video_position=0,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )

        result = controller.execute("learner-1", lecture_id="lecture-1")

        assert isinstance(result, LastUpdatedViewModel)
        assert result.last_updated == FIXED_NOW

    def test_after_quiz_attempt_returns_max_attempted_at(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _get_snapshot_use_case(repository=repository)
        controller = _controller(use_case)
        record_viewing = _record_viewing_use_case(repository)
        record_quiz = _record_quiz_use_case(repository)
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                occurred_at=FIXED_NOW,
                video_position=0,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )
        record_quiz.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                attempted_at=QUIZ_AT,
                score_numerator=1,
                score_denominator=1,
                answers=(QuizAnswer(question_index=1, selected_answer="A", is_correct=True),),
            )
        )

        result = controller.execute("learner-1", lecture_id="lecture-1")

        assert isinstance(result, LastUpdatedViewModel)
        assert result.last_updated == QUIZ_AT
