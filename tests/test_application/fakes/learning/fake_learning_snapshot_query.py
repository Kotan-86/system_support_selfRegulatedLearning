# 仕様: docs/spec/application-usecase.md#LearningSnapshotQuery（Tutoring → Learning ACL）
"""LearningSnapshotQuery の Fake 実装（テスト用）。"""
from __future__ import annotations

from domain.learning.learning_snapshot import LearningSnapshot
from domain.shared.ids import LectureId, LearnerId

from application.learning.ports.learning_snapshot_query import LearningSnapshotQuery


class FakeLearningSnapshotQuery(LearningSnapshotQuery):
    """設定済み Snapshot を返す Fake LearningSnapshotQuery。"""

    def __init__(
        self,
        snapshots: dict[tuple[LearnerId, LectureId], LearningSnapshot] | None = None,
    ) -> None:
        self._snapshots: dict[tuple[LearnerId, LectureId], LearningSnapshot] = (
            snapshots or {}
        )

    def get_by_learner_and_lecture(
        self, learner_id: LearnerId, lecture_id: LectureId
    ) -> LearningSnapshot:
        key = (learner_id, lecture_id)
        if key not in self._snapshots:
            raise KeyError(
                f"No snapshot configured for (learner_id={learner_id!r}, "
                f"lecture_id={lecture_id!r})"
            )
        return self._snapshots[key]

    def set_snapshot(
        self,
        learner_id: LearnerId,
        lecture_id: LectureId,
        snapshot: LearningSnapshot,
    ) -> None:
        """テスト用: 指定スコープの Snapshot を登録する。"""
        self._snapshots[(learner_id, lecture_id)] = snapshot
