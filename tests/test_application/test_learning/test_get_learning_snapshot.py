# 仕様: docs/spec/application-usecase.md#GetLearningSnapshot
"""GetLearningSnapshotUseCase の受入基準テスト。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from application.common.errors import ErrorCode, LectureNotFoundError, ValidationError
from application.common.result import Err, Ok
from application.learning.adapters.get_learning_snapshot_query import (
    GetLearningSnapshotQuery,
)
from application.learning.dto.get_learning_snapshot import GetLearningSnapshotRequest
from application.learning.dto.record_quiz_attempt import RecordQuizAttemptRequest
from application.learning.dto.record_viewing_event import RecordViewingEventRequest
from application.learning.use_cases.get_learning_snapshot import GetLearningSnapshotUseCase
from application.learning.use_cases.record_quiz_attempt import RecordQuizAttemptUseCase
from application.learning.use_cases.record_viewing_event import RecordViewingEventUseCase
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from domain.learning.lecture import Lecture
from domain.learning.quiz_attempt import QuizAnswer
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.learning.viewing_event import ViewingAction
from domain.shared.ids import LectureId, LearnerId
from tests.test_application.fakes.learning.fake_id_generators import (
    FakeLearningSessionIdGenerator,
    FakeQuizAttemptIdGenerator,
    FakeViewingEventIdGenerator,
)
from tests.test_application.fakes.learning.fake_lecture_catalog import FakeLectureCatalog
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _five_question_quiz_definition() -> QuizDefinition:
    return QuizDefinition(
        questions=tuple(
            Question(
                index=index,
                text=f"問{index}",
                choices=("A", "B", "C"),
                correct_answer="A",
            )
            for index in range(1, 6)
        )
    )


def _lecture(*, lecture_id: str = "lecture-1") -> Lecture:
    return Lecture.create(
        id=LectureId(lecture_id),
        title="サンプル講義",
        video_url="https://example.com/video.mp4",
        srt_path="/path/to/subtitles.srt",
        quiz_definition=_five_question_quiz_definition(),
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


def _get_snapshot_use_case(
    repository: InMemoryLearningSessionRepository | None = None,
    *,
    lectures: tuple[Lecture, ...] | None = None,
) -> GetLearningSnapshotUseCase:
    repo = repository or InMemoryLearningSessionRepository()
    catalog = FakeLectureCatalog(
        lectures=lectures if lectures is not None else (_lecture(),)
    )
    return GetLearningSnapshotUseCase(repository=repo, lecture_catalog=catalog)


def _record_viewing_use_case(
    repository: InMemoryLearningSessionRepository,
) -> RecordViewingEventUseCase:
    return RecordViewingEventUseCase(
        start_or_get=StartOrGetLearningSessionUseCase(
            repository=repository,
            id_generator=FakeLearningSessionIdGenerator(),
        ),
        viewing_event_id_generator=FakeViewingEventIdGenerator(),
        repository=repository,
    )


def _record_quiz_use_case(
    repository: InMemoryLearningSessionRepository,
    *,
    lectures: tuple[Lecture, ...] | None = None,
) -> RecordQuizAttemptUseCase:
    return RecordQuizAttemptUseCase(
        start_or_get=StartOrGetLearningSessionUseCase(
            repository=repository,
            id_generator=FakeLearningSessionIdGenerator(),
        ),
        lecture_catalog=FakeLectureCatalog(
            lectures=lectures if lectures is not None else (_lecture(),)
        ),
        quiz_attempt_id_generator=FakeQuizAttemptIdGenerator(),
        repository=repository,
    )


def _request(
    *,
    learner_id: str = "learner-1",
    lecture_id: str = "lecture-1",
) -> GetLearningSnapshotRequest:
    return GetLearningSnapshotRequest(
        learner_id=LearnerId(learner_id),
        lecture_id=LectureId(lecture_id),
    )


class TestGetLearningSnapshotAcceptance:
    """受入基準を executable spec として検証する。"""

    def test_same_snapshot_for_lad_and_query_adapter(self) -> None:
        repository = InMemoryLearningSessionRepository()
        get_snapshot = _get_snapshot_use_case(repository=repository)
        adapter = GetLearningSnapshotQuery(get_snapshot)
        record_viewing = _record_viewing_use_case(repository)
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                occurred_at=FIXED_NOW,
                video_position=120,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )

        use_case_result = get_snapshot.execute(_request())
        adapter_snapshot = adapter.get_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId("lecture-1")
        )

        assert isinstance(use_case_result, Ok)
        assert adapter_snapshot == use_case_result.value.snapshot

    def test_after_record_viewing_event_snapshot_contains_new_event(self) -> None:
        repository = InMemoryLearningSessionRepository()
        get_snapshot = _get_snapshot_use_case(repository=repository)
        record_viewing = _record_viewing_use_case(repository)
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                occurred_at=FIXED_NOW,
                video_position=120,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )

        result = get_snapshot.execute(_request())

        assert isinstance(result, Ok)
        snapshot = result.value.snapshot
        assert len(snapshot.viewing_events) == 1
        assert snapshot.viewing_events[0].video_position == 120
        assert snapshot.viewing_events[0].action == ViewingAction.PLAY
        assert result.value.content_updated_at == FIXED_NOW

    def test_after_record_quiz_attempt_latest_quiz_attempt_is_updated(self) -> None:
        repository = InMemoryLearningSessionRepository()
        get_snapshot = _get_snapshot_use_case(repository=repository)
        record_quiz = _record_quiz_use_case(repository)
        first_at = FIXED_NOW
        second_at = FIXED_NOW + timedelta(minutes=10)
        record_quiz.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                attempted_at=first_at,
                score_numerator=4,
                score_denominator=5,
                answers=_five_answers(wrong_at=3),
            )
        )
        record_quiz.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                attempted_at=second_at,
                score_numerator=5,
                score_denominator=5,
                answers=_five_answers(),
            )
        )

        result = get_snapshot.execute(_request())

        assert isinstance(result, Ok)
        snapshot = result.value.snapshot
        assert snapshot.latest_quiz_attempt is not None
        assert snapshot.latest_quiz_attempt.attempted_at == second_at
        assert snapshot.latest_quiz_attempt.score_numerator == 5
        assert result.value.content_updated_at == second_at

    def test_quiz_answers_preserve_question_index_and_is_correct(self) -> None:
        repository = InMemoryLearningSessionRepository()
        get_snapshot = _get_snapshot_use_case(repository=repository)
        record_quiz = _record_quiz_use_case(repository)
        record_quiz.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                attempted_at=FIXED_NOW,
                score_numerator=4,
                score_denominator=5,
                answers=_five_answers(wrong_at=3),
            )
        )

        result = get_snapshot.execute(_request())

        assert isinstance(result, Ok)
        answers = result.value.snapshot.quiz_answers
        assert len(answers) == 5
        question_three = next(
            answer for answer in answers if answer.question_index == 3
        )
        assert question_three.is_correct is False
        assert question_three.selected_answer == "B"

    def test_snapshot_scope_is_single_learning_session(self) -> None:
        repository = InMemoryLearningSessionRepository()
        get_snapshot = _get_snapshot_use_case(
            repository=repository,
            lectures=(_lecture(lecture_id="lecture-1"), _lecture(lecture_id="lecture-2")),
        )
        record_viewing = _record_viewing_use_case(repository)
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                occurred_at=FIXED_NOW,
                video_position=100,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-2"),
                occurred_at=FIXED_NOW + timedelta(minutes=1),
                video_position=200,
                action=ViewingAction.PAUSE,
                position_delta=0,
            )
        )

        result = get_snapshot.execute(
            _request(learner_id="learner-1", lecture_id="lecture-1")
        )

        assert isinstance(result, Ok)
        snapshot = result.value.snapshot
        assert snapshot.lecture_id == LectureId("lecture-1")
        assert len(snapshot.viewing_events) == 1
        assert snapshot.viewing_events[0].video_position == 100

    def test_builder_does_not_return_prompt_string(self) -> None:
        repository = InMemoryLearningSessionRepository()
        get_snapshot = _get_snapshot_use_case(repository=repository)
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

        result = get_snapshot.execute(_request())

        assert isinstance(result, Ok)
        assert not isinstance(result.value.snapshot, str)

    def test_no_session_returns_empty_snapshot_with_none_content_updated_at(self) -> None:
        get_snapshot = _get_snapshot_use_case()

        result = get_snapshot.execute(_request())

        assert isinstance(result, Ok)
        snapshot = result.value.snapshot
        assert snapshot.learner_id == LearnerId("learner-1")
        assert snapshot.lecture_id == LectureId("lecture-1")
        assert snapshot.viewing_events == ()
        assert snapshot.latest_quiz_attempt is None
        assert snapshot.quiz_answers == ()
        assert result.value.content_updated_at is None

    def test_missing_lecture_returns_lecture_not_found(self) -> None:
        get_snapshot = _get_snapshot_use_case(lectures=())

        result = get_snapshot.execute(_request(lecture_id="missing-lecture"))

        assert isinstance(result, Err)
        assert isinstance(result.error, LectureNotFoundError)
        assert result.error.code == ErrorCode.LECTURE_NOT_FOUND


class TestGetLearningSnapshotQueryAdapter:
    """LearningSnapshotQuery Adapter の振る舞いを検証する。"""

    def test_adapter_returns_empty_snapshot_when_session_not_created(self) -> None:
        get_snapshot = _get_snapshot_use_case()
        adapter = GetLearningSnapshotQuery(get_snapshot)

        snapshot = adapter.get_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId("lecture-1")
        )

        assert snapshot.viewing_events == ()
        assert snapshot.latest_quiz_attempt is None

    def test_adapter_raises_lecture_not_found_error(self) -> None:
        get_snapshot = _get_snapshot_use_case(lectures=())
        adapter = GetLearningSnapshotQuery(get_snapshot)

        with pytest.raises(LectureNotFoundError):
            adapter.get_by_learner_and_lecture(
                LearnerId("learner-1"), LectureId("missing-lecture")
            )


class TestGetLearningSnapshotContentUpdatedAt:
    """content_updated_at の算出を検証する。"""

    def test_max_of_viewing_and_quiz_event_times(self) -> None:
        repository = InMemoryLearningSessionRepository()
        get_snapshot = _get_snapshot_use_case(repository=repository)
        record_viewing = _record_viewing_use_case(repository)
        record_quiz = _record_quiz_use_case(repository)
        viewing_at = FIXED_NOW
        quiz_at = FIXED_NOW + timedelta(minutes=5)
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                occurred_at=viewing_at,
                video_position=10,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )
        record_quiz.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                attempted_at=quiz_at,
                score_numerator=5,
                score_denominator=5,
                answers=_five_answers(),
            )
        )

        result = get_snapshot.execute(_request())

        assert isinstance(result, Ok)
        assert result.value.content_updated_at == quiz_at


class TestGetLearningSnapshotValidation:
    """Request 検証を検証する。"""

    def test_empty_learner_id_returns_validation_error(self) -> None:
        request = GetLearningSnapshotRequest(
            learner_id=str.__new__(LearnerId, ""),
            lecture_id=LectureId("lecture-1"),
        )
        get_snapshot = _get_snapshot_use_case()

        result = get_snapshot.execute(request)

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code == ErrorCode.VALIDATION_ERROR
