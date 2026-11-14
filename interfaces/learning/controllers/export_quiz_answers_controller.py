# 仕様: docs/spec/research-lad-csv-download.md#url共有if
"""研究用の小テスト回答 CSV の Controller。参加者IDは検証も変換もしない。"""
from __future__ import annotations

from application.learning.dto.export_quiz_answers import ExportQuizAnswersRequest
from application.learning.use_cases.export_quiz_answers import ExportQuizAnswersUseCase
from interfaces.common.error_presenter import present_error
from interfaces.learning.presenters.research_quiz_answers_csv_presenter import (
    ResearchQuizAnswersCsvPresenter,
)
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.learning.view_models.research_csv import ResearchCsvViewModel


class ExportQuizAnswersController:
    def __init__(
        self,
        use_case: ExportQuizAnswersUseCase,
        presenter: ResearchQuizAnswersCsvPresenter,
    ) -> None:
        self._use_case = use_case
        self._presenter = presenter

    def execute_for_participant(
        self, participant_id: str
    ) -> ResearchCsvViewModel | ErrorViewModel:
        return self._run(participant_id)

    def execute_all(self) -> ResearchCsvViewModel | ErrorViewModel:
        return self._run(None)

    def _run(self, participant_id: str | None) -> ResearchCsvViewModel | ErrorViewModel:
        result = self._use_case.execute(ExportQuizAnswersRequest(participant_id=participant_id))
        if result.is_err:
            return present_error(result.error)
        return self._presenter.present(result.value, participant_id)
