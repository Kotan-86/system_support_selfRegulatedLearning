# 仕様: docs/spec/research-dialog-download.md#json-の形
"""研究用ダウンロードのユースケース。

`ExportResearchData`(application-usecase.md)とは別。対話ログだけを研究者向けに返す。
"""
from __future__ import annotations

from application.common.errors import AppError
from application.common.result import Result, ok
from application.tutoring.dto.export_dialog_logs import (
    ExportDialogLogsRequest,
    ExportDialogLogsResponse,
)
from application.tutoring.ports.dialog_log_export_query import DialogLogExportQuery


class ExportDialogLogsUseCase:
    """対話ログを取得し、participant_id(文字列の昇順) → 作成時刻 → tutor_session_id の順に並べる。"""

    def __init__(self, query: DialogLogExportQuery) -> None:
        self._query = query

    def execute(
        self, request: ExportDialogLogsRequest
    ) -> Result[ExportDialogLogsResponse, AppError]:
        if request.participant_id is None:
            logs = self._query.list_all()
        else:
            logs = self._query.list_for_participant(request.participant_id)
        ordered = sorted(
            logs,
            key=lambda log: (
                log.participant_id,
                log.tutor_session_created_at,
                log.tutor_session_id,
            ),
        )
        return ok(ExportDialogLogsResponse(logs=tuple(ordered)))
