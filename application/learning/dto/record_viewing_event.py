# 仕様: docs/spec/application-usecase.md#RecordViewingEvent
"""RecordViewingEvent の Request / Response DTO。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.common.errors import ValidationError
from application.common.result import Result, err, ok
from domain.learning.viewing_event import ViewingAction
from domain.shared.ids import LectureId, LearnerId, LearningSessionId, ViewingEventId


@dataclass(frozen=True)
class RecordViewingEventRequest:
    """RecordViewingEvent の入力。"""

    learner_id: LearnerId
    lecture_id: LectureId
    occurred_at: datetime
    video_position: int
    action: ViewingAction
    position_delta: int

    def validate(self) -> Result[RecordViewingEventRequest, ValidationError]:
        if not self.learner_id:
            return err(ValidationError("learner_id must not be empty"))
        if not self.lecture_id:
            return err(ValidationError("lecture_id must not be empty"))
        return ok(self)


@dataclass(frozen=True)
class RecordViewingEventResponse:
    """RecordViewingEvent の出力。"""

    event_id: ViewingEventId
    session_id: LearningSessionId
