# 仕様: docs/spec/domain-model.md#Shared Kernel — Value Object
# 仕様: docs/spec/domain-implementation-plan.md Phase 0
"""Shared Kernel の ID 型（Value Object）。"""
from __future__ import annotations

from typing import TypeVar

T = TypeVar("T", bound=str)


def _create_id_type(name: str) -> type[str]:
    """非空文字列を不変条件とする ID 型を生成する。"""

    class _Id(str):
        def __new__(cls, value: str) -> _Id:
            if not value:
                raise ValueError(f"{name} must not be empty")
            return super().__new__(cls, value)

    _Id.__name__ = name
    _Id.__qualname__ = name
    return _Id


LearnerId = _create_id_type("LearnerId")
LectureId = _create_id_type("LectureId")
LearningSessionId = _create_id_type("LearningSessionId")
ViewingEventId = _create_id_type("ViewingEventId")
QuizAttemptId = _create_id_type("QuizAttemptId")
TutorSessionId = _create_id_type("TutorSessionId")
MessageId = _create_id_type("MessageId")
ParticipantProgramId = _create_id_type("ParticipantProgramId")
ProgramId = _create_id_type("ProgramId")
