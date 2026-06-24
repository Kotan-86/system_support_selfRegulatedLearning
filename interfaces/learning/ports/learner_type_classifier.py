# 仕様: docs/spec/interfaces-layer.md#Classifier（TBD・Stub）
"""学習者タイプ判定 Port。"""
from __future__ import annotations

from typing import Protocol

from interfaces.learning.services.viewing_behavior_metrics import ViewingBehaviorMetrics


class LearnerTypeClassifier(Protocol):
    """視聴行動集計から学習者タイプ code を返す。"""

    def classify(self, metrics: ViewingBehaviorMetrics) -> str | None:
        """判定できなければ None。"""
