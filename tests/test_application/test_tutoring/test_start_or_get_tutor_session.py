# 仕様: docs/spec/application-usecase.md#StartOrGetTutorSession
"""StartOrGetTutorSessionUseCase の受入基準テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.common.errors import ConflictError, ErrorCode, ValidationError
from application.common.result import Err, Ok
from application.common.start_or_get_outcome import StartOrGetOutcome
from application.tutoring.dto.start_or_get_tutor_session import (
    StartOrGetTutorSessionRequest,
)
from application.tutoring.ports.tutor_session_repository import TutorSessionRepository
from application.tutoring.use_cases.start_or_get_tutor_session import (
    StartOrGetTutorSessionUseCase,
)
from domain.shared.ids import LearningSessionId, TutorSessionId
from domain.tutoring.tutor_session import TutorSession
from tests.test_application.fakes.tutoring.fake_id_generators import (
    FakeTutorSessionIdGenerator,
)
from tests.test_application.fakes.tutoring.in_memory_tutor_session_repository import (
    InMemoryTutorSessionRepository,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _request(
    *,
    learning_session_id: str = "ls-1",
    started_at: datetime = FIXED_NOW,
) -> StartOrGetTutorSessionRequest:
    return StartOrGetTutorSessionRequest(
        learning_session_id=LearningSessionId(learning_session_id),
        started_at=started_at,
    )


def _use_case(
    repository: InMemoryTutorSessionRepository | None = None,
    id_generator: FakeTutorSessionIdGenerator | None = None,
) -> StartOrGetTutorSessionUseCase:
    return StartOrGetTutorSessionUseCase(
        repository=repository or InMemoryTutorSessionRepository(),
        id_generator=id_generator or FakeTutorSessionIdGenerator(),
    )


def _existing_tutor_session(
    *,
    tutor_session_id: str = "existing-tutor",
    learning_session_id: str = "ls-1",
    started_at: datetime = FIXED_NOW,
) -> TutorSession:
    return TutorSession.start(
        id=TutorSessionId(tutor_session_id),
        learning_session_id=LearningSessionId(learning_session_id),
        started_at=started_at,
    )


class _InconsistentRepository(TutorSessionRepository):
    """find が None を返すが list には同一 learning_session_id の Session がある不整合 Repository（Policy / 競合防御のテスト用）。"""

    def __init__(self, session: TutorSession) -> None:
        self._session = session
        self.save_count = 0

    def find_by_id(self, tutor_session_id: TutorSessionId) -> TutorSession | None:
        return None

    def find_by_learning_session_id(
        self, learning_session_id: LearningSessionId
    ) -> TutorSession | None:
        return None

    def list_all(self) -> tuple[TutorSession, ...]:
        return (self._session,)

    def save(self, session: TutorSession) -> None:
        self.save_count += 1


class TestStartOrGetTutorSessionAcceptance:
    """受入基準を executable spec として検証する。"""

    def test_creates_session_and_saves_once_when_not_exists(self) -> None:
        repository = InMemoryTutorSessionRepository()
        use_case = _use_case(repository=repository)

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert result.value.outcome is StartOrGetOutcome.CREATED
        assert result.value.tutor_session_id == TutorSessionId("ts-1")
        assert result.value.session.learning_session_id == LearningSessionId("ls-1")
        assert result.value.session.started_at == FIXED_NOW
        assert repository.save_count == 1
        assert len(repository.all_sessions()) == 1

    def test_returns_existing_session_without_save(self) -> None:
        existing = _existing_tutor_session()
        repository = InMemoryTutorSessionRepository(sessions=(existing,))
        use_case = _use_case(repository=repository)

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert result.value.outcome is StartOrGetOutcome.RETRIEVED
        assert result.value.tutor_session_id == TutorSessionId("existing-tutor")
        assert result.value.session is existing
        assert repository.save_count == 0

    def test_second_call_for_same_learning_session_is_get_with_single_session(
        self,
    ) -> None:
        repository = InMemoryTutorSessionRepository()
        use_case = _use_case(repository=repository)

        first = use_case.execute(_request())
        second = use_case.execute(_request())

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert first.value.outcome is StartOrGetOutcome.CREATED
        assert second.value.outcome is StartOrGetOutcome.RETRIEVED
        assert second.value.tutor_session_id == first.value.tutor_session_id
        assert second.value.session is first.value.session
        assert repository.save_count == 1
        assert len(repository.all_sessions()) == 1

    def test_different_learning_sessions_can_have_multiple_tutor_sessions(
        self,
    ) -> None:
        repository = InMemoryTutorSessionRepository()
        use_case = _use_case(repository=repository)

        first = use_case.execute(_request(learning_session_id="ls-a"))
        second = use_case.execute(_request(learning_session_id="ls-b"))

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert first.value.outcome is StartOrGetOutcome.CREATED
        assert second.value.outcome is StartOrGetOutcome.CREATED
        assert first.value.tutor_session_id != second.value.tutor_session_id
        assert repository.save_count == 2
        assert len(repository.all_sessions()) == 2


class TestStartOrGetTutorSessionPolicy:
    """NearTermExperimentPolicy 連携と競合防御を検証する。"""

    def test_policy_violation_when_list_has_same_learning_session_but_find_misses(
        self,
    ) -> None:
        existing = _existing_tutor_session()
        repository = _InconsistentRepository(existing)
        use_case = _use_case(repository=repository)  # type: ignore[arg-type]

        result = use_case.execute(_request())

        assert isinstance(result, Err)
        assert isinstance(result.error, ConflictError)
        assert result.error.code == ErrorCode.TUTOR_SESSION_POLICY_VIOLATION
        assert repository.save_count == 0


class TestStartOrGetTutorSessionValidation:
    """Request 検証を検証する。"""

    def test_empty_learning_session_id_returns_validation_error(self) -> None:
        request = StartOrGetTutorSessionRequest(
            learning_session_id=str.__new__(LearningSessionId, ""),
            started_at=FIXED_NOW,
        )
        use_case = _use_case()

        result = use_case.execute(request)

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code == ErrorCode.VALIDATION_ERROR
