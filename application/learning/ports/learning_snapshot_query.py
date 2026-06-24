# 仕様: docs/spec/application-usecase.md#LearningSnapshotQuery（Tutoring → Learning ACL）
"""LAD と AI 共通の学習コンテキスト Read Port（Tutoring ACL）。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.learning.learning_snapshot import LearningSnapshot
from domain.shared.ids import LectureId, LearnerId


class LearningSnapshotQuery(ABC):
    """GetLearningSnapshot と同一 Read 契約。Tutoring は Learning Entity を import せず利用する。"""

    @abstractmethod
    def get_by_learner_and_lecture(
        self, learner_id: LearnerId, lecture_id: LectureId
    ) -> LearningSnapshot:
        """指定スコープの LearningSnapshot を返す。"""
