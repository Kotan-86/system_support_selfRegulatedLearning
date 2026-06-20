# 仕様: docs/spec/domain-model.md#ViewingEvent（視聴イベント）
# 仕様: docs/spec/domain-implementation-plan.md Phase 1
"""Learning コンテキストの視聴関連 Value Object。"""
from __future__ import annotations

from enum import Enum


class ViewingAction(str, Enum):
    """視聴操作の種別（仕様上の camelCase: videoPosition, positionDelta 等は Phase 2 で Entity 化）。"""

    PLAY = "play"
    PAUSE = "pause"
    FORWARD_SKIP = "forward_skip"
    BACKWARD_SKIP = "backward_skip"
    FORWARD_SEEK = "forward_seek"
    BACKWARD_SEEK = "backward_seek"
