# 仕様: docs/spec/application-usecase.md#RecordViewingEvent
"""RecordViewingEventUseCase の受入基準テスト。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from application.common.errors import ErrorCode, ValidationError
from application.common.result import Err, Ok
from application.common.start_or_get_outcome import StartOrGetOutcome
from application.learning.dto.record_viewing_event import RecordViewingEventRequest
from application.learning.use_cases.record_viewing_event import RecordViewingEventUseCase
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from domain.learning.viewing_event import ViewingAction
from domain.shared.ids import LectureId, LearnerId, LearningSessionId, ViewingEventId
from tests.test_application.fakes.learning.fake_id_generators import (
    FakeLearningSessionIdGenerator,
    FakeViewingEventIdGenerator,
)
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _request(
    *,
    learner_id: str = "learner-1",
    lecture_id: str = "lecture-1",
    occurred_at: datetime = FIXED_NOW,
    video_position: int = 120,
    action: ViewingAction = ViewingAction.PLAY,
    position_delta: int = 0,
) -> RecordViewingEventRequest:
    return RecordViewingEventRequest(
        learner_id=LearnerId(learner_id),
        lecture_id=LectureId(lecture_id),
        occurred_at=occurred_at,
        video_position=video_position,
        action=action,
        position_delta=position_delta,
    )


def _use_case(
    repository: InMemoryLearningSessionRepository | None = None,
) -> RecordViewingEventUseCase:
    repo = repository or InMemoryLearningSessionRepository()
    return RecordViewingEventUseCase(
        start_or_get=StartOrGetLearningSessionUseCase(
            repository=repo,
            id_generator=FakeLearningSessionIdGenerator(),
        ),
        viewing_event_id_generator=FakeViewingEventIdGenerator(),
        repository=repo,
    )


class TestRecordViewingEventAcceptance:
    """受入基準を executable spec として検証する。"""

    def test_first_event_creates_session_via_start_or_get(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert result.value.event_id == ViewingEventId("ve-1")
        assert result.value.session_id == LearningSessionId("ls-1")
        assert repository.save_count == 2
        sessions = repository.all_sessions()
        assert len(sessions) == 1
        session = sessions[0]
        assert session.learner_id == LearnerId("learner-1")
        assert session.lecture_id == LectureId("lecture-1")
        assert len(session.viewing_events) == 1
        event = session.viewing_events[0]
        assert event.id == ViewingEventId("ve-1")
        assert event.action == ViewingAction.PLAY
        assert event.video_position == 120
        assert event.position_delta == 0
        assert event.occurred_at == FIXED_NOW

    def test_second_event_appends_to_same_session(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)
        second_at = FIXED_NOW + timedelta(seconds=30)

        first = use_case.execute(_request())
        save_count_after_first = repository.save_count
        second = use_case.execute(
            _request(
                occurred_at=second_at,
                video_position=150,
                action=ViewingAction.PAUSE,
            )
        )

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert second.value.session_id == first.value.session_id
        assert second.value.event_id == ViewingEventId("ve-2")
        assert repository.save_count == save_count_after_first + 1
        session = repository.all_sessions()[0]
        assert len(session.viewing_events) == 2
        assert session.viewing_events[1].action == ViewingAction.PAUSE
        assert session.viewing_events[1].occurred_at == second_at

    def test_backward_skip_with_negative_delta_is_accepted(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)

        result = use_case.execute(
            _request(
                action=ViewingAction.BACKWARD_SKIP,
                position_delta=-10,
                video_position=100,
            )
        )

        assert isinstance(result, Ok)
        session = repository.all_sessions()[0]
        event = session.viewing_events[0]
        assert event.action == ViewingAction.BACKWARD_SKIP
        assert event.position_delta == -10


class TestRecordViewingEventValidation:
    """Request 検証と視聴不変条件を検証する。"""

    def test_empty_learner_id_returns_validation_error(self) -> None:
        request = RecordViewingEventRequest(
            learner_id=str.__new__(LearnerId, ""),
            lecture_id=LectureId("lecture-1"),
            occurred_at=FIXED_NOW,
            video_position=0,
            action=ViewingAction.PLAY,
            position_delta=0,
        )
        use_case = _use_case()

        result = use_case.execute(request)

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code == ErrorCode.VALIDATION_ERROR

    def test_play_with_nonzero_delta_returns_invalid_viewing_event(self) -> None:
        use_case = _use_case()

        result = use_case.execute(
            _request(action=ViewingAction.PLAY, position_delta=5)
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code == ErrorCode.INVALID_VIEWING_EVENT

    def test_negative_video_position_returns_invalid_viewing_event(self) -> None:
        use_case = _use_case()

        result = use_case.execute(_request(video_position=-1))

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code == ErrorCode.INVALID_VIEWING_EVENT

    def test_invalid_viewing_event_does_not_call_save(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)

        result = use_case.execute(
            _request(action=ViewingAction.PLAY, position_delta=1)
        )

        assert isinstance(result, Err)
        assert repository.save_count == 0
