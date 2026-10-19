# 仕様: docs/spec/research-dialog-download.md#json-の形
"""研究用ダウンロードの ViewModel。発言は message_to_json_dict の結果の dict。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResearchDialogLogViewModel:
    format_version: int
    participant_id: str
    lecture_id: str
    learning_session_id: str
    tutor_session_id: str
    ended_at: str | None
    end_method: str | None
    messages: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ResearchDialogLogsViewModel:
    logs: tuple[ResearchDialogLogViewModel, ...]
