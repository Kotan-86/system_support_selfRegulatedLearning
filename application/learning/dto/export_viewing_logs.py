# 仕様: docs/spec/research-lad-csv-download.md#視聴ログの-csv-の列この順pbi-1
# 仕様: docs/spec/research-lad-csv-download.md#何本目の列round_number共有if2つの-csv-に共通pbi-c決定-multi-video-learningmd-の-q7q-c1q-c42026-11-14
"""研究用の視聴ログ CSV ダウンロードの DTO(生ログ。LAD の集計は使わない)。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchViewingLog:
    """視聴イベント1件。時刻・action は保存された文字列のまま。"""

    participant_id: str
    round_number: int  # 参加者の全学習セッションでの順位(開始時刻の文字列、ID の昇順。1始まり)
    lecture_id: str
    learning_session_id: str
    viewing_log_id: int
    time_stamp: str
    current_time: int
    action: str
    duration: float


@dataclass(frozen=True)
class ExportViewingLogsRequest:
    """`participant_id` が None なら全参加者。文字列は検証も変換もせず完全一致で照合する。"""

    participant_id: str | None


@dataclass(frozen=True)
class ExportViewingLogsResponse:
    logs: tuple[ResearchViewingLog, ...]
