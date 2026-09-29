# 仕様: docs/spec/dialog-log-save.md#保存-API
"""SaveDialogLog の Controller。"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from application.common.errors import ValidationError
from application.common.result import Result
from application.tutoring.dto.save_dialog_log import SaveDialogLogRequest
from application.tutoring.use_cases.save_dialog_log import SaveDialogLogUseCase

from interfaces.common.error_presenter import present_error
from interfaces.common.ingress import (
    parse_end_method,
    parse_learner_id,
    parse_lecture_id_for_participant,
)
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.tutoring.presenters.dialog_log_saved_presenter import (
    DialogLogSavedPresenter,
)
from interfaces.tutoring.view_models.dialog_log_saved import DialogLogSavedViewModel


class SaveDialogLogController:
    """POST /api/dialog-log の本文を検証し、UC 実行後に ViewModel を返す。"""

    def __init__(
        self,
        use_case: SaveDialogLogUseCase,
        presenter: DialogLogSavedPresenter,
    ) -> None:
        self._use_case = use_case
        self._presenter = presenter

    def execute(
        self, payload: Any, *, received_at: datetime
    ) -> DialogLogSavedViewModel | ErrorViewModel:
        # payload が Mapping でない(None = 本文が JSON でない、配列など)は要求の誤り
        if not isinstance(payload, Mapping):
            return present_error(ValidationError("request body must be a JSON object"))

        participant_id = payload.get("participant_id")
        if not isinstance(participant_id, str):
            return present_error(ValidationError("participant_id must be a string"))

        learner_result = parse_learner_id(participant_id)
        if learner_result.is_err:
            return present_error(learner_result.error)

        end_method_result = parse_end_method(payload.get("end_method"))
        if end_method_result.is_err:
            return present_error(end_method_result.error)

        lecture_result = parse_lecture_id_for_participant(participant_id.strip(), None)
        if lecture_result.is_err:
            return present_error(lecture_result.error)

        request = SaveDialogLogRequest(
            learner_id=learner_result.value,
            lecture_id=lecture_result.value,
            end_method=end_method_result.value,
            received_at=received_at,
        )
        result = self._use_case.execute(request)
        if result.is_err:
            return present_error(result.error)
        return self._presenter.present(result.value)
