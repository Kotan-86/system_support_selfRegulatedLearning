# 仕様: docs/spec/domain-model.md#TutorSession（AI 振り返り）
# 仕様: docs/spec/domain-implementation-plan.md Phase 4
"""Tutoring コンテキストの TutorSession 集約ルート。"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from domain.shared.ids import LearningSessionId, MessageId, TutorSessionId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.interpretation_state import InterpretationStateCard
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
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
        utterance_type: LearnerUtteranceType | None = None,
        dialogue_move: DialogueMove | None = None,
        interpretation_state: InterpretationStateCard | None = None,
    ) -> TutorSession:
        message = Message.create(
            id=message_id,
            role=role,
            content=content,
            created_at=created_at,
            utterance_type=utterance_type,
            dialogue_move=dialogue_move,
            interpretation_state=interpretation_state,
        )
        return replace(self, messages=(*self.messages, message))
