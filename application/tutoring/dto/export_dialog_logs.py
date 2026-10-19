# 仕様: docs/spec/research-dialog-download.md#json-の形
"""研究用ダウンロードの DTO。

`ExportResearchData`(application-usecase.md)とは別。対話ログだけを研究者向けに返す。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.tutoring.dto.save_dialog_log import EndMethod
from domain.tutoring.message import Message


@dataclass(frozen=True)
class ResearchDialogLog:
    """1つの対話セッションの研究用ログ。

    `tutor_session_created_at` は UTC のタイムゾーン付き。並び替えにだけ使い、JSON には出さない。
    """

    participant_id: str
    lecture_id: str
    learning_session_id: str
    tutor_session_id: str
    tutor_session_created_at: datetime
    ended_at: datetime | None
    end_method: EndMethod | None
    messages: tuple[Message, ...]


@dataclass(frozen=True)
class ExportDialogLogsRequest:
    """`participant_id` が None なら全参加者。文字列は検証も変換もせず完全一致で照合する。"""

    participant_id: str | None


@dataclass(frozen=True)
class ExportDialogLogsResponse:
    logs: tuple[ResearchDialogLog, ...]
