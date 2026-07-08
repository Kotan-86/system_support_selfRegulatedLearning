# 仕様: docs/spec/domain-model.md#Tutoring-VO（InterpretationStateCard）
"""学習者解釈状態（Interpretation State Card）の Value Object。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class InterpretationFieldStatus(StrEnum):
    """State Card 各軸の確信度。"""

    CONFIRMED = "confirmed"
    HYPOTHESIZED = "hypothesized"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InterpretationField:
    """State Card の 1 軸（status + note）。"""

    status: InterpretationFieldStatus
    note: str = ""

    @classmethod
    def unknown(cls, *, note: str = "") -> InterpretationField:
        return cls(status=InterpretationFieldStatus.UNKNOWN, note=note)


_STATE_CARD_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "task_understanding",
        "answer_rationale",
        "felt_dissonance",
        "domain_connection",
        "process_memory",
        "lad_connection",
        "ai_hypotheses",
        "learner_load",
    }
)


@dataclass(frozen=True)
class InterpretationStateCard:
    """8 軸の学習者解釈状態カード。"""

    task_understanding: InterpretationField
    answer_rationale: InterpretationField
    felt_dissonance: InterpretationField
    domain_connection: InterpretationField
    process_memory: InterpretationField
    lad_connection: InterpretationField
    ai_hypotheses: InterpretationField
    learner_load: InterpretationField

    @classmethod
    def empty(cls) -> InterpretationStateCard:
        """全軸を unknown で初期化する。"""
        unknown = InterpretationField.unknown()
        return cls(
            task_understanding=unknown,
            answer_rationale=unknown,
            felt_dissonance=unknown,
            domain_connection=unknown,
            process_memory=unknown,
            lad_connection=unknown,
            ai_hypotheses=unknown,
            learner_load=unknown,
        )

    @property
    def field_names(self) -> frozenset[str]:
        return _STATE_CARD_FIELD_NAMES
