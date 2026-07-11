# 仕様: docs/spec/application-usecase.md#RunTutoringPipeline
"""RunTutoringPipeline の Request / Response / TurnContext DTO。"""
from __future__ import annotations

from dataclasses import dataclass

from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.dialogue_move_decision import DialogueMoveDecision
from domain.tutoring.dialogue_move_history import DialogueMoveHistory
from domain.tutoring.interpretation_state import InterpretationStateCard
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from domain.tutoring.message import Message, MessageRole


@dataclass(frozen=True)
class TurnContext:
    """1 ターンの対話文脈（Pedagogical Model 入力）。"""

    is_first_assistant_turn: bool
    lecture: Lecture
    turn_index: int
    move_history: DialogueMoveHistory
    has_lad_data: bool
    lad_check_pending: bool

    @classmethod
    def from_messages(
        cls,
        messages: tuple[Message, ...],
        *,
        lecture: Lecture,
        snapshot: LearningSnapshot,
    ) -> TurnContext:
        # 仕様: docs/spec/domain-model.md#TurnContext（LAD 可用性フラグ）
        assistant_count = sum(
            1 for message in messages if message.role is MessageRole.ASSISTANT
        )
        has_lad_data = bool(snapshot.viewing_events)
        has_data_check = any(
            message.role is MessageRole.ASSISTANT
            and message.dialogue_move is DialogueMove.DATA_CHECK
            for message in messages
        )
        return cls(
            is_first_assistant_turn=assistant_count == 0,
            lecture=lecture,
            turn_index=assistant_count,
            move_history=DialogueMoveHistory.from_messages(messages),
            has_lad_data=has_lad_data,
            lad_check_pending=has_lad_data and not has_data_check,
        )


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
