# 仕様: docs/spec/interfaces-layer.md#既存-API-対応表
"""RecordViewingEvent の Controller。"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from application.common.errors import AppError, ValidationError
from application.common.result import Result
from application.learning.dto.record_viewing_event import (
    RecordViewingEventRequest,
    RecordViewingEventResponse,
)
from application.learning.use_cases.record_viewing_event import RecordViewingEventUseCase

from interfaces.common.error_presenter import present_error
from interfaces.common.ingress import (
    parse_learner_id,
    parse_lecture_id,
    parse_occurred_at,
    parse_position_delta,
    parse_video_position,
    parse_viewing_action,
)
from interfaces.learning.presenters.record_viewing_event_presenter import (
    RecordViewingEventPresenter,
)
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.learning.view_models.record_responses import (
    RecordViewingEventSuccessViewModel,
)


class RecordViewingEventController:
    """GAS 視聴ログ payload を正規化し、UC 実行後に成功 ViewModel を返す。"""

    def __init__(
        self,
        use_case: RecordViewingEventUseCase,
        presenter: RecordViewingEventPresenter,
    ) -> None:
        self._use_case = use_case
        self._presenter = presenter

    def execute(
        self,
        payload: Mapping[str, Any],
    ) -> RecordViewingEventSuccessViewModel | ErrorViewModel:
        learner_result = parse_learner_id(str(payload.get("participant_id") or ""))
        if learner_result.is_err:
            return present_error(learner_result.error)

        lecture_result = parse_lecture_id(payload.get("lecture_id"))
        if lecture_result.is_err:
            return present_error(lecture_result.error)

        occurred_result = parse_occurred_at(payload.get("time_stamp"))
        if occurred_result.is_err:
            return present_error(occurred_result.error)

        if payload.get("current_time") is None:
            return present_error(ValidationError("current_time is required"))
        video_position_result = parse_video_position(payload.get("current_time"))
        if video_position_result.is_err:
            return present_error(video_position_result.error)

        action_result = parse_viewing_action(payload.get("action"))
        if action_result.is_err:
            return present_error(action_result.error)

        if payload.get("duration") is None:
            return present_error(ValidationError("duration is required"))
        position_delta_result = parse_position_delta(payload.get("duration"))
        if position_delta_result.is_err:
            return present_error(position_delta_result.error)

        request = RecordViewingEventRequest(
            learner_id=learner_result.value,
            lecture_id=lecture_result.value,
            occurred_at=occurred_result.value,
            video_position=video_position_result.value,
            action=action_result.value,
            position_delta=position_delta_result.value,
        )
        result = self._use_case.execute(request)
        return self._present_or_error(result)

    def _present_or_error(
        self,
        result: Result[RecordViewingEventResponse, AppError],
    ) -> RecordViewingEventSuccessViewModel | ErrorViewModel:
        if result.is_err:
            return present_error(result.error)

        return self._presenter.present(result.value)
