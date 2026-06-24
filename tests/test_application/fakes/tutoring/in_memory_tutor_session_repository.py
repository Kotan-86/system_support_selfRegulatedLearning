# 仕様: docs/spec/application-usecase.md#TutorSessionRepository
"""TutorSessionRepository の InMemory 実装（テスト用）。"""
from __future__ import annotations

from domain.shared.ids import LearningSessionId, TutorSessionId
from domain.tutoring.tutor_session import TutorSession

from application.tutoring.ports.tutor_session_repository import TutorSessionRepository


class InMemoryTutorSessionRepository(TutorSessionRepository):
    """dict ベースの InMemory TutorSessionRepository。"""

    def __init__(self, sessions: tuple[TutorSession, ...] = ()) -> None:
        self._sessions: dict[TutorSessionId, TutorSession] = {
            session.id: session for session in sessions
        }
        self.save_count = 0

    def find_by_id(self, tutor_session_id: TutorSessionId) -> TutorSession | None:
        return self._sessions.get(tutor_session_id)

    def find_by_learning_session_id(
        self, learning_session_id: LearningSessionId
    ) -> TutorSession | None:
        for session in self._sessions.values():
            if session.learning_session_id == learning_session_id:
                return session
        return None

    def list_all(self) -> tuple[TutorSession, ...]:
        return tuple(self._sessions.values())

    def save(self, session: TutorSession) -> None:
        self._sessions[session.id] = session
        self.save_count += 1

    def all_sessions(self) -> tuple[TutorSession, ...]:
        """テスト用: 保存済み Session をすべて返す。"""
        return tuple(self._sessions.values())
