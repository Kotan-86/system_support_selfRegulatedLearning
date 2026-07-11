# 仕様: docs/spec/application-usecase.md#PedagogicalModelGateway
"""PedagogicalModelGateway の Fake 実装（テスト用）。"""
from __future__ import annotations

from dataclasses import dataclass

from application.tutoring.dto.tutoring_pipeline import TurnContext
from application.tutoring.ports.pedagogical_model_gateway import PedagogicalModelGateway
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.dialogue_move_decision import DialogueMoveDecision, ResponseBudget
from domain.tutoring.learner_interpretation import LearnerInterpretationResult


@dataclass(frozen=True)
class SelectMoveCall:
    """select_move 呼び出しの記録。"""

    interpretation: LearnerInterpretationResult
    snapshot: LearningSnapshot
    turn_context: TurnContext


class FakePedagogicalModelGateway(PedagogicalModelGateway):
    """固定の DialogueMoveDecision を返す Fake PedagogicalModelGateway。"""

    def __init__(
        self,
        *,
        dialogue_move: DialogueMove = DialogueMove.JOINT_EVIDENCE_CHECK,
        interface_instructions: str = "小テスト問1の選択肢を確認する",
    ) -> None:
        self._dialogue_move = dialogue_move
        self._interface_instructions = interface_instructions
        self.select_move_calls: list[SelectMoveCall] = []

    def select_move(
        self,
        interpretation: LearnerInterpretationResult,
        *,
        snapshot: LearningSnapshot,
        turn_context: TurnContext,
    ) -> DialogueMoveDecision:
        self.select_move_calls.append(
            SelectMoveCall(
                interpretation=interpretation,
                snapshot=snapshot,
                turn_context=turn_context,
            )
        )
        return DialogueMoveDecision(
            dialogue_move=self._dialogue_move,
            response_budget=ResponseBudget(max_sentences=5, max_questions=1),
            interface_instructions=self._interface_instructions,
        )
