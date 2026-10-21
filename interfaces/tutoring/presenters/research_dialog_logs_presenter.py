# 仕様: docs/spec/research-dialog-download.md#json-の形
"""研究用ダウンロードの Presenter。順序はユースケースの結果のまま。"""
from __future__ import annotations

from application.tutoring.dto.export_dialog_logs import (
    ExportDialogLogsResponse,
    ResearchDialogLog,
)
from interfaces.tutoring.dialog_log_json_format import (
    FORMAT_VERSION,
    format_log_timestamp,
    message_to_json_dict,
)
from interfaces.tutoring.view_models.research_dialog_logs import (
    ResearchDialogLogsViewModel,
    ResearchDialogLogViewModel,
)


def _present_log(log: ResearchDialogLog) -> ResearchDialogLogViewModel:
    return ResearchDialogLogViewModel(
        format_version=FORMAT_VERSION,
        participant_id=log.participant_id,
        lecture_id=log.lecture_id,
        learning_session_id=log.learning_session_id,
        tutor_session_id=log.tutor_session_id,
        ended_at=(
            format_log_timestamp(log.ended_at) if log.ended_at is not None else None
        ),
        end_method=log.end_method.value if log.end_method is not None else None,
        messages=tuple(message_to_json_dict(m) for m in log.messages),
    )


class ResearchDialogLogsPresenter:
    def present(self, response: ExportDialogLogsResponse) -> ResearchDialogLogsViewModel:
        return ResearchDialogLogsViewModel(
            logs=tuple(_present_log(log) for log in response.logs)
        )
