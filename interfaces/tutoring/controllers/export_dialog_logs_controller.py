# 仕様: docs/spec/research-dialog-download.md#url-と資格情報共有if固定済み2026-10-19
"""研究用ダウンロードの Controller。参加者IDは検証も変換もしない(Q6)。"""
from __future__ import annotations

from application.tutoring.dto.export_dialog_logs import ExportDialogLogsRequest
from application.tutoring.use_cases.export_dialog_logs import ExportDialogLogsUseCase
from interfaces.common.error_presenter import present_error
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.tutoring.presenters.research_dialog_logs_presenter import (
    ResearchDialogLogsPresenter,
)
from interfaces.tutoring.view_models.research_dialog_logs import (
    ResearchDialogLogsViewModel,
)


class ExportDialogLogsController:
    def __init__(
        self,
        use_case: ExportDialogLogsUseCase,
        presenter: ResearchDialogLogsPresenter,
    ) -> None:
        self._use_case = use_case
        self._presenter = presenter

    def execute_for_participant(
        self, participant_id: str
    ) -> ResearchDialogLogsViewModel | ErrorViewModel:
        return self._run(ExportDialogLogsRequest(participant_id=participant_id))

    def execute_all(self) -> ResearchDialogLogsViewModel | ErrorViewModel:
        return self._run(ExportDialogLogsRequest(participant_id=None))

    def _run(
        self, request: ExportDialogLogsRequest
    ) -> ResearchDialogLogsViewModel | ErrorViewModel:
        result = self._use_case.execute(request)
        if result.is_err:
            return present_error(result.error)
        return self._presenter.present(result.value)
