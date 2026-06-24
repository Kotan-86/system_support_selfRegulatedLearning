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
    def save(self, session: LearningSession) -> None:
        """集約全体を upsert する。"""
