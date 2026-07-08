# 仕様: docs/spec/domain-model.md#Message（対話メッセージ）
# 仕様: docs/spec/domain-model.md#Tutoring-VO
# 仕様: docs/spec/domain-implementation-plan.md Phase 4
"""Tutoring コンテキストの Message Entity と MessageRole VO。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from domain.shared.ids import MessageId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.interpretation_state import InterpretationStateCard
from domain.tutoring.learner_utterance_type import LearnerUtteranceType


class MessageRole(str, Enum):
    """発話者（user / assistant のみ）。"""

    USER = "user"
    ASSISTANT = "assistant"

    @classmethod
    def from_value(cls, value: str) -> MessageRole:
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Invalid MessageRole: {value!r}") from exc


@dataclass(frozen=True)
class Message:
    """user / assistant の 1 発話。"""

    id: MessageId
    role: MessageRole
    content: str
    created_at: datetime

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError("Use Message.create to construct Message")

    @classmethod
    def create(
        cls,
        *,
        id: MessageId,
        role: MessageRole,
        content: str,
        created_at: datetime,
        utterance_type: LearnerUtteranceType | None = None,
        dialogue_move: DialogueMove | None = None,
        interpretation_state: InterpretationStateCard | None = None,
    ) -> Message:
        if not content:
            raise ValueError("Message content must not be empty")

        instance = object.__new__(cls)
        object.__setattr__(instance, "id", id)
        object.__setattr__(instance, "role", role)
        object.__setattr__(instance, "content", content)
        object.__setattr__(instance, "created_at", created_at)
        object.__setattr__(instance, "utterance_type", utterance_type)
        object.__setattr__(instance, "dialogue_move", dialogue_move)
        object.__setattr__(instance, "interpretation_state", interpretation_state)
        return instance
