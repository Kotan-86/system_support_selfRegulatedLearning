# 仕様: docs/spec/application-usecase.md#RecordQuizAttempt
"""RecordQuizAttempt の Request / Response DTO。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.common.errors import ValidationError
from application.common.result import Result, err, ok
from domain.learning.quiz_attempt import QuizAnswer
from domain.shared.ids import LectureId, LearnerId, LearningSessionId, QuizAttemptId


@dataclass(frozen=True)
class RecordQuizAttemptRequest:
    """RecordQuizAttempt の入力。"""

    learner_id: LearnerId
    lecture_id: LectureId
    attempted_at: datetime
    score_numerator: int
    score_denominator: int
    answers: tuple[QuizAnswer, ...]

    def validate(self) -> Result[RecordQuizAttemptRequest, ValidationError]:
        if not self.learner_id:
            return err(ValidationError("learner_id must not be empty"))
        if not self.lecture_id:
            return err(ValidationError("lecture_id must not be empty"))
        return ok(self)


@dataclass(frozen=True)
class RecordQuizAttemptResponse:
    """RecordQuizAttempt の出力。"""

    attempt_id: QuizAttemptId
    session_id: LearningSessionId
