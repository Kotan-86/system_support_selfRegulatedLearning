# 仕様: docs/spec/bugs/lad-video-segments-over-10min.md#修正方針
"""LAD 応答用に、疎な区間集計を 0 秒からの欠けのない全区間(密)へ補完する。"""
from __future__ import annotations

from domain.learning.viewing_event import ViewingAction

from interfaces.learning.services.viewing_behavior_metrics import (
    SEGMENT_WIDTH_SEC,
    VideoSegmentMetrics,
)
from interfaces.learning.view_models.lad_dashboard import VideoSegmentViewModel

# 最低 5 区間(0〜600 秒)を保つための、最後の区間の開始秒の下限。
MIN_LAST_SEGMENT_START_SEC = 480


def last_segment_start_sec(
    *, video_duration_sec: int, max_segment_start_sec: int | None
) -> int:
    """最後の区間の開始秒を返す(仕様「修正方針」の式)。"""
    if video_duration_sec <= 0:
        raise ValueError("video_duration_sec must be > 0")
    covering_duration = (
        -(-video_duration_sec // SEGMENT_WIDTH_SEC) * SEGMENT_WIDTH_SEC
        - SEGMENT_WIDTH_SEC
    )
    candidates = [MIN_LAST_SEGMENT_START_SEC, covering_duration]
    if max_segment_start_sec is not None:
        candidates.append(max_segment_start_sec)
    return max(candidates)


def build_dense_video_segments(
    video_segments: tuple[VideoSegmentMetrics, ...],
    *,
    video_duration_sec: int,
) -> tuple[VideoSegmentViewModel, ...]:
    """疎な区間集計から、0 から最後の区間までの全区間を開始秒の昇順で作る。"""
    by_start = {segment.segment_start_sec: segment for segment in video_segments}
    last_start = last_segment_start_sec(
        video_duration_sec=video_duration_sec,
        max_segment_start_sec=max(by_start) if by_start else None,
    )
    result: list[VideoSegmentViewModel] = []
    for start in range(0, last_start + 1, SEGMENT_WIDTH_SEC):
        existing = by_start.get(start)
        if existing is not None:
            counts = dict(existing.action_counts)
        else:
            counts = {action.value: 0 for action in ViewingAction}
        result.append(VideoSegmentViewModel(segment_start_sec=start, action_counts=counts))
    return tuple(result)
