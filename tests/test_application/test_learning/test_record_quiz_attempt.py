# 仕様: docs/spec/application-usecase.md#RecordQuizAttempt
"""RecordQuizAttemptUseCase の受入基準テスト。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from application.common.errors import ErrorCode, LectureNotFoundError, ValidationError
from application.common.result import Err, Ok
from application.learning.dto.record_quiz_attempt import RecordQuizAttemptRequest
from application.learning.use_cases.record_quiz_attempt import RecordQuizAttemptUseCase
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from domain.learning.lecture import Lecture
from domain.learning.quiz_attempt import QuizAnswer
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.shared.ids import LectureId, LearnerId, LearningSessionId, QuizAttemptId
from tests.test_application.fakes.learning.fake_id_generators import (
    FakeLearningSessionIdGenerator,
    FakeQuizAttemptIdGenerator,
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


def _request(
    *,
    learner_id: str = "learner-1",
    lecture_id: str = "lecture-1",
    attempted_at: datetime = FIXED_NOW,
    score_numerator: int = 4,
    score_denominator: int = 5,
    answers: tuple[QuizAnswer, ...] | None = None,
) -> RecordQuizAttemptRequest:
    return RecordQuizAttemptRequest(
        learner_id=LearnerId(learner_id),
        lecture_id=LectureId(lecture_id),
        attempted_at=attempted_at,
        score_numerator=score_numerator,
        score_denominator=score_denominator,
        answers=answers if answers is not None else _five_answers(wrong_at=3),
    )


def _use_case(
    repository: InMemoryLearningSessionRepository | None = None,
    *,
    lectures: tuple[Lecture, ...] | None = None,
) -> RecordQuizAttemptUseCase:
    repo = repository or InMemoryLearningSessionRepository()
    catalog = FakeLectureCatalog(
        lectures=lectures if lectures is not None else (_lecture(),)
    )
    return RecordQuizAttemptUseCase(
        start_or_get=StartOrGetLearningSessionUseCase(
            repository=repo,
            id_generator=FakeLearningSessionIdGenerator(),
        ),
        lecture_catalog=catalog,
        quiz_attempt_id_generator=FakeQuizAttemptIdGenerator(),
        repository=repo,
    )


class TestRecordQuizAttemptAcceptance:
    """受入基準を executable spec として検証する。"""

    def test_first_attempt_creates_session_via_start_or_get(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert result.value.attempt_id == QuizAttemptId("qa-1")
        assert result.value.session_id == LearningSessionId("ls-1")
        assert repository.save_count == 2
        sessions = repository.all_sessions()
        assert len(sessions) == 1
        session = sessions[0]
        assert session.learner_id == LearnerId("learner-1")
        assert session.lecture_id == LectureId("lecture-1")
        assert len(session.quiz_attempts) == 1
        attempt = session.quiz_attempts[0]
        assert attempt.id == QuizAttemptId("qa-1")
        assert attempt.score_numerator == 4
        assert attempt.score_denominator == 5
        assert len(attempt.answers) == 5

    def test_retake_appends_second_attempt_to_same_session(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)
        second_at = FIXED_NOW + timedelta(minutes=10)

        first = use_case.execute(_request())
        save_count_after_first = repository.save_count
        second = use_case.execute(
            _request(
                attempted_at=second_at,
                score_numerator=5,
                answers=_five_answers(),
            )
        )

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert second.value.session_id == first.value.session_id
        assert second.value.attempt_id == QuizAttemptId("qa-2")
        assert repository.save_count == save_count_after_first + 1
        session = repository.all_sessions()[0]
        assert len(session.quiz_attempts) == 2
        assert session.quiz_attempts[1].attempted_at == second_at
        assert session.quiz_attempts[1].score_numerator == 5

    def test_missing_lecture_returns_lecture_not_found(self) -> None:
        use_case = _use_case(lectures=())

        result = use_case.execute(_request(lecture_id="missing-lecture"))

        assert isinstance(result, Err)
        assert isinstance(result.error, LectureNotFoundError)
        assert result.error.code == ErrorCode.LECTURE_NOT_FOUND

    def test_unknown_question_index_is_rejected(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)
        answers = _five_answers()
        invalid_answers = answers[:-1] + (
            QuizAnswer(
                question_index=99,
                selected_answer="A",
                is_correct=False,
            ),
        )

        result = use_case.execute(_request(answers=invalid_answers))

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code == ErrorCode.UNKNOWN_QUESTION_INDEX
        assert repository.save_count == 0

    def test_five_question_format_is_persisted(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)
        answers = _five_answers(wrong_at=3)

        result = use_case.execute(_request(answers=answers))

        assert isinstance(result, Ok)
        attempt = repository.all_sessions()[0].quiz_attempts[0]
        assert len(attempt.answers) == 5
        assert {answer.question_index for answer in attempt.answers} == {1, 2, 3, 4, 5}

    def test_question_three_incorrect_answer_is_persisted(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)
        answers = _five_answers(wrong_at=3)

        result = use_case.execute(_request(answers=answers))

        assert isinstance(result, Ok)
        attempt = repository.all_sessions()[0].quiz_attempts[0]
        question_three = next(
            answer for answer in attempt.answers if answer.question_index == 3
        )
        assert question_three.is_correct is False
        assert question_three.selected_answer == "B"


class TestRecordQuizAttemptValidation:
    """Request 検証と小テスト不変条件を検証する。"""

    def test_empty_learner_id_returns_validation_error(self) -> None:
        request = RecordQuizAttemptRequest(
            learner_id=str.__new__(LearnerId, ""),
            lecture_id=LectureId("lecture-1"),
            attempted_at=FIXED_NOW,
            score_numerator=1,
            score_denominator=5,
            answers=_five_answers(),
        )
        use_case = _use_case()

        result = use_case.execute(request)

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code == ErrorCode.VALIDATION_ERROR

    def test_duplicate_question_index_returns_invalid_quiz_attempt(self) -> None:
        use_case = _use_case()
        answers = (
            QuizAnswer(question_index=1, selected_answer="A", is_correct=True),
            QuizAnswer(question_index=1, selected_answer="B", is_correct=False),
        )

        result = use_case.execute(
            _request(
                score_numerator=1,
                score_denominator=5,
                answers=answers,
            )
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code == ErrorCode.INVALID_QUIZ_ATTEMPT

    def test_invalid_quiz_attempt_does_not_call_save(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _use_case(repository=repository)

        result = use_case.execute(
            _request(score_numerator=6, score_denominator=5)
        )

        assert isinstance(result, Err)
        assert repository.save_count == 0
