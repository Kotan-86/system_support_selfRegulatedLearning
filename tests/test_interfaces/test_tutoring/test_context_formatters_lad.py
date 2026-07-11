# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
# 仕様: docs/spec/interfaces-layer.md#ViewingBehaviorMetrics
"""LAD 要約フォーマッタの単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from domain.learning.learning_snapshot import LearningSnapshot
from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import (
    LearnerId,
    LearningSessionId,
    LectureId,
    ViewingEventId,
)
from interfaces.tutoring.context_formatters import (
    EMPTY_PLACEHOLDER,
    format_evidence_list,
    format_lad_digest,
    format_lad_timeline,
)
from tests.test_application.test_learning.test_get_learning_snapshot import _lecture

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


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


def _snapshot(*events: ViewingEvent) -> LearningSnapshot:
    return LearningSnapshot(
        session_id=LearningSessionId("session-1"),
        learner_id=LearnerId("learner-1"),
        lecture_id=LectureId("lecture-1"),
        viewing_events=events,
        latest_quiz_attempt=None,
        quiz_answers=(),
    )


class TestFormatLadTimeline:
    """format_lad_timeline の整形。"""

    def test_empty_events_returns_placeholder(self) -> None:
        assert format_lad_timeline(_snapshot()) == EMPTY_PLACEHOLDER

    def test_play_and_pause_use_readable_labels(self) -> None:
        text = format_lad_timeline(
            _snapshot(
                _event(video_position=0, action=ViewingAction.PLAY, event_id="e1"),
                _event(video_position=310, action=ViewingAction.PAUSE, event_id="e2"),
            )
        )

        assert "- 00:00 再生開始" in text
        assert "- 05:10 一時停止" in text

    def test_forward_skip_includes_delta_and_target(self) -> None:
        text = format_lad_timeline(
            _snapshot(
                _event(
                    video_position=90,
                    action=ViewingAction.FORWARD_SKIP,
                    position_delta=30,
                ),
            )
        )

        assert "- 01:30 早送り（+30秒 → 02:00）" in text


class TestFormatLadDigest:
    """format_lad_digest の集計サマリとタイムライン。"""

    def test_empty_events_returns_placeholder(self) -> None:
        lecture = _lecture()
        assert format_lad_digest(_snapshot(), lecture) == EMPTY_PLACEHOLDER

    def test_includes_action_summary_and_busy_segments(self) -> None:
        text = format_lad_digest(
            _snapshot(
                _event(
                    video_position=10,
                    action=ViewingAction.FORWARD_SKIP,
                    position_delta=20,
                    event_id="e1",
                ),
                _event(
                    video_position=20,
                    action=ViewingAction.PAUSE,
                    event_id="e2",
                ),
                _event(
                    video_position=150,
                    action=ViewingAction.BACKWARD_SKIP,
                    position_delta=-30,
                    event_id="e3",
                ),
            ),
            _lecture(),
        )

        assert "## 視聴ログ要約" in text
        assert "早送り: 1回" in text
        assert "巻き戻し: 1回" in text
        assert "一時停止: 1回" in text
        assert "操作が多い区間:" in text
        assert "## 操作タイムライン（直近10件）" in text
        assert "早送り（+20秒" in text

    def test_recent_timeline_is_limited_to_last_ten_events(self) -> None:
        events = tuple(
            _event(
                video_position=index,
                action=ViewingAction.PLAY,
                event_id=f"e{index}",
            )
            for index in range(12)
        )
        text = format_lad_digest(_snapshot(*events), _lecture())

        assert text.count("再生開始") == 10
        assert "- 00:00 再生開始" not in text
        assert "- 00:02 再生開始" in text


class TestFormatEvidenceList:
    """format_evidence_list の整形。"""

    def test_empty_returns_placeholder(self) -> None:
        assert format_evidence_list(()) == EMPTY_PLACEHOLDER

    def test_joins_items_with_comma(self) -> None:
        assert format_evidence_list(
            ("lad_log_segment_00:00-02:00", "quiz_q2_choices")
        ) == "lad_log_segment_00:00-02:00, quiz_q2_choices"
