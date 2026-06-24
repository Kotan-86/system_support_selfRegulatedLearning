# 仕様: docs/spec/application-usecase.md#StartOrGetLearningSession
"""StartOrGetLearningSession の Request / Response DTO。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.common.errors import ValidationError
from application.common.result import Result, err, ok
from application.common.start_or_get_outcome import StartOrGetOutcome
from domain.learning.learning_session import LearningSession
from domain.shared.ids import LectureId, LearnerId, LearningSessionId


@dataclass(frozen=True)
class StartOrGetLearningSessionRequest:
    """StartOrGetLearningSession の入力。"""

    learner_id: LearnerId
    lecture_id: LectureId
    started_at: datetime

    def validate(self) -> Result[StartOrGetLearningSessionRequest, ValidationError]:
        if not self.learner_id:
            return err(ValidationError("learner_id must not be empty"))
        if not self.lecture_id:
            return err(ValidationError("lecture_id must not be empty"))
        return ok(self)


@dataclass(frozen=True)
class StartOrGetLearningSessionResponse:
    """StartOrGetLearningSession の出力。"""

    session_id: LearningSessionId
    session: LearningSession
    outcome: StartOrGetOutcome
