# 仕様: docs/spec/research-dialog-download.md#json-の形
"""DialogLogExportQuery の Fake(テスト用)。順序は問わない契約なので、保持した順で返す。"""
from __future__ import annotations

from application.tutoring.dto.export_dialog_logs import ResearchDialogLog
from application.tutoring.ports.dialog_log_export_query import DialogLogExportQuery


class FakeDialogLogExportQuery(DialogLogExportQuery):
    def __init__(self, logs: tuple[ResearchDialogLog, ...] = ()) -> None:
        self._logs = logs
        self.list_for_participant_calls: list[str] = []
        self.list_all_calls = 0

    def list_for_participant(self, participant_id: str) -> tuple[ResearchDialogLog, ...]:
        self.list_for_participant_calls.append(participant_id)
        return tuple(log for log in self._logs if log.participant_id == participant_id)

    def list_all(self) -> tuple[ResearchDialogLog, ...]:
        self.list_all_calls += 1
        return self._logs
