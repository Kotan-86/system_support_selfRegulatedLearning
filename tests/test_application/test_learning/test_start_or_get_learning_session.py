# 仕様: docs/spec/application-usecase.md#StartOrGetLearningSession
"""StartOrGetLearningSessionUseCase の受入基準テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.common.errors import ConflictError, ErrorCode, ValidationError
from application.common.result import Err, Ok
from application.common.start_or_get_outcome import StartOrGetOutcome
from application.learning.dto.start_or_get_learning_session import (
    StartOrGetLearningSessionRequest,
)
from application.learning.ports.learning_session_repository import (
    LearningSessionRepository,
)
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from domain.learning.learning_session import LearningSession
from domain.shared.ids import LectureId, LearnerId, LearningSessionId
from tests.test_application.fakes.learning.fake_id_generators import (
    FakeLearningSessionIdGenerator,
)
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _request(
    *,
    learner_id: str = "learner-1",
    lecture_id: str = "lecture-1",
    started_at: datetime = FIXED_NOW,
) -> StartOrGetLearningSessionRequest:
    return StartOrGetLearningSessionRequest(
        learner_id=LearnerId(learner_id),
        lecture_id=LectureId(lecture_id),
        started_at=started_at,
    )


def _use_case(
    repository: InMemoryLearningSessionRepository | None = None,
    id_generator: FakeLearningSessionIdGenerator | None = None,
) -> StartOrGetLearningSessionUseCase:
    return StartOrGetLearningSessionUseCase(
        repository=repository or InMemoryLearningSessionRepository(),
        id_generator=id_generator or FakeLearningSessionIdGenerator(),
    )


class _InconsistentRepository(LearningSessionRepository):
    """find が None を返すが list には重複 Session がある不整合 Repository（競合防御のテスト用）。"""

    def __init__(self, session: LearningSession) -> None:
        self._session = session
        self.save_count = 0

    def find_by_learner_and_lecture(
        self, learner_id: LearnerId, lecture_id: LectureId
    ) -> LearningSession | None:
        return None

    def list_by_learner(self, learner_id: LearnerId) -> tuple[LearningSession, ...]:
        return (self._session,)

    def save(self, session: LearningSession) -> LearningSession:
        self.save_count += 1
        return session


class TestStartOrGetLearningSessionAcceptance:
    """受入基準を executable spec として検証する。"""

    def test_creates_session_and_saves_once_when_not_exists(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert result.value.outcome is StartOrGetOutcome.CREATED
        assert result.value.session_id == LearningSessionId("ls-1")
        assert result.value.session.learner_id == LearnerId("learner-1")
        assert result.value.session.lecture_id == LectureId("lecture-1")
        assert result.value.session.started_at == FIXED_NOW
        assert repository.save_count == 1
        assert len(repository.all_sessions()) == 1

    def test_returns_existing_session_without_save(self) -> None:
        existing = LearningSession(
            id=LearningSessionId("existing-session"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            started_at=FIXED_NOW,
        )
        repository = InMemoryLearningSessionRepository(sessions=(existing,))
        use_case = _use_case(repository=repository)

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert result.value.outcome is StartOrGetOutcome.RETRIEVED
        assert result.value.session_id == LearningSessionId("existing-session")
        assert result.value.session is existing
        assert repository.save_count == 0

    def test_second_call_for_same_pair_is_get_with_single_session(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)

        first = use_case.execute(_request())
        second = use_case.execute(_request())

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert first.value.outcome is StartOrGetOutcome.CREATED
        assert second.value.outcome is StartOrGetOutcome.RETRIEVED
        assert second.value.session_id == first.value.session_id
        assert second.value.session is first.value.session
        assert repository.save_count == 1
        assert len(repository.all_sessions()) == 1

    def test_same_learner_can_have_multiple_sessions_for_different_lectures(
        self,
    ) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)

        first = use_case.execute(_request(lecture_id="lecture-a"))
        second = use_case.execute(_request(lecture_id="lecture-b"))

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert first.value.outcome is StartOrGetOutcome.CREATED
        assert second.value.outcome is StartOrGetOutcome.CREATED
        assert first.value.session_id != second.value.session_id
        assert repository.save_count == 2
        assert len(repository.all_sessions()) == 2


class TestStartOrGetLearningSessionValidation:
    """Request 検証と競合防御を検証する。"""

    def test_empty_learner_id_returns_validation_error(self) -> None:
        request = StartOrGetLearningSessionRequest(
            learner_id=str.__new__(LearnerId, ""),
            lecture_id=LectureId("lecture-1"),
            started_at=FIXED_NOW,
        )
        use_case = _use_case()

        result = use_case.execute(request)

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code == ErrorCode.VALIDATION_ERROR

    def test_empty_lecture_id_returns_validation_error(self) -> None:
        request = StartOrGetLearningSessionRequest(
            learner_id=LearnerId("learner-1"),
            lecture_id=str.__new__(LectureId, ""),
            started_at=FIXED_NOW,
        )
        use_case = _use_case()

        result = use_case.execute(request)

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code == ErrorCode.VALIDATION_ERROR

    def test_duplicate_detected_via_list_returns_conflict_error(self) -> None:
        existing = LearningSession(
            id=LearningSessionId("existing-session"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            started_at=FIXED_NOW,
        )
        repository = _InconsistentRepository(existing)
        use_case = _use_case(repository=repository)  # type: ignore[arg-type]

        result = use_case.execute(_request())

        assert isinstance(result, Err)
        assert isinstance(result.error, ConflictError)
        assert result.error.code == ErrorCode.DUPLICATE_LEARNING_SESSION
        assert repository.save_count == 0
