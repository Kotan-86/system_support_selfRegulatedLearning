# 仕様: docs/spec/research-lad-csv-download.md#対象と並び順
"""研究用の視聴ログの読み出しポート(読み取り専用)。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from application.learning.dto.export_viewing_logs import ResearchViewingLog


class ViewingLogExportQuery(ABC):
    """視聴ログを研究用に読み出す。

    契約:
    - DB に書かない(SELECT のみ。commit しない)。
    - 学習セッションに対応のない視聴ログは除外する。
    - 並びは問わない(並び替えはユースケースが行う)。
    """

    @abstractmethod
    def list_for_participant(self, participant_id: str) -> tuple[ResearchViewingLog, ...]:
        """`participant_id` と完全一致する学習セッションの視聴ログを返す。"""

    @abstractmethod
    def list_all(self) -> tuple[ResearchViewingLog, ...]:
        """全学習セッションの視聴ログを返す。"""
