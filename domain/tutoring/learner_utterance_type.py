# 仕様: docs/spec/domain-model.md#Tutoring-VO（LearnerUtteranceType）
"""学習者発話分類の Value Object。"""
from __future__ import annotations

from enum import StrEnum


class LearnerUtteranceType(StrEnum):
    """学習者の 1 発話を分類する 5 種類。"""

    FACT_REQUEST = "FACT_REQUEST"
    RUBRIC_CONFUSION = "RUBRIC_CONFUSION"
    VAGUE_MEMORY = "VAGUE_MEMORY"
    LEARNER_INTERPRETATION = "LEARNER_INTERPRETATION"
    OVERLOAD_OR_RESISTANCE = "OVERLOAD_OR_RESISTANCE"
