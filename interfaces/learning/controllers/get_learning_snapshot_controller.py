# 仕様: docs/spec/interfaces-layer.md#既存-API-対応表
"""GetLearningSnapshot の Controller。"""
from __future__ import annotations

from application.common.errors import AppError, LectureNotFoundError
from application.common.result import Result
from application.learning.dto.get_learning_snapshot import (
    GetLearningSnapshotRequest,
    GetLearningSnapshotResponse,
)
from application.learning.ports.lecture_catalog import LectureCatalog
from application.learning.use_cases.get_learning_snapshot import (
    GetLearningSnapshotUseCase,
)

from interfaces.common.error_presenter import present_error
from interfaces.common.ingress import parse_learner_id, parse_lecture_id
from interfaces.learning.presenters.lad_dashboard_presenter import LadDashboardPresenter
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.learning.view_models.lad_dashboard import LadDashboardViewModel


class GetLearningSnapshotController:
    """外部入力を正規化し、UC 実行後に LAD ViewModel を返す。"""

    def __init__(
        self,
        use_case: GetLearningSnapshotUseCase,
        presenter: LadDashboardPresenter,
        lecture_catalog: LectureCatalog,
    ) -> None:
        self._use_case = use_case
        self._presenter = presenter
        self._lecture_catalog = lecture_catalog

    def execute(
        self,
        participant_id: str,
        *,
        lecture_id: str | None = None,
    ) -> LadDashboardViewModel | ErrorViewModel:
        learner_result = parse_learner_id(participant_id)
        if learner_result.is_err:
            return present_error(learner_result.error)

        lecture_result = parse_lecture_id(lecture_id)
        if lecture_result.is_err:
            return present_error(lecture_result.error)

        request = GetLearningSnapshotRequest(
            learner_id=learner_result.value,
            lecture_id=lecture_result.value,
        )
        result = self._use_case.execute(request)
        return self._present_or_error(result)

    def _present_or_error(
        self,
        result: Result[GetLearningSnapshotResponse, AppError],
    ) -> LadDashboardViewModel | ErrorViewModel:
        if result.is_err:
            return present_error(result.error)

        lecture = self._lecture_catalog.find_by_id(result.value.snapshot.lecture_id)
        if lecture is None:
            return present_error(
                LectureNotFoundError(
                    f"lecture not found: {result.value.snapshot.lecture_id!s}"
                )
            )

        return self._presenter.present(result.value, lecture)
