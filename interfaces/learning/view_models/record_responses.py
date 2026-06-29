# 仕様: docs/spec/interfaces-layer.md#Write-応答-ViewModel
"""Learning Write 成功応答 ViewModel。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecordViewingEventSuccessViewModel:
    """POST /api/viewing-log 成功時の ViewModel。"""

    ok: bool = True


@dataclass(frozen=True)
class RecordQuizAttemptSuccessViewModel:
    """POST /api/quiz-attempts 成功時の ViewModel。"""

    attempt_id: str
    ok: bool = True
