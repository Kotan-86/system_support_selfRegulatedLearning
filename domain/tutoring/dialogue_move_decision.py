# 仕様: docs/spec/domain-model.md#Tutoring-VO（DialogueMoveDecision）
"""Pedagogical Model 出力（Dialogue Move 決定）の Value Object。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from domain.tutoring.dialogue_move import DialogueMove


class ScaffoldingLevel(StrEnum):
    """Interface Model への足場かけの強度。"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class ResponseBudget:
    """Interface Model への応答制約。"""

    max_sentences: int
    max_questions: int
    scaffolding_level: ScaffoldingLevel = ScaffoldingLevel.HIGH
    allow_composite_turn: bool = False
    composite_pattern: str | None = None

    def __post_init__(self) -> None:
        if self.max_sentences < 1:
            raise ValueError("max_sentences must be a positive integer")
        if self.max_questions < 0:
            raise ValueError("max_questions must be zero or a positive integer")


@dataclass(frozen=True)
class DialogueMoveDecision:
    """1 ターンで選択された Coach Move と Interface への指示。"""

    dialogue_move: DialogueMove
    response_budget: ResponseBudget
    interface_instructions: str
    evidence_to_surface: tuple[str, ...] = ()
