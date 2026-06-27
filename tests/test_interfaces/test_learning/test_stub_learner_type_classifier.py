# 仕様: docs/spec/interfaces-layer.md#Classifier（TBD・Stub）
"""StubLearnerTypeClassifier の単体テスト。"""
from __future__ import annotations

from interfaces.learning.classifiers.stub_learner_type_classifier import (
    StubLearnerTypeClassifier,
)
from interfaces.learning.services.viewing_behavior_metrics import ViewingBehaviorMetrics


class TestStubLearnerTypeClassifier:
    """Stub の振る舞いを検証する。"""

    def test_default_returns_none(self) -> None:
        classifier = StubLearnerTypeClassifier()
        metrics = ViewingBehaviorMetrics.from_events((), video_duration_sec=600)

        assert classifier.classify(metrics) is None

    def test_fixed_type_code_returns_configured_value(self) -> None:
        classifier = StubLearnerTypeClassifier(fixed_type_code="diligent")
        metrics = ViewingBehaviorMetrics.from_events((), video_duration_sec=600)

        assert classifier.classify(metrics) == "diligent"
