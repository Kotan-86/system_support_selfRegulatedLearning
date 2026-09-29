# 仕様: docs/spec/dialog-log-save.md#保存-API
"""POST /api/dialog-log 成功応答 ViewModel。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DialogLogSavedViewModel:
    tutor_session_id: str
    ended_at: str
    end_method: str
