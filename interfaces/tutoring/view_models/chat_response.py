# 仕様: docs/spec/interfaces-layer.md#ChatResponseViewModel
"""POST /chat 成功応答 ViewModel。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChatResponseViewModel:
    """POST /chat 成功時の ViewModel。既存 JSON キー response / session_id と互換。"""

    response: str
    session_id: str
