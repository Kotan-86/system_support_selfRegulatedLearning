# 仕様: docs/spec/application-usecase.md#StartOrGetTutorSession
"""StartOrGetTutorSession の Request / Response DTO。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.common.errors import ValidationError
from application.common.result import Result, err, ok
from application.common.start_or_get_outcome import StartOrGetOutcome
from domain.shared.ids import LearningSessionId, TutorSessionId
from domain.tutoring.tutor_session import TutorSession


@dataclass(frozen=True)
class StartOrGetTutorSessionRequest:
    """StartOrGetTutorSession の入力。"""

    learning_session_id: LearningSessionId
    started_at: datetime

    def validate(self) -> Result[StartOrGetTutorSessionRequest, ValidationError]:
        if not self.learning_session_id:
            return err(ValidationError("learning_session_id must not be empty"))
        return ok(self)


@dataclass(frozen=True)
class StartOrGetTutorSessionResponse:
    """StartOrGetTutorSession の出力。"""

    tutor_session_id: TutorSessionId
    session: TutorSession
    outcome: StartOrGetOutcome
