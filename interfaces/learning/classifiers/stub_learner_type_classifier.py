# 仕様: docs/spec/interfaces-layer.md#Classifier（TBD・Stub）
"""学習者タイプ判定の Stub 実装。"""
from __future__ import annotations

from interfaces.learning.services.viewing_behavior_metrics import ViewingBehaviorMetrics


class StubLearnerTypeClassifier:
    """本番ルール未確定のため、常に None またはテスト用固定値を返す。"""

    def __init__(self, *, fixed_type_code: str | None = None) -> None:
        self._fixed_type_code = fixed_type_code

    def classify(self, metrics: ViewingBehaviorMetrics) -> str | None:
        return self._fixed_type_code
