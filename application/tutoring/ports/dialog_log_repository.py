# 仕様: docs/spec/dialog-log-save.md#tutordb-の表
"""対話ログの永続化 Port。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from application.tutoring.dto.save_dialog_log import DialogLog


class DialogLogRepository(ABC):
    """対話ログを永続化する。1 対話セッションにつき最大 1 件。"""

    @abstractmethod
    def save(self, log: DialogLog) -> None:
        """同じ tutor_session_id があれば置き換え、なければ追加する。失敗時は例外を送出する。"""
