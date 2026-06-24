# 仕様: docs/spec/application-usecase.md#LearningSessionIdGenerator
# 仕様: docs/spec/application-usecase.md#ViewingEventIdGenerator
# 仕様: docs/spec/application-usecase.md#QuizAttemptIdGenerator
"""Learning コンテキストの ID 生成 Port。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.shared.ids import LearningSessionId, QuizAttemptId, ViewingEventId


class LearningSessionIdGenerator(ABC):
    """LearningSessionId を生成する。"""

    @abstractmethod
    def next_id(self) -> LearningSessionId:
        """次の LearningSessionId を返す。"""


class ViewingEventIdGenerator(ABC):
    """ViewingEventId を生成する。"""

    @abstractmethod
    def next_id(self) -> ViewingEventId:
        """次の ViewingEventId を返す。"""


class QuizAttemptIdGenerator(ABC):
    """QuizAttemptId を生成する。"""

    @abstractmethod
    def next_id(self) -> QuizAttemptId:
        """次の QuizAttemptId を返す。"""
