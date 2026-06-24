# 仕様: docs/spec/application-usecase.md#TutorSessionIdGenerator
# 仕様: docs/spec/application-usecase.md#MessageIdGenerator
"""Tutoring コンテキストの ID 生成 Port。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.shared.ids import MessageId, TutorSessionId


class TutorSessionIdGenerator(ABC):
    """TutorSessionId を生成する。"""

    @abstractmethod
    def next_id(self) -> TutorSessionId:
        """次の TutorSessionId を返す。"""


class MessageIdGenerator(ABC):
    """MessageId を生成する。"""

    @abstractmethod
    def next_id(self) -> MessageId:
        """次の MessageId を返す。"""
