# 仕様: docs/spec/research-lad-csv-download.md#対象と並び順
"""研究用の視聴ログ取得のユースケース。"""
from __future__ import annotations

from application.common.errors import AppError
from application.common.result import Result, ok
from application.learning.dto.export_viewing_logs import (
    ExportViewingLogsRequest,
    ExportViewingLogsResponse,
)
from application.learning.ports.viewing_log_export_query import ViewingLogExportQuery


class ExportViewingLogsUseCase:
    """参加者ID(文字列の昇順) → round_number(数値の昇順) → viewing_log_id(昇順)に並べる。

    講義IDでは並べない。時刻では並べない(時差が混ざると文字列の順が時刻の順にならないため)。
    """

    def __init__(self, query: ViewingLogExportQuery) -> None:
        self._query = query

    def execute(
        self, request: ExportViewingLogsRequest
    ) -> Result[ExportViewingLogsResponse, AppError]:
        if request.participant_id is None:
            logs = self._query.list_all()
        else:
            logs = self._query.list_for_participant(request.participant_id)
        ordered = sorted(
            logs, key=lambda log: (log.participant_id, log.round_number, log.viewing_log_id)
        )
        return ok(ExportViewingLogsResponse(logs=tuple(ordered)))
