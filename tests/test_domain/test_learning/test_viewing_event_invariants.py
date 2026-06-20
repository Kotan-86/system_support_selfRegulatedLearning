# 仕様: docs/spec/domain-model.md#ViewingEvent（視聴イベント）
# 仕様: docs/spec/domain-implementation-plan.md Phase 2
"""
ViewingEvent の action × positionDelta 不変条件マトリクス。

仕様フィールド対応: videoPosition → video_position, positionDelta → position_delta,
occurredAt → occurred_at
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import ViewingEventId

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _create_event(
    *,
    action: ViewingAction,
    position_delta: float,
    video_position: int = 60,
) -> ViewingEvent:
    return ViewingEvent.create(
        id=ViewingEventId("event-1"),
        occurred_at=FIXED_NOW,
        video_position=video_position,
        action=action,
        position_delta=position_delta,
    )


class TestViewingEventPositionDeltaMatrix:
    """action 別 positionDelta 符号ルールを網羅する。"""

    @pytest.mark.parametrize("action", [ViewingAction.PLAY, ViewingAction.PAUSE])
    def test_play_and_pause_require_zero_delta(self, action: ViewingAction) -> None:
        """play / pause は positionDelta == 0 のみ受理する。"""
        event = _create_event(action=action, position_delta=0)
        assert event.position_delta == 0

    @pytest.mark.parametrize("action", [ViewingAction.PLAY, ViewingAction.PAUSE])
    @pytest.mark.parametrize("invalid_delta", [-1.0, 1.0, -0.5, 5.0])
    def test_play_and_pause_reject_non_zero_delta(
        self,
        action: ViewingAction,
        invalid_delta: float,
    ) -> None:
        """play / pause で positionDelta != 0 は拒否される。"""
        with pytest.raises(ValueError):
            _create_event(action=action, position_delta=invalid_delta)

    @pytest.mark.parametrize(
        "action",
        [ViewingAction.FORWARD_SKIP, ViewingAction.FORWARD_SEEK],
    )
    def test_forward_actions_require_positive_delta(self, action: ViewingAction) -> None:
        """forward_skip / forward_seek は positionDelta > 0 を要求する。"""
        event = _create_event(action=action, position_delta=5.0)
        assert event.position_delta == 5.0

    @pytest.mark.parametrize(
        "action",
        [ViewingAction.FORWARD_SKIP, ViewingAction.FORWARD_SEEK],
    )
    def test_forward_actions_allow_zero_delta_at_video_end(
        self,
        action: ViewingAction,
    ) -> None:
        """forward_skip / forward_seek は動画端 edge case で positionDelta == 0 を許容する。"""
        event = _create_event(action=action, position_delta=0)
        assert event.position_delta == 0

    @pytest.mark.parametrize(
        "action",
        [ViewingAction.FORWARD_SKIP, ViewingAction.FORWARD_SEEK],
    )
    @pytest.mark.parametrize("invalid_delta", [-1.0, -0.1])
    def test_forward_actions_reject_negative_delta(
        self,
        action: ViewingAction,
        invalid_delta: float,
    ) -> None:
        """forward_skip / forward_seek で positionDelta < 0 は拒否される。"""
        with pytest.raises(ValueError):
            _create_event(action=action, position_delta=invalid_delta)

    @pytest.mark.parametrize(
        "action",
        [ViewingAction.BACKWARD_SKIP, ViewingAction.BACKWARD_SEEK],
    )
    def test_backward_actions_require_negative_delta(self, action: ViewingAction) -> None:
        """backward_skip / backward_seek は positionDelta < 0 を要求する。"""
        event = _create_event(action=action, position_delta=-5.0)
        assert event.position_delta == -5.0

    @pytest.mark.parametrize(
        "action",
        [ViewingAction.BACKWARD_SKIP, ViewingAction.BACKWARD_SEEK],
    )
    def test_backward_actions_allow_zero_delta_at_video_end(
        self,
        action: ViewingAction,
    ) -> None:
        """backward_skip / backward_seek は動画端 edge case で positionDelta == 0 を許容する。"""
        event = _create_event(action=action, position_delta=0)
        assert event.position_delta == 0

    @pytest.mark.parametrize(
        "action",
        [ViewingAction.BACKWARD_SKIP, ViewingAction.BACKWARD_SEEK],
    )
    @pytest.mark.parametrize("invalid_delta", [1.0, 0.1])
    def test_backward_actions_reject_positive_delta(
        self,
        action: ViewingAction,
        invalid_delta: float,
    ) -> None:
        """backward_skip / backward_seek で positionDelta > 0 は拒否される。"""
        with pytest.raises(ValueError):
            _create_event(action=action, position_delta=invalid_delta)

    def test_backward_skip_with_negative_delta_accepted(self) -> None:
        """backward_skip + positionDelta=-5 が受理される（既存 DB duration マッピングの根拠）。"""
        event = ViewingEvent.create(
            id=ViewingEventId("event-backward"),
            occurred_at=FIXED_NOW,
            video_position=55,
            action=ViewingAction.BACKWARD_SKIP,
            position_delta=-5,
        )
        assert event.action == ViewingAction.BACKWARD_SKIP
        assert event.position_delta == -5
        assert event.video_position == 55


class TestViewingEventVideoPosition:
    """videoPosition の不変条件を検証する。"""

    def test_rejects_negative_video_position(self) -> None:
        """videoPosition < 0 は拒否される。"""
        with pytest.raises(ValueError):
            ViewingEvent.create(
                id=ViewingEventId("event-1"),
                occurred_at=FIXED_NOW,
                video_position=-1,
                action=ViewingAction.PLAY,
                position_delta=0,
            )

    def test_accepts_zero_video_position(self) -> None:
        """videoPosition == 0 は受理される。"""
        event = _create_event(action=ViewingAction.PLAY, position_delta=0, video_position=0)
        assert event.video_position == 0
