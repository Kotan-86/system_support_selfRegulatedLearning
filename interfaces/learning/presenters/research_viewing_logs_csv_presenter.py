# 仕様: docs/spec/research-lad-csv-download.md#視聴ログの-csv-の列この順pbi-1
# 仕様: docs/spec/research-lad-csv-download.md#何本目の列round_number共有if2つの-csv-に共通pbi-c決定-multi-video-learningmd-の-q7q-c1q-c42026-11-14
"""研究用の視聴ログ CSV の Presenter。行の順はユースケースの結果のまま。"""
from __future__ import annotations

import re

from application.learning.dto.export_viewing_logs import ExportViewingLogsResponse
from interfaces.common.csv_encoding import encode_csv, guard_formula
from interfaces.learning.view_models.research_csv import ResearchCsvViewModel

HEADER = (
    "participant_id",
    "round_number",
    "lecture_id",
    "learning_session_id",
    "viewing_log_id",
    "time_stamp",
    "current_time",
    "action",
    "duration",
)
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]+")


def csv_filename(prefix: str, participant_id: str | None) -> str:
    """一括は `<prefix>_all.csv`。参加者IDが英数字・-・_ だけなら入れ、それ以外は `_participant`。"""
    if participant_id is None:
        return f"{prefix}_all.csv"
    if _SAFE_ID.fullmatch(participant_id):
        return f"{prefix}_{participant_id}.csv"
    return f"{prefix}_participant.csv"


class ResearchViewingLogsCsvPresenter:
    def present(
        self, response: ExportViewingLogsResponse, participant_id: str | None
    ) -> ResearchCsvViewModel:
        rows = [
            (
                guard_formula(log.participant_id),
                log.round_number,
                guard_formula(log.lecture_id),
                guard_formula(log.learning_session_id),
                log.viewing_log_id,
                guard_formula(log.time_stamp),
                log.current_time,
                guard_formula(log.action),
                repr(float(log.duration)),
            )
            for log in response.logs
        ]
        return ResearchCsvViewModel(
            filename=csv_filename("viewing-logs", participant_id),
            content=encode_csv(HEADER, rows),
        )
