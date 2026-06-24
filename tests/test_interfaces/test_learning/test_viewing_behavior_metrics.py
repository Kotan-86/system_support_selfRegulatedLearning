# 仕様: docs/spec/interfaces-layer.md#2-分バケット定義（ViewingBehaviorMetrics）
"""ViewingBehaviorMetrics の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import ViewingEventId
from interfaces.learning.services.viewing_behavior_metrics import ViewingBehaviorMetrics

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _event(*, video_position: int, action: ViewingAction) -> ViewingEvent:
    return ViewingEvent.create(
        id=ViewingEventId("event-1"),
        occurred_at=FIXED_NOW,
        video_position=video_position,
        action=action,
        position_delta=0,
    )


class TestViewingBehaviorMetrics:
    """操作集計と 2 分バケットを検証する。"""

    def test_empty_events_produces_zero_counts_and_no_segments(self) -> None:
        metrics = ViewingBehaviorMetrics.from_events(())

        assert metrics.action_counts == {
            "play": 0,
            "pause": 0,
            "forward_skip": 0,
            "backward_skip": 0,
            "forward_seek": 0,
            "backward_seek": 0,
        }
        assert metrics.video_segments == ()

    def test_action_counts_aggregate_all_events(self) -> None:
        events = (
            _event(video_position=10, action=ViewingAction.PLAY),
            _event(video_position=20, action=ViewingAction.PLAY),
            _event(video_position=30, action=ViewingAction.PAUSE),
        )

        metrics = ViewingBehaviorMetrics.from_events(events)

        assert metrics.action_counts["play"] == 2
        assert metrics.action_counts["pause"] == 1

    def test_video_position_125_maps_to_segment_120(self) -> None:
        events = (_event(video_position=125, action=ViewingAction.PLAY),)

        metrics = ViewingBehaviorMetrics.from_events(events)

        assert len(metrics.video_segments) == 1
        assert metrics.video_segments[0].segment_start_sec == 120
        assert metrics.video_segments[0].action_counts["play"] == 1

    def test_video_position_0_maps_to_segment_0(self) -> None:
        events = (_event(video_position=0, action=ViewingAction.PAUSE),)

        metrics = ViewingBehaviorMetrics.from_events(events)

        assert metrics.video_segments[0].segment_start_sec == 0

    def test_events_in_different_buckets_create_multiple_segments(self) -> None:
        events = (
            _event(video_position=30, action=ViewingAction.PLAY),
            _event(video_position=150, action=ViewingAction.PAUSE),
        )

        metrics = ViewingBehaviorMetrics.from_events(events)

        assert [segment.segment_start_sec for segment in metrics.video_segments] == [
            0,
            120,
        ]
        assert metrics.video_segments[0].action_counts["play"] == 1
        assert metrics.video_segments[1].action_counts["pause"] == 1

    def test_learning_behaviors_include_all_actions_with_values(self) -> None:
        events = (_event(video_position=10, action=ViewingAction.FORWARD_SKIP),)

        metrics = ViewingBehaviorMetrics.from_events(events)
        behaviors = metrics.learning_behaviors()

        assert len(behaviors) == 6
        labels = [behavior.label for behavior in behaviors]
        assert "早送り回数" in labels
        forward_skip = next(
            behavior for behavior in behaviors if behavior.label == "早送り回数"
        )
        assert forward_skip.value == 1
