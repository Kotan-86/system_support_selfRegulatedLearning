# 仕様: docs/spec/application-usecase.md#RunTutoringPipeline
"""RunTutoringPipeline の Request / Response / TurnContext DTO。"""
from __future__ import annotations

from dataclasses import dataclass

from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.dialogue_move_decision import DialogueMoveDecision
from domain.tutoring.interpretation_state import InterpretationStateCard
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from domain.tutoring.message import Message, MessageRole


@dataclass(frozen=True)
class TurnContext:
    """1 ターンの対話文脈（Pedagogical Model 入力）。"""

    is_first_assistant_turn: bool
    lecture: Lecture

    @classmethod
    def from_messages(
        cls, messages: tuple[Message, ...], *, lecture: Lecture
    ) -> TurnContext:
        has_assistant = any(message.role is MessageRole.ASSISTANT for message in messages)
        return cls(is_first_assistant_turn=not has_assistant, lecture=lecture)


@dataclass(frozen=True)
class TutoringPipelineRequest:
    """RunTutoringPipeline の入力。"""

    snapshot: LearningSnapshot
    messages: tuple[Message, ...]
    user_message: str
    lecture: Lecture
    previous_state_card: InterpretationStateCard | None = None


@dataclass(frozen=True)
class TutoringPipelineResult:
    """RunTutoringPipeline の出力。"""

    assistant_text: str
    interpretation: LearnerInterpretationResult
    decision: DialogueMoveDecision
