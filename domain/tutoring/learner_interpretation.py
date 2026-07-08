# 仕様: docs/spec/domain-model.md#Tutoring-VO（LearnerInterpretationResult）
"""Student Model 出力（学習者解釈結果）の Value Object。"""
from __future__ import annotations

from dataclasses import dataclass

from domain.tutoring.interpretation_state import InterpretationStateCard
from domain.tutoring.learner_utterance_type import LearnerUtteranceType


@dataclass(frozen=True)
class LearnerInterpretationResult:
    """Student Model が返す学習者発話の解釈。"""

    utterance_type: LearnerUtteranceType
    state_card: InterpretationStateCard
    evidence_references: tuple[str, ...] = ()
