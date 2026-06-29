# 仕様: docs/spec/application-usecase.md#StartOrGetLearningSession
# 仕様: docs/spec/framework-drivers-persistence.md#repository-操作what
"""SqliteLearningSessionRepository と StartOrGetLearningSessionUseCase の統合テスト。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from application.common.errors import ValidationError
from application.common.result import Err, Ok
from application.common.start_or_get_outcome import StartOrGetOutcome
from application.learning.dto.start_or_get_learning_session import (
    StartOrGetLearningSessionRequest,
)
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from domain.learning.learning_session import LearningSession
from domain.shared.ids import LectureId, LearnerId, LearningSessionId
from framework_drivers.db.learning.sqlite_learning_session_mapper import format_datetime
from framework_drivers.db.learning.sqlite_learning_session_repository import (
    SqliteLearningSessionRepository,
)
from domain.learning.viewing_event import ViewingAction
from tests.test_application.fakes.learning.fake_id_generators import (
    FakeLearningSessionIdGenerator,
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
    repository: SqliteLearningSessionRepository,
    id_generator: FakeLearningSessionIdGenerator | None = None,
) -> StartOrGetLearningSessionUseCase:
    return StartOrGetLearningSessionUseCase(
        repository=repository,
        id_generator=id_generator or FakeLearningSessionIdGenerator(),
    )


def _count_sessions(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS cnt FROM learning_sessions").fetchone()
    assert row is not None
    return int(row["cnt"])


class TestSqliteLearningSessionRepositoryRead:
    """Repository read 経路の基本動作。"""

    def test_find_returns_none_when_empty(
        self, sqlite_learning_session_repository: SqliteLearningSessionRepository
    ) -> None:
        result = sqlite_learning_session_repository.find_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId("lecture-1")
        )

        assert result is None

    def test_save_and_find_round_trip(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        session = LearningSession(
            id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            started_at=FIXED_NOW,
        )

        sqlite_learning_session_repository.save(session)
        loaded = sqlite_learning_session_repository.find_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId("lecture-1")
        )

        assert loaded is not None
        assert loaded.id == session.id
        assert loaded.learner_id == session.learner_id
        assert loaded.lecture_id == session.lecture_id
        assert loaded.started_at == session.started_at
        assert loaded.viewing_events == ()
        assert loaded.quiz_attempts == ()
        assert _count_sessions(learning_db_conn) == 1

    def test_list_by_learner_returns_all_sessions(
        self, sqlite_learning_session_repository: SqliteLearningSessionRepository
    ) -> None:
        first = LearningSession(
            id=LearningSessionId("session-a"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-a"),
            started_at=FIXED_NOW,
        )
        second = LearningSession(
            id=LearningSessionId("session-b"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-b"),
            started_at=FIXED_NOW,
        )
        other_learner = LearningSession(
            id=LearningSessionId("session-c"),
            learner_id=LearnerId("learner-2"),
            lecture_id=LectureId("lecture-a"),
            started_at=FIXED_NOW,
        )

        sqlite_learning_session_repository.save(first)
        sqlite_learning_session_repository.save(second)
        sqlite_learning_session_repository.save(other_learner)

        sessions = sqlite_learning_session_repository.list_by_learner(
            LearnerId("learner-1")
        )

        assert {session.id for session in sessions} == {
            LearningSessionId("session-a"),
            LearningSessionId("session-b"),
        }


class TestStartOrGetLearningSessionWithSqliteRepository:
    """StartOrGetLearningSessionUseCase + SQLite Repository の受入基準。"""

    def test_creates_session_and_persists_once_when_not_exists(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        use_case = _use_case(sqlite_learning_session_repository)

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert result.value.outcome is StartOrGetOutcome.CREATED
        assert result.value.session_id == LearningSessionId("ls-1")
        assert result.value.session.learner_id == LearnerId("learner-1")
        assert result.value.session.lecture_id == LectureId("lecture-1")
        assert result.value.session.started_at == FIXED_NOW
        assert _count_sessions(learning_db_conn) == 1

    def test_returns_existing_session_without_second_insert(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        existing = LearningSession(
            id=LearningSessionId("existing-session"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            started_at=FIXED_NOW,
        )
        sqlite_learning_session_repository.save(existing)
        use_case = _use_case(sqlite_learning_session_repository)

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert result.value.outcome is StartOrGetOutcome.RETRIEVED
        assert result.value.session_id == LearningSessionId("existing-session")
        assert result.value.session.started_at == FIXED_NOW
        assert _count_sessions(learning_db_conn) == 1

    def test_second_call_for_same_pair_is_get_with_single_row(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        use_case = _use_case(sqlite_learning_session_repository)

        first = use_case.execute(_request())
        second = use_case.execute(_request())

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert first.value.outcome is StartOrGetOutcome.CREATED
        assert second.value.outcome is StartOrGetOutcome.RETRIEVED
        assert second.value.session_id == first.value.session_id
        assert _count_sessions(learning_db_conn) == 1

    def test_same_learner_can_have_multiple_sessions_for_different_lectures(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        use_case = _use_case(sqlite_learning_session_repository)

        first = use_case.execute(_request(lecture_id="lecture-a"))
        second = use_case.execute(_request(lecture_id="lecture-b"))

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert first.value.outcome is StartOrGetOutcome.CREATED
        assert second.value.outcome is StartOrGetOutcome.CREATED
        assert first.value.session_id != second.value.session_id
        assert _count_sessions(learning_db_conn) == 2

    def test_empty_learner_id_returns_validation_error(
        self, sqlite_learning_session_repository: SqliteLearningSessionRepository
    ) -> None:
        request = StartOrGetLearningSessionRequest(
            learner_id=str.__new__(LearnerId, ""),
            lecture_id=LectureId("lecture-1"),
            started_at=FIXED_NOW,
        )
        use_case = _use_case(sqlite_learning_session_repository)

        result = use_case.execute(request)

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)

    def test_loads_viewing_logs_inserted_directly(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        """Read 経路で viewing_logs 行が ViewingEvent に復元される。"""
        session = LearningSession(
            id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            started_at=FIXED_NOW,
        )
        sqlite_learning_session_repository.save(session)
        learning_db_conn.execute(
            """
            INSERT INTO viewing_logs
                (learning_session_id, time_stamp, "current_time", action, duration)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "session-1",
                format_datetime(FIXED_NOW),
                100,
                ViewingAction.PLAY.value,
                0.0,
            ),
        )
        learning_db_conn.commit()

        loaded = sqlite_learning_session_repository.find_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId("lecture-1")
        )

        assert loaded is not None
        assert len(loaded.viewing_events) == 1
        assert loaded.viewing_events[0].action is ViewingAction.PLAY
        assert loaded.viewing_events[0].video_position == 100
