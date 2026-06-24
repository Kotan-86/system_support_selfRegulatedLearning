# 仕様: docs/spec/application-usecase.md#DTO
"""Start-or-Get ユースケースの結果種別。"""
from __future__ import annotations

from enum import StrEnum


class StartOrGetOutcome(StrEnum):
    """Session 確保 UC が新規 start したか既存 get したか。"""

    CREATED = "created"
    RETRIEVED = "retrieved"
