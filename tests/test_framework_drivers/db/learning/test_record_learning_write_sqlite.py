# 仕様: docs/spec/application-usecase.md#RecordViewingEvent
# 仕様: docs/spec/application-usecase.md#RecordQuizAttempt
# 仕様: docs/spec/framework-drivers-persistence.md#write-経路との対応
"""RecordViewingEvent / RecordQuizAttempt と SqliteLearningSessionRepository の統合テスト。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from application.common.result import Ok
from application.learning.dto.record_quiz_attempt import RecordQuizAttemptRequest
from application.learning.dto.record_viewing_event import RecordViewingEventRequest
from application.learning.use_cases.record_quiz_attempt import RecordQuizAttemptUseCase
from application.learning.use_cases.record_viewing_event import RecordViewingEventUseCase
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from domain.learning.quiz_attempt import QuizAnswer
from domain.learning.viewing_event import ViewingAction
from domain.shared.ids import LectureId, LearnerId, QuizAttemptId, ViewingEventId
from framework_drivers.db.learning.id_generators import UuidLearningSessionIdGenerator
from framework_drivers.db.learning.sqlite_learning_session_repository import (
    SqliteLearningSessionRepository,
)
from framework_drivers.db.learning.static_lecture_catalog import StaticLectureCatalog
from interfaces.common.default_lecture import DEFAULT_LECTURE_ID_VALUE

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _count_rows(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
    assert row is not None
    return int(row["cnt"])


def _viewing_use_case(
    repository: SqliteLearningSessionRepository,
) -> RecordViewingEventUseCase:
    return RecordViewingEventUseCase(
        start_or_get=StartOrGetLearningSessionUseCase(
            repository=repository,
            id_generator=UuidLearningSessionIdGenerator(),
        ),
        repository=repository,
    )


def _quiz_use_case(
    repository: SqliteLearningSessionRepository,
) -> RecordQuizAttemptUseCase:
    return RecordQuizAttemptUseCase(
        start_or_get=StartOrGetLearningSessionUseCase(
            repository=repository,
            id_generator=UuidLearningSessionIdGenerator(),
        ),
        lecture_catalog=StaticLectureCatalog(),
        repository=repository,
    )


def _five_answers(*, wrong_at: int | None = None) -> tuple[QuizAnswer, ...]:
    return tuple(
        QuizAnswer(
            question_index=index,
            selected_answer="A" if index != wrong_at else "B",
            is_correct=index != wrong_at,
        )
        for index in range(1, 6)
    )


class TestRecordViewingEventWithSqliteRepository:
    """RecordViewingEventUseCase + SQLite Repository の受入基準。"""

    def test_first_event_persists_session_and_viewing_log(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        use_case = _viewing_use_case(sqlite_learning_session_repository)

        result = use_case.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                occurred_at=FIXED_NOW,
                video_position=120,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )

        assert isinstance(result, Ok)
        assert result.value.event_id == ViewingEventId("1")
        assert _count_rows(learning_db_conn, "learning_sessions") == 1
        assert _count_rows(learning_db_conn, "viewing_logs") == 1

        loaded = sqlite_learning_session_repository.find_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId(DEFAULT_LECTURE_ID_VALUE)
        )
        assert loaded is not None
        assert loaded.id == result.value.session_id
        assert len(loaded.viewing_events) == 1
        assert loaded.viewing_events[0].id == ViewingEventId("1")
        assert loaded.viewing_events[0].action is ViewingAction.PLAY
        assert loaded.viewing_events[0].video_position == 120

    def test_second_event_appends_to_same_session(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        use_case = _viewing_use_case(sqlite_learning_session_repository)
        second_at = FIXED_NOW + timedelta(seconds=30)

        first = use_case.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                occurred_at=FIXED_NOW,
                video_position=120,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )
        second = use_case.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                occurred_at=second_at,
                video_position=150,
                action=ViewingAction.PAUSE,
                position_delta=0,
            )
        )

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert second.value.session_id == first.value.session_id
        assert second.value.event_id == ViewingEventId("2")
        assert _count_rows(learning_db_conn, "learning_sessions") == 1
        assert _count_rows(learning_db_conn, "viewing_logs") == 2

        loaded = sqlite_learning_session_repository.find_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId(DEFAULT_LECTURE_ID_VALUE)
        )
        assert loaded is not None
        assert len(loaded.viewing_events) == 2
        assert loaded.viewing_events[1].action is ViewingAction.PAUSE


class TestRecordQuizAttemptWithSqliteRepository:
    """RecordQuizAttemptUseCase + SQLite Repository の受入基準。"""

    def test_first_attempt_persists_session_quiz_and_answers(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        use_case = _quiz_use_case(sqlite_learning_session_repository)

        result = use_case.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                attempted_at=FIXED_NOW,
                score_numerator=4,
                score_denominator=5,
                answers=_five_answers(wrong_at=3),
            )
        )

        assert isinstance(result, Ok)
        assert result.value.attempt_id == QuizAttemptId("1")
        assert _count_rows(learning_db_conn, "learning_sessions") == 1
        assert _count_rows(learning_db_conn, "quiz_attempts") == 1
        assert _count_rows(learning_db_conn, "quiz_attempt_answers") == 5

        loaded = sqlite_learning_session_repository.find_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId(DEFAULT_LECTURE_ID_VALUE)
        )
        assert loaded is not None
        assert loaded.id == result.value.session_id
        assert len(loaded.quiz_attempts) == 1
        attempt = loaded.quiz_attempts[0]
        assert attempt.id == QuizAttemptId("1")
        assert attempt.score_numerator == 4
        assert len(attempt.answers) == 5
        question_three = next(
            answer for answer in attempt.answers if answer.question_index == 3
        )
        assert question_three.is_correct is False

    def test_retake_appends_second_attempt_to_same_session(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        use_case = _quiz_use_case(sqlite_learning_session_repository)
        second_at = FIXED_NOW + timedelta(minutes=10)

        first = use_case.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                attempted_at=FIXED_NOW,
                score_numerator=4,
                score_denominator=5,
                answers=_five_answers(wrong_at=3),
            )
        )
        second = use_case.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                attempted_at=second_at,
                score_numerator=5,
                score_denominator=5,
                answers=_five_answers(),
            )
        )

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert second.value.session_id == first.value.session_id
        assert second.value.attempt_id == QuizAttemptId("2")
        assert _count_rows(learning_db_conn, "learning_sessions") == 1
        assert _count_rows(learning_db_conn, "quiz_attempts") == 2
        assert _count_rows(learning_db_conn, "quiz_attempt_answers") == 10

        loaded = sqlite_learning_session_repository.find_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId(DEFAULT_LECTURE_ID_VALUE)
        )
        assert loaded is not None
        assert len(loaded.quiz_attempts) == 2
        assert loaded.quiz_attempts[1].score_numerator == 5


class TestCombinedLearningWriteWithSqliteRepository:
    """同一 (learner_id, lecture_id) で session 1 行・視聴/小テスト複数行。"""

    def test_viewing_and_quiz_share_single_session_row(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        viewing_use_case = _viewing_use_case(sqlite_learning_session_repository)
        quiz_use_case = _quiz_use_case(sqlite_learning_session_repository)

        viewing_result = viewing_use_case.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                occurred_at=FIXED_NOW,
                video_position=60,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )
        quiz_result = quiz_use_case.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                attempted_at=FIXED_NOW + timedelta(minutes=5),
                score_numerator=5,
                score_denominator=5,
                answers=_five_answers(),
            )
        )

        assert isinstance(viewing_result, Ok)
        assert isinstance(quiz_result, Ok)
        assert quiz_result.value.session_id == viewing_result.value.session_id
        assert _count_rows(learning_db_conn, "learning_sessions") == 1
        assert _count_rows(learning_db_conn, "viewing_logs") == 1
        assert _count_rows(learning_db_conn, "quiz_attempts") == 1

        loaded = sqlite_learning_session_repository.find_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId(DEFAULT_LECTURE_ID_VALUE)
        )
        assert loaded is not None
        assert len(loaded.viewing_events) == 1
        assert len(loaded.quiz_attempts) == 1
