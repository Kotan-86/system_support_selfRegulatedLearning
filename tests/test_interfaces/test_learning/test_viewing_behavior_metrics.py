# 仕様: docs/spec/interfaces-layer.md#ViewingBehaviorMetrics
"""ViewingBehaviorMetrics の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import ViewingEventId
from interfaces.learning.services.viewing_behavior_metrics import ViewingBehaviorMetrics

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
DEFAULT_VIDEO_DURATION_SEC = 600


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


class TestViewingBehaviorMetrics:
    """操作集計と 2 分バケットを検証する。"""

    def test_empty_events_produces_zero_counts_and_no_segments(self) -> None:
        metrics = ViewingBehaviorMetrics.from_events(
            (),
            video_duration_sec=DEFAULT_VIDEO_DURATION_SEC,
        )

        assert metrics.action_counts == {
            "play": 0,
            "pause": 0,
            "forward_skip": 0,
            "backward_skip": 0,
            "forward_seek": 0,
            "backward_seek": 0,
        }
        assert metrics.video_segments == ()
        assert metrics.video_duration_sec == DEFAULT_VIDEO_DURATION_SEC
        assert metrics.back_cumulative_sec == 0
        assert metrics.back_cumulative_time_ratio == 0.0
        assert metrics.forward_ops_per_10min == 0.0
        assert metrics.back_ops_per_10min == 0.0
        assert metrics.pause_ops_per_10min == 0.0

    def test_action_counts_aggregate_all_events(self) -> None:
        events = (
            _event(video_position=10, action=ViewingAction.PLAY, event_id="e1"),
            _event(video_position=20, action=ViewingAction.PLAY, event_id="e2"),
            _event(video_position=30, action=ViewingAction.PAUSE, event_id="e3"),
        )

        metrics = ViewingBehaviorMetrics.from_events(
            events,
            video_duration_sec=DEFAULT_VIDEO_DURATION_SEC,
        )

        assert metrics.action_counts["play"] == 2
        assert metrics.action_counts["pause"] == 1

    def test_video_position_125_maps_to_segment_120(self) -> None:
        events = (_event(video_position=125, action=ViewingAction.PLAY),)

        metrics = ViewingBehaviorMetrics.from_events(
            events,
            video_duration_sec=DEFAULT_VIDEO_DURATION_SEC,
        )

        assert len(metrics.video_segments) == 1
        assert metrics.video_segments[0].segment_start_sec == 120
        assert metrics.video_segments[0].action_counts["play"] == 1

    def test_video_position_0_maps_to_segment_0(self) -> None:
        events = (_event(video_position=0, action=ViewingAction.PAUSE),)

        metrics = ViewingBehaviorMetrics.from_events(
            events,
            video_duration_sec=DEFAULT_VIDEO_DURATION_SEC,
        )

        assert metrics.video_segments[0].segment_start_sec == 0

    def test_events_in_different_buckets_create_multiple_segments(self) -> None:
        events = (
            _event(video_position=30, action=ViewingAction.PLAY, event_id="e1"),
            _event(video_position=150, action=ViewingAction.PAUSE, event_id="e2"),
        )

        metrics = ViewingBehaviorMetrics.from_events(
            events,
            video_duration_sec=DEFAULT_VIDEO_DURATION_SEC,
        )

        assert [segment.segment_start_sec for segment in metrics.video_segments] == [
            0,
            120,
        ]
        assert metrics.video_segments[0].action_counts["play"] == 1
        assert metrics.video_segments[1].action_counts["pause"] == 1

    def test_learning_behaviors_include_all_actions_with_values(self) -> None:
        events = (_event(video_position=10, action=ViewingAction.FORWARD_SKIP),)

        metrics = ViewingBehaviorMetrics.from_events(
            events,
            video_duration_sec=DEFAULT_VIDEO_DURATION_SEC,
        )
        behaviors = metrics.learning_behaviors()

        assert len(behaviors) == 6
        labels = [behavior.label for behavior in behaviors]
        assert "早送り回数" in labels
        forward_skip = next(
            behavior for behavior in behaviors if behavior.label == "早送り回数"
        )
        assert forward_skip.value == 1


class TestViewingBehaviorMetricsDerived:
    """派生指標（Classifier 入力）を検証する。"""

    def test_back_cumulative_sec_sums_abs_position_delta(self) -> None:
        events = (
            _event(
                video_position=100,
                action=ViewingAction.BACKWARD_SKIP,
                position_delta=-30,
                event_id="e1",
            ),
            _event(
                video_position=200,
                action=ViewingAction.BACKWARD_SEEK,
                position_delta=-20,
                event_id="e2",
            ),
        )

        metrics = ViewingBehaviorMetrics.from_events(events, video_duration_sec=200)

        assert metrics.back_cumulative_sec == 50
        assert metrics.back_cumulative_time_ratio == pytest.approx(0.25)

    def test_pause_ops_per_10min_scales_short_videos(self) -> None:
        events = (
            _event(video_position=10, action=ViewingAction.PAUSE, event_id="e1"),
            _event(video_position=20, action=ViewingAction.PAUSE, event_id="e2"),
            _event(video_position=30, action=ViewingAction.PAUSE, event_id="e3"),
        )

        metrics = ViewingBehaviorMetrics.from_events(events, video_duration_sec=300)

        assert metrics.pause_ops_per_10min == 6.0

    def test_backward_event_with_zero_position_delta_counts_op_not_seconds(self) -> None:
        events = (
            _event(
                video_position=50,
                action=ViewingAction.BACKWARD_SEEK,
                position_delta=0,
                event_id="e1",
            ),
        )

        metrics = ViewingBehaviorMetrics.from_events(events, video_duration_sec=600)

        assert metrics.action_counts["backward_seek"] == 1
        assert metrics.back_cumulative_sec == 0
        assert metrics.back_cumulative_time_ratio == 0.0
        assert metrics.back_ops_per_10min == 1.0

    def test_video_duration_sec_zero_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="video_duration_sec must be > 0"):
            ViewingBehaviorMetrics.from_events((), video_duration_sec=0)

    def test_video_duration_sec_negative_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="video_duration_sec must be > 0"):
            ViewingBehaviorMetrics.from_events((), video_duration_sec=-1)
