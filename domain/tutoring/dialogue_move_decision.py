# 仕様: docs/spec/domain-model.md#Tutoring-VO（DialogueMoveDecision）
"""Pedagogical Model 出力（Dialogue Move 決定）の Value Object。"""
from __future__ import annotations

from dataclasses import dataclass

from domain.tutoring.dialogue_move import DialogueMove


@dataclass(frozen=True)
class ResponseBudget:
    """Interface Model への応答制約。"""

    max_sentences: int
    max_questions: int


@dataclass(frozen=True)
class DialogueMoveDecision:
    """1 ターンで選択された Coach Move と Interface への指示。"""

    dialogue_move: DialogueMove
    response_budget: ResponseBudget
    interface_instructions: str
    evidence_to_surface: tuple[str, ...] = ()
