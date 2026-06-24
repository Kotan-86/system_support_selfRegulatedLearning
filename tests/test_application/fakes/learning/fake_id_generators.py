# 仕様: docs/spec/application-usecase.md#LearningSessionIdGenerator
# 仕様: docs/spec/application-usecase.md#ViewingEventIdGenerator
# 仕様: docs/spec/application-usecase.md#QuizAttemptIdGenerator
"""ID Generator Port の Fake 実装（テスト用）。"""
from __future__ import annotations

from domain.shared.ids import LearningSessionId, QuizAttemptId, ViewingEventId

from application.learning.ports.id_generators import (
    LearningSessionIdGenerator,
    QuizAttemptIdGenerator,
    ViewingEventIdGenerator,
)


class FakeLearningSessionIdGenerator(LearningSessionIdGenerator):
    """連番 UUID 形式の LearningSessionId を生成する Fake。"""

    def __init__(self, *, prefix: str = "ls", start: int = 1) -> None:
        self._prefix = prefix
        self._next = start

    def next_id(self) -> LearningSessionId:
        value = f"{self._prefix}-{self._next}"
        self._next += 1
        return LearningSessionId(value)


class FakeViewingEventIdGenerator(ViewingEventIdGenerator):
    """連番 UUID 形式の ViewingEventId を生成する Fake。"""

    def __init__(self, *, prefix: str = "ve", start: int = 1) -> None:
        self._prefix = prefix
        self._next = start

    def next_id(self) -> ViewingEventId:
        value = f"{self._prefix}-{self._next}"
        self._next += 1
        return ViewingEventId(value)


class FakeQuizAttemptIdGenerator(QuizAttemptIdGenerator):
    """連番 UUID 形式の QuizAttemptId を生成する Fake。"""

    def __init__(self, *, prefix: str = "qa", start: int = 1) -> None:
        self._prefix = prefix
        self._next = start

    def next_id(self) -> QuizAttemptId:
        value = f"{self._prefix}-{self._next}"
        self._next += 1
        return QuizAttemptId(value)
