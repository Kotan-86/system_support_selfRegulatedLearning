# 仕様: docs/spec/application-usecase.md#LearningSessionRepository
"""LearningSession 集約の永続化 Port。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.learning.learning_session import LearningSession
from domain.shared.ids import LectureId, LearnerId


class LearningSessionRepository(ABC):
    """1 学習者 × 1 講義の LearningSession 集約を永続化する。"""

    @abstractmethod
    def find_by_learner_and_lecture(
        self, learner_id: LearnerId, lecture_id: LectureId
    ) -> LearningSession | None:
        """指定 (learner_id, lecture_id) の Session を返す。存在しなければ None。"""

    @abstractmethod
    def list_by_learner(self, learner_id: LearnerId) -> tuple[LearningSession, ...]:
        """学習者に紐づく全 LearningSession を返す（重複チェック用）。"""

    @abstractmethod
    def save(self, session: LearningSession) -> LearningSession:
        """集約全体を upsert し、DB 確定後の集約を返す。"""

    def save_if_learner_has_none(self, session: LearningSession) -> LearningSession:
        """学習者に Session が無いときだけ保存し、保存後(または既存)の先頭 Session を返す。

        実装は、確認と保存を排他的に行うこと(同時の確定でも1件に保つ)。
        既定実装は排他しない(単一スレッド用)。
        """
        existing = self.list_by_learner(session.learner_id)
        if existing:
            return existing[0]
        return self.save(session)
