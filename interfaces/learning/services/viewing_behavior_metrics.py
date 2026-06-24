# 仕様: docs/spec/interfaces-layer.md#2-分バケット定義（ViewingBehaviorMetrics）
"""視聴イベントから操作集計と 2 分バケットを算出する。"""
from __future__ import annotations

from dataclasses import dataclass

from domain.learning.viewing_event import ViewingAction, ViewingEvent

SEGMENT_WIDTH_SEC = 120

_ACTION_LABELS: dict[ViewingAction, str] = {
    ViewingAction.PLAY: "再生回数",
    ViewingAction.PAUSE: "一時停止回数",
    ViewingAction.FORWARD_SKIP: "早送り回数",
    ViewingAction.BACKWARD_SKIP: "巻き戻し回数",
    ViewingAction.FORWARD_SEEK: "前方シーク回数",
    ViewingAction.BACKWARD_SEEK: "後方シーク回数",
}


def _empty_action_counts() -> dict[str, int]:
    return {action.value: 0 for action in ViewingAction}


def _segment_start_sec(video_position: int) -> int:
    return (video_position // SEGMENT_WIDTH_SEC) * SEGMENT_WIDTH_SEC


@dataclass(frozen=True)
class VideoSegmentMetrics:
    """区間ごとの操作集計（Presenter 変換前の中間表現）。"""

    segment_start_sec: int
    action_counts: dict[str, int]


@dataclass(frozen=True)
class LearningBehaviorMetric:
    """動的学習行動指標（Presenter 変換前の中間表現）。"""

    label: str
    value: int


@dataclass(frozen=True)
class ViewingBehaviorMetrics:
    """viewing_events から算出した視聴行動集計。"""

    action_counts: dict[str, int]
    video_segments: tuple[VideoSegmentMetrics, ...]

    @classmethod
    def from_events(cls, events: tuple[ViewingEvent, ...]) -> ViewingBehaviorMetrics:
        action_counts = _empty_action_counts()
        segment_buckets: dict[int, dict[str, int]] = {}

        for event in events:
            action_key = event.action.value
            action_counts[action_key] = action_counts.get(action_key, 0) + 1

            start = _segment_start_sec(event.video_position)
            bucket = segment_buckets.setdefault(start, _empty_action_counts())
            bucket[action_key] = bucket.get(action_key, 0) + 1

        video_segments = tuple(
            VideoSegmentMetrics(segment_start_sec=start, action_counts=counts)
            for start, counts in sorted(segment_buckets.items())
        )
        return cls(action_counts=action_counts, video_segments=video_segments)

    def learning_behaviors(self) -> tuple[LearningBehaviorMetric, ...]:
        return tuple(
            LearningBehaviorMetric(label=_ACTION_LABELS[action], value=action_counts)
            for action in ViewingAction
            for action_counts in [self.action_counts.get(action.value, 0)]
        )
