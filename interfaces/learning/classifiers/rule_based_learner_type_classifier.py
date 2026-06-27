# 仕様: docs/spec/interfaces-layer.md#Classifier
"""ルールベース学習者タイプ判定。"""
from __future__ import annotations

from interfaces.learning.services.viewing_behavior_metrics import ViewingBehaviorMetrics

_BACK_CUMULATIVE_TIME_RATIO_INDIFFERENT = 0.18
_FORWARD_OPS_PER_10MIN_ADVANCED = 6
_BACK_OPS_PER_10MIN_ADVANCED = 3
_PAUSE_OPS_PER_10MIN_DILIGENT = 6


class RuleBasedLearnerTypeClassifier:
    """ViewingBehaviorMetrics の派生指標から学習者タイプ code を判定する。"""

    def classify(self, metrics: ViewingBehaviorMetrics) -> str:
        if metrics.back_cumulative_time_ratio >= _BACK_CUMULATIVE_TIME_RATIO_INDIFFERENT:
            return "indifferent"

        if (
            metrics.forward_ops_per_10min >= _FORWARD_OPS_PER_10MIN_ADVANCED
            and metrics.back_ops_per_10min >= _BACK_OPS_PER_10MIN_ADVANCED
        ):
            return "advanced"

        if metrics.pause_ops_per_10min >= _PAUSE_OPS_PER_10MIN_DILIGENT:
            return "diligent"

        return "persistent"
