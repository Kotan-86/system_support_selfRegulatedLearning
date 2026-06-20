# 仕様: docs/spec/domain-model.md#TutorSession（AI 振り返り）
# 仕様: docs/spec/domain-implementation-plan.md Phase 4
"""Tutoring コンテキストの TutorSession 集約ルート。"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from domain.shared.ids import LearningSessionId, MessageId, TutorSessionId
from domain.tutoring.message import Message, MessageRole


@dataclass(frozen=True)
class TutorSession:
    """1 LearningSession に紐づく AI 振り返り対話（集約ルート）。"""

    id: TutorSessionId
    learning_session_id: LearningSessionId
    started_at: datetime
    messages: tuple[Message, ...] = ()

    @classmethod
    def start(
        cls,
        *,
        id: TutorSessionId,
        learning_session_id: LearningSessionId,
        started_at: datetime,
    ) -> TutorSession:
        return cls(
            id=id,
            learning_session_id=learning_session_id,
            started_at=started_at,
        )

    def append_message(
        self,
        *,
        message_id: MessageId,
        role: MessageRole,
        content: str,
        created_at: datetime,
    ) -> TutorSession:
        message = Message.create(
            id=message_id,
            role=role,
            content=content,
            created_at=created_at,
        )
        return replace(self, messages=(*self.messages, message))
