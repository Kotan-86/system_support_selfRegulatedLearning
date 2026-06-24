# 仕様: docs/spec/application-usecase.md#GetLearningSnapshot
"""GetLearningSnapshot の Request / Response DTO。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.common.errors import ValidationError
from application.common.result import Result, err, ok
from domain.learning.learning_snapshot import LearningSnapshot
from domain.shared.ids import LectureId, LearnerId


@dataclass(frozen=True)
class GetLearningSnapshotRequest:
    """GetLearningSnapshot の入力。"""

    learner_id: LearnerId
    lecture_id: LectureId

    def validate(self) -> Result[GetLearningSnapshotRequest, ValidationError]:
        if not self.learner_id:
            return err(ValidationError("learner_id must not be empty"))
        if not self.lecture_id:
            return err(ValidationError("lecture_id must not be empty"))
        return ok(self)


@dataclass(frozen=True)
class GetLearningSnapshotResponse:
    """GetLearningSnapshot の出力。"""

    snapshot: LearningSnapshot
    content_updated_at: datetime | None
