# 仕様: docs/spec/application-usecase.md#LearningSnapshotQuery（Tutoring → Learning ACL）
"""GetLearningSnapshotUseCase を LearningSnapshotQuery Port へ適合させる Adapter。"""
from __future__ import annotations

from application.learning.dto.get_learning_snapshot import GetLearningSnapshotRequest
from application.learning.ports.learning_snapshot_query import LearningSnapshotQuery
from application.learning.use_cases.get_learning_snapshot import (
    GetLearningSnapshotUseCase,
)
from domain.learning.learning_snapshot import LearningSnapshot
from domain.shared.ids import LectureId, LearnerId


class GetLearningSnapshotQuery(LearningSnapshotQuery):
    """GetLearningSnapshotUseCase を Tutoring ACL 向け Port として公開する。"""

    def __init__(self, use_case: GetLearningSnapshotUseCase) -> None:
        self._use_case = use_case

    def get_by_learner_and_lecture(
        self, learner_id: LearnerId, lecture_id: LectureId
    ) -> LearningSnapshot:
        result = self._use_case.execute(
            GetLearningSnapshotRequest(
                learner_id=learner_id,
                lecture_id=lecture_id,
            )
        )
        if result.is_err:
            raise result.error
        return result.value.snapshot
