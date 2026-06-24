# 仕様: docs/spec/application-usecase.md#TutorSessionRepository
"""TutorSession 集約の永続化 Port。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.shared.ids import LearningSessionId, TutorSessionId
from domain.tutoring.tutor_session import TutorSession


class TutorSessionRepository(ABC):
    """TutorSession 集約を永続化する。"""

    @abstractmethod
    def find_by_id(self, tutor_session_id: TutorSessionId) -> TutorSession | None:
        """指定 tutor_session_id の Session を返す。存在しなければ None。"""

    @abstractmethod
    def find_by_learning_session_id(
        self, learning_session_id: LearningSessionId
    ) -> TutorSession | None:
        """指定 learning_session_id に紐づく TutorSession を返す。存在しなければ None。"""

    @abstractmethod
    def list_all(self) -> tuple[TutorSession, ...]:
        """全 TutorSession を返す（NearTermExperimentPolicy 用）。"""

    @abstractmethod
    def save(self, session: TutorSession) -> None:
        """集約全体を upsert する。"""
