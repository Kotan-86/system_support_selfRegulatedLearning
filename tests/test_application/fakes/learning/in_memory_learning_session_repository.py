# 仕様: docs/spec/application-usecase.md#LearningSessionRepository
"""LearningSessionRepository の InMemory 実装（テスト用）。"""
from __future__ import annotations

from domain.learning.learning_session import LearningSession
from domain.shared.ids import LectureId, LearnerId, LearningSessionId

from application.learning.ports.learning_session_repository import (
    LearningSessionRepository,
)


class InMemoryLearningSessionRepository(LearningSessionRepository):
    """dict ベースの InMemory LearningSessionRepository。"""

    def __init__(self, sessions: tuple[LearningSession, ...] = ()) -> None:
        self._sessions: dict[LearningSessionId, LearningSession] = {
            session.id: session for session in sessions
        }
        self.save_count = 0

    def find_by_learner_and_lecture(
        self, learner_id: LearnerId, lecture_id: LectureId
    ) -> LearningSession | None:
        for session in self._sessions.values():
            if session.learner_id == learner_id and session.lecture_id == lecture_id:
                return session
        return None

    def list_by_learner(self, learner_id: LearnerId) -> tuple[LearningSession, ...]:
        return tuple(
            session
            for session in self._sessions.values()
            if session.learner_id == learner_id
        )

    def save(self, session: LearningSession) -> None:
        self._sessions[session.id] = session
        self.save_count += 1

    def all_sessions(self) -> tuple[LearningSession, ...]:
        """テスト用: 保存済み Session をすべて返す。"""
        return tuple(self._sessions.values())
