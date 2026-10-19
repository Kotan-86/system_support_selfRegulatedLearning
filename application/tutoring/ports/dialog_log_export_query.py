# 仕様: docs/spec/research-dialog-download.md#json-の形
"""研究用の対話ログの読み出しポート(読み取り専用)。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from application.tutoring.dto.export_dialog_logs import ResearchDialogLog


class DialogLogExportQuery(ABC):
    """対話ログを研究用に読み出す。

    契約:
    - 各 `messages` は受け付けた時刻の昇順、同じなら保存された順(`messages.id` の昇順)。
    - `tutor_session_created_at` は UTC のタイムゾーン付き(DB の値にタイムゾーンがなければ UTC とみなす)。
    - DB に書かない(SELECT のみ。commit しない)。
    - 対話セッションの順序は問わない(並び替えはユースケースが行う)。
    """

    @abstractmethod
    def list_for_participant(self, participant_id: str) -> tuple[ResearchDialogLog, ...]:
        """`participant_id` と完全一致する対話セッションだけを返す。"""

    @abstractmethod
    def list_all(self) -> tuple[ResearchDialogLog, ...]:
        """学習セッションに対応のある全対話セッションを返す。

        学習セッションに対応のない対話セッションは除外する(D-25-T2-001)。
        """
