# 仕様: docs/spec/dialog-log-save.md#保存-API
"""SaveDialogLog の Controller。"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from application.common.errors import LectureNotFoundError, ValidationError
from application.common.result import Result
from application.learning.ports.lecture_catalog import LectureCatalog
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
        lecture_catalog: LectureCatalog | None = None,
    ) -> None:
        self._use_case = use_case
        self._presenter = presenter
        # 本文の lecture_id が登録済みかの検査に使う(None のときは検査しない)
        self._lecture_catalog = lecture_catalog

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

        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC21(任意の lecture_id。なければ固定割当)
        raw_lecture_id = payload.get("lecture_id")
        if raw_lecture_id is not None and not isinstance(raw_lecture_id, str):
            return present_error(ValidationError("lecture_id must be a string"))
        lecture_result = parse_lecture_id_for_participant(
            participant_id.strip(), raw_lecture_id
        )
        if lecture_result.is_err:
            return present_error(lecture_result.error)
        if (
            raw_lecture_id is not None
            and self._lecture_catalog is not None
            and self._lecture_catalog.find_by_id(lecture_result.value) is None
        ):
            return present_error(
                LectureNotFoundError(f"lecture not found: {lecture_result.value!s}")
            )

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
