# 仕様: docs/spec/interfaces-layer.md#LastUpdatedViewModel
"""最終更新時刻用 ViewModel。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LastUpdatedViewModel:
    """GET /api/last-updated の成功レスポンス契約。"""

    last_updated: datetime | None
