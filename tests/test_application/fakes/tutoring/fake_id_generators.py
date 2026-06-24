# 仕様: docs/spec/application-usecase.md#TutorSessionIdGenerator
# 仕様: docs/spec/application-usecase.md#MessageIdGenerator
"""Tutoring ID Generator Port の Fake 実装（テスト用）。"""
from __future__ import annotations

from domain.shared.ids import MessageId, TutorSessionId

from application.tutoring.ports.id_generators import MessageIdGenerator, TutorSessionIdGenerator


class FakeTutorSessionIdGenerator(TutorSessionIdGenerator):
    """連番 UUID 形式の TutorSessionId を生成する Fake。"""

    def __init__(self, *, prefix: str = "ts", start: int = 1) -> None:
        self._prefix = prefix
        self._next = start

    def next_id(self) -> TutorSessionId:
        value = f"{self._prefix}-{self._next}"
        self._next += 1
        return TutorSessionId(value)


class FakeMessageIdGenerator(MessageIdGenerator):
    """連番 UUID 形式の MessageId を生成する Fake。"""

    def __init__(self, *, prefix: str = "msg", start: int = 1) -> None:
        self._prefix = prefix
        self._next = start

    def next_id(self) -> MessageId:
        value = f"{self._prefix}-{self._next}"
        self._next += 1
        return MessageId(value)
