# 仕様: docs/spec/interfaces-layer.md#Classifier
"""RuleBasedLearnerTypeClassifier の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import ViewingEventId
from interfaces.learning.classifiers.rule_based_learner_type_classifier import (
    RuleBasedLearnerTypeClassifier,
)
from interfaces.learning.services.viewing_behavior_metrics import ViewingBehaviorMetrics

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
VIDEO_DURATION_SEC = 600


def _event(
    *,
    video_position: int,
    action: ViewingAction,
    position_delta: int = 0,
    event_id: str = "event-1",
) -> ViewingEvent:
    return ViewingEvent.create(
        id=ViewingEventId(event_id),
        occurred_at=FIXED_NOW,
        video_position=video_position,
        action=action,
        position_delta=position_delta,
    )


def _metrics(
    *,
    back_cumulative_time_ratio: float = 0.0,
    forward_ops_per_10min: float = 0.0,
    back_ops_per_10min: float = 0.0,
    pause_ops_per_10min: float = 0.0,
    video_duration_sec: int = VIDEO_DURATION_SEC,
) -> ViewingBehaviorMetrics:
    back_cumulative_sec = int(back_cumulative_time_ratio * video_duration_sec)
    return ViewingBehaviorMetrics(
        action_counts={
            "play": 0,
            "pause": 0,
            "forward_skip": 0,
            "backward_skip": 0,
            "forward_seek": 0,
            "backward_seek": 0,
        },
        video_segments=(),
        video_duration_sec=video_duration_sec,
        back_cumulative_sec=back_cumulative_sec,
        back_cumulative_time_ratio=back_cumulative_time_ratio,
        forward_ops_per_10min=forward_ops_per_10min,
        back_ops_per_10min=back_ops_per_10min,
        pause_ops_per_10min=pause_ops_per_10min,
    )


class TestRuleBasedLearnerTypeClassifier:
    """4 タイプ判定ルール（優先順・排他）を検証する。"""

    def setup_method(self) -> None:
        self.classifier = RuleBasedLearnerTypeClassifier()

    def test_empty_events_classifies_as_persistent(self) -> None:
        metrics = ViewingBehaviorMetrics.from_events((), video_duration_sec=VIDEO_DURATION_SEC)

        assert self.classifier.classify(metrics) == "persistent"

    def test_indifferent_when_back_cumulative_ratio_high(self) -> None:
        events = (
            _event(
                video_position=100,
                action=ViewingAction.BACKWARD_SKIP,
                position_delta=-120,
                event_id="e1",
            ),
        )
        metrics = ViewingBehaviorMetrics.from_events(events, video_duration_sec=VIDEO_DURATION_SEC)

        assert metrics.back_cumulative_time_ratio == pytest.approx(0.2)
        assert self.classifier.classify(metrics) == "indifferent"

    def test_advanced_when_forward_and_back_ops_meet_thresholds(self) -> None:
        events = tuple(
            _event(
                video_position=10 * index,
                action=ViewingAction.FORWARD_SKIP,
                event_id=f"fwd-{index}",
            )
            for index in range(6)
        ) + tuple(
            _event(
                video_position=100 + 10 * index,
                action=ViewingAction.BACKWARD_SKIP,
                position_delta=-10,
                event_id=f"back-{index}",
            )
            for index in range(3)
        )
        metrics = ViewingBehaviorMetrics.from_events(events, video_duration_sec=VIDEO_DURATION_SEC)

        assert metrics.forward_ops_per_10min == pytest.approx(6.0)
        assert metrics.back_ops_per_10min == pytest.approx(3.0)
        assert metrics.back_cumulative_time_ratio == pytest.approx(0.05)
        assert self.classifier.classify(metrics) == "advanced"

    def test_diligent_when_pause_ops_high_without_indifferent_or_advanced(self) -> None:
        events = tuple(
            _event(
                video_position=10 * index,
                action=ViewingAction.PAUSE,
                event_id=f"pause-{index}",
            )
            for index in range(6)
        )
        metrics = ViewingBehaviorMetrics.from_events(events, video_duration_sec=VIDEO_DURATION_SEC)

        assert metrics.pause_ops_per_10min == pytest.approx(6.0)
        assert self.classifier.classify(metrics) == "diligent"

    def test_persistent_when_no_rule_matches(self) -> None:
        events = (
            _event(video_position=10, action=ViewingAction.PLAY, event_id="e1"),
            _event(video_position=20, action=ViewingAction.PAUSE, event_id="e2"),
        )
        metrics = ViewingBehaviorMetrics.from_events(events, video_duration_sec=VIDEO_DURATION_SEC)

        assert self.classifier.classify(metrics) == "persistent"


class TestRuleBasedLearnerTypeClassifierBoundaries:
    """閾値境界（0.18 / 6 / 3）を検証する。"""

    def setup_method(self) -> None:
        self.classifier = RuleBasedLearnerTypeClassifier()

    def test_ratio_exactly_0_18_is_indifferent(self) -> None:
        metrics = _metrics(back_cumulative_time_ratio=0.18)

        assert self.classifier.classify(metrics) == "indifferent"

    def test_ratio_just_below_0_18_is_not_indifferent(self) -> None:
        metrics = _metrics(back_cumulative_time_ratio=0.179)

        assert self.classifier.classify(metrics) == "persistent"

    def test_indifferent_takes_priority_over_advanced(self) -> None:
        metrics = _metrics(
            back_cumulative_time_ratio=0.18,
            forward_ops_per_10min=6.0,
            back_ops_per_10min=3.0,
        )

        assert self.classifier.classify(metrics) == "indifferent"

    def test_forward_ops_exactly_6_and_back_ops_exactly_3_is_advanced(self) -> None:
        metrics = _metrics(
            back_cumulative_time_ratio=0.17,
            forward_ops_per_10min=6.0,
            back_ops_per_10min=3.0,
        )

        assert self.classifier.classify(metrics) == "advanced"

    def test_forward_ops_just_below_6_is_not_advanced(self) -> None:
        metrics = _metrics(
            back_cumulative_time_ratio=0.0,
            forward_ops_per_10min=5.999,
            back_ops_per_10min=3.0,
        )

        assert self.classifier.classify(metrics) == "persistent"

    def test_back_ops_just_below_3_is_not_advanced(self) -> None:
        metrics = _metrics(
            back_cumulative_time_ratio=0.0,
            forward_ops_per_10min=6.0,
            back_ops_per_10min=2.999,
        )

        assert self.classifier.classify(metrics) == "persistent"

    def test_pause_ops_exactly_6_is_diligent(self) -> None:
        metrics = _metrics(pause_ops_per_10min=6.0)

        assert self.classifier.classify(metrics) == "diligent"

    def test_pause_ops_just_below_6_is_persistent(self) -> None:
        metrics = _metrics(pause_ops_per_10min=5.999)

        assert self.classifier.classify(metrics) == "persistent"
