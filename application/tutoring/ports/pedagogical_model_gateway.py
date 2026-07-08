# 仕様: docs/spec/application-usecase.md#PedagogicalModelGateway
"""ITS Pedagogical Model Port（Dialogue Move 決定）。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from application.tutoring.dto.tutoring_pipeline import TurnContext
from domain.tutoring.dialogue_move_decision import DialogueMoveDecision
from domain.tutoring.learner_interpretation import LearnerInterpretationResult


class PedagogicalModelGateway(ABC):
    """解釈結果とターン文脈から Coach Move を選択する。"""

    @abstractmethod
    def select_move(
        self,
        interpretation: LearnerInterpretationResult,
        *,
        turn_context: TurnContext,
    ) -> DialogueMoveDecision:
        """Stage 2: Dialogue Move と Interface 指示を返す。"""
