# 仕様: docs/spec/application-usecase.md#RecordQuizAttempt
# 仕様: docs/spec/application-error-handling.md#RecordQuizAttempt
"""RecordQuizAttempt ユースケース。"""
from __future__ import annotations

from application.common.errors import (
    AppError,
    ErrorCode,
    LectureNotFoundError,
    ValidationError,
)
from application.common.result import Result, err, ok
from application.learning.dto.record_quiz_attempt import (
    RecordQuizAttemptRequest,
    RecordQuizAttemptResponse,
)
from application.learning.dto.start_or_get_learning_session import (
    StartOrGetLearningSessionRequest,
)
from application.learning.ports.id_generators import QuizAttemptIdGenerator
from application.learning.ports.learning_session_repository import (
    LearningSessionRepository,
)
from application.learning.ports.lecture_catalog import LectureCatalog
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from domain.learning.quiz_attempt import QuizAnswer
from domain.learning.quiz_definition import QuizDefinition


def _valid_question_indexes(quiz_definition: QuizDefinition) -> frozenset[int]:
    return frozenset(question.index for question in quiz_definition.questions)


def _validate_question_indexes(
    answers: tuple[QuizAnswer, ...],
    valid_indexes: frozenset[int],
) -> Result[None, ValidationError]:
    for answer in answers:
        if answer.question_index not in valid_indexes:
            return err(
                ValidationError(
                    f"unknown question_index: {answer.question_index}",
                    ErrorCode.UNKNOWN_QUESTION_INDEX,
                )
            )
    return ok(None)


def _validate_quiz_invariants(
    score_numerator: int,
    score_denominator: int,
    answers: tuple[QuizAnswer, ...],
) -> Result[None, ValidationError]:
    if score_denominator <= 0:
        return err(
            ValidationError(
                "score_denominator must be greater than 0",
                ErrorCode.INVALID_QUIZ_ATTEMPT,
            )
        )
    if score_numerator < 0 or score_numerator > score_denominator:
        return err(
            ValidationError(
                "score_numerator must satisfy 0 <= score_numerator <= score_denominator",
                ErrorCode.INVALID_QUIZ_ATTEMPT,
            )
        )
    if len(answers) < 1:
        return err(
            ValidationError(
                "answers must contain at least one item",
                ErrorCode.INVALID_QUIZ_ATTEMPT,
            )
        )

    indexes = [answer.question_index for answer in answers]
    if len(indexes) != len(set(indexes)):
        return err(
            ValidationError(
                "question_index must be unique within answers",
                ErrorCode.INVALID_QUIZ_ATTEMPT,
            )
        )
    return ok(None)


class RecordQuizAttemptUseCase:
    """小テスト受験 1 回を LearningSession 集約に追記する。"""

    def __init__(
        self,
        start_or_get: StartOrGetLearningSessionUseCase,
        lecture_catalog: LectureCatalog,
        quiz_attempt_id_generator: QuizAttemptIdGenerator,
        repository: LearningSessionRepository,
    ) -> None:
        self._start_or_get = start_or_get
        self._lecture_catalog = lecture_catalog
        self._quiz_attempt_id_generator = quiz_attempt_id_generator
        self._repository = repository

    def execute(
        self, request: RecordQuizAttemptRequest
    ) -> Result[RecordQuizAttemptResponse, AppError]:
        validated = request.validate()
        if validated.is_err:
            return validated  # type: ignore[return-value]

        req = validated.value
        lecture = self._lecture_catalog.find_by_id(req.lecture_id)
        if lecture is None:
            return err(
                LectureNotFoundError(
                    f"lecture not found: {req.lecture_id!s}"
                )
            )

        question_valid = _validate_question_indexes(
            req.answers,
            _valid_question_indexes(lecture.quiz_definition),
        )
        if question_valid.is_err:
            return question_valid  # type: ignore[return-value]

        quiz_valid = _validate_quiz_invariants(
            req.score_numerator,
            req.score_denominator,
            req.answers,
        )
        if quiz_valid.is_err:
            return quiz_valid  # type: ignore[return-value]

        session_result = self._start_or_get.execute(
            StartOrGetLearningSessionRequest(
                learner_id=req.learner_id,
                lecture_id=req.lecture_id,
                started_at=req.attempted_at,
            )
        )
        if session_result.is_err:
            return session_result  # type: ignore[return-value]

        session = session_result.value.session
        attempt_id = self._quiz_attempt_id_generator.next_id()
        updated = session.record_quiz_attempt(
            attempt_id=attempt_id,
            attempted_at=req.attempted_at,
            score_numerator=req.score_numerator,
            score_denominator=req.score_denominator,
            answers=req.answers,
        )
        self._repository.save(updated)
        return ok(
            RecordQuizAttemptResponse(
                attempt_id=attempt_id,
                session_id=updated.id,
            )
        )
