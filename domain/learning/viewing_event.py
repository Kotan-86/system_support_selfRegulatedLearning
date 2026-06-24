# 仕様: docs/spec/domain-model.md#ViewingEvent（視聴イベント）
# 仕様: docs/spec/domain-implementation-plan.md Phase 1, Phase 2
"""Learning コンテキストの視聴関連 Value Object と Entity。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from domain.shared.ids import ViewingEventId


class ViewingAction(str, Enum):
    """視聴操作の種別。"""

    PLAY = "play"
    PAUSE = "pause"
    FORWARD_SKIP = "forward_skip"
    BACKWARD_SKIP = "backward_skip"
    FORWARD_SEEK = "forward_seek"
    BACKWARD_SEEK = "backward_seek"


def _validate_position_delta(action: ViewingAction, position_delta: int) -> None:
    if action in (ViewingAction.PLAY, ViewingAction.PAUSE):
        if position_delta != 0:
            raise ValueError(
                f"position_delta must be 0 for {action.value}, got {position_delta}"
            )
        return

    if action in (ViewingAction.FORWARD_SKIP, ViewingAction.FORWARD_SEEK):
        if position_delta < 0:
            raise ValueError(
                f"position_delta must be >= 0 for {action.value}, got {position_delta}"
            )
        return

    if action in (ViewingAction.BACKWARD_SKIP, ViewingAction.BACKWARD_SEEK):
        if position_delta > 0:
            raise ValueError(
                f"position_delta must be <= 0 for {action.value}, got {position_delta}"
            )


@dataclass(frozen=True)
class ViewingEvent:
    """視聴イベント 1 回分。"""

    id: ViewingEventId
    occurred_at: datetime
    video_position: int
    action: ViewingAction
    position_delta: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError("Use ViewingEvent.create to construct ViewingEvent")

    @classmethod
    def create(
        cls,
        *,
        id: ViewingEventId,
        occurred_at: datetime,
        video_position: int,
        action: ViewingAction,
        position_delta: int,
    ) -> ViewingEvent:
        if video_position < 0:
            raise ValueError("video_position must be >= 0")
        _validate_position_delta(action, position_delta)

        instance = object.__new__(cls)
        object.__setattr__(instance, "id", id)
        object.__setattr__(instance, "occurred_at", occurred_at)
        object.__setattr__(instance, "video_position", video_position)
        object.__setattr__(instance, "action", action)
        object.__setattr__(instance, "position_delta", position_delta)
        return instance
