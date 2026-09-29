# 仕様: docs/spec/dialog-log-save.md#tutordb-の表
"""DialogLogRepository の InMemory 実装(テスト用)。"""
from __future__ import annotations

from application.tutoring.dto.save_dialog_log import DialogLog
from application.tutoring.ports.dialog_log_repository import DialogLogRepository


class InMemoryDialogLogRepository(DialogLogRepository):
    """tutor_session_id をキーに、置き換えで保存する InMemory 実装。"""

    def __init__(self) -> None:
        self.logs: dict[str, DialogLog] = {}
        self.save_count = 0

    def save(self, log: DialogLog) -> None:
        self.logs[log.tutor_session_id] = log
        self.save_count += 1
