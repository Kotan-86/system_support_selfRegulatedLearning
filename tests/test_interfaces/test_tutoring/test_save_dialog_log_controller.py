# 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-1 A8, A17)
# 仕様: docs/spec/dialog-log-save.md#保存-api
"""SaveDialogLogController / Presenter / JSON 化 / HTTP 応答(偽の use case で確認)。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from flask import Flask

from application.common.errors import LectureNotFoundError
from application.common.result import err, ok
from application.tutoring.dto.save_dialog_log import (
    EndMethod,
    SaveDialogLogRequest,
    SaveDialogLogResponse,
)
from domain.shared.ids import LearnerId, LectureId, TutorSessionId
from framework_drivers.platform.http_response import controller_result_to_flask_response
from interfaces.common import json_encoding
from interfaces.learning.view_models.errors import ErrorViewModel, StatusKind
from interfaces.tutoring.controllers.save_dialog_log_controller import (
    SaveDialogLogController,
)
from interfaces.tutoring.presenters.dialog_log_saved_presenter import (
    DialogLogSavedPresenter,
)
from interfaces.tutoring.view_models.dialog_log_saved import DialogLogSavedViewModel

RECEIVED_AT = datetime(2026, 9, 29, 1, 5, 0, tzinfo=timezone.utc)


class _FakeUseCase:
    """execute を持つ偽の SaveDialogLogUseCase。呼び出しを記録する。"""

    def __init__(self, result=None) -> None:
        self.requests: list[SaveDialogLogRequest] = []
        self._result = result

    def execute(self, request: SaveDialogLogRequest):
        self.requests.append(request)
        if self._result is not None:
            return self._result
        return ok(
            SaveDialogLogResponse(
                tutor_session_id=TutorSessionId("ts-1"),
                ended_at=request.received_at,
                end_method=request.end_method,
            )
        )


def _controller(use_case: _FakeUseCase) -> SaveDialogLogController:
    return SaveDialogLogController(
        use_case=use_case, presenter=DialogLogSavedPresenter()
    )


class TestController:
    def test_a8_valid_request_calls_use_case_and_returns_view_model(self) -> None:
        use_case = _FakeUseCase()

        result = _controller(use_case).execute(
            {"participant_id": "1", "end_method": "end_button"},
            received_at=RECEIVED_AT,
        )

        assert result == DialogLogSavedViewModel(
            tutor_session_id="ts-1",
            ended_at="2026-09-29T01:05:00+00:00",
            end_method="end_button",
        )
        assert use_case.requests == [
            SaveDialogLogRequest(
                learner_id=LearnerId("1"),
                lecture_id=LectureId("lecture-1"),
                end_method=EndMethod.END_BUTTON,
                received_at=RECEIVED_AT,
            )
        ]

    def test_a8_page_leave_is_accepted(self) -> None:
        use_case = _FakeUseCase()

        result = _controller(use_case).execute(
            {"participant_id": "1", "end_method": "page_leave"},
            received_at=RECEIVED_AT,
        )

        assert isinstance(result, DialogLogSavedViewModel)
        assert result.end_method == "page_leave"
        assert use_case.requests[0].end_method is EndMethod.PAGE_LEAVE

    @pytest.mark.parametrize(
        ("participant_id", "lecture_id"),
        [("1", "lecture-1"), ("2", "lecture-2"), ("3", "lecture-3"), ("abc", "lecture-1")],
    )
    def test_lecture_is_resolved_from_participant(
        self, participant_id: str, lecture_id: str
    ) -> None:
        use_case = _FakeUseCase()

        _controller(use_case).execute(
            {"participant_id": participant_id, "end_method": "end_button"},
            received_at=RECEIVED_AT,
        )

        assert use_case.requests[0].lecture_id == LectureId(lecture_id)
        assert use_case.requests[0].learner_id == LearnerId(participant_id)

    @pytest.mark.parametrize(
        "payload",
        [
            None,  # 本文が JSON でない
            [],
            ["participant_id"],
            "participant_id=1",
            42,
            {},
            {"end_method": "end_button"},
            {"participant_id": None, "end_method": "end_button"},
            {"participant_id": "", "end_method": "end_button"},
            {"participant_id": "   ", "end_method": "end_button"},
            {"participant_id": "1"},
            {"participant_id": "1", "end_method": None},
            {"participant_id": "1", "end_method": ""},
            {"participant_id": "1", "end_method": "leave"},
            {"participant_id": "1", "end_method": "END_BUTTON"},
            {"participant_id": "1", "end_method": 1},
        ],
    )
    def test_a17_request_errors_return_validation_and_do_not_call_use_case(
        self, payload: object
    ) -> None:
        use_case = _FakeUseCase()

        result = _controller(use_case).execute(payload, received_at=RECEIVED_AT)

        assert isinstance(result, ErrorViewModel)
        assert result.status_kind is StatusKind.VALIDATION
        assert use_case.requests == []

    def test_use_case_error_is_presented_as_error_view_model(self) -> None:
        use_case = _FakeUseCase(result=err(LectureNotFoundError("no lecture")))

        result = _controller(use_case).execute(
            {"participant_id": "1", "end_method": "end_button"},
            received_at=RECEIVED_AT,
        )

        assert isinstance(result, ErrorViewModel)
        assert result.status_kind is StatusKind.NOT_FOUND


class TestPresenter:
    def test_ended_at_uses_shared_time_format_truncated_to_seconds(self) -> None:
        response = SaveDialogLogResponse(
            tutor_session_id=TutorSessionId("ts-9"),
            ended_at=datetime(2026, 9, 29, 1, 5, 0, 987654, tzinfo=timezone.utc),
            end_method=EndMethod.PAGE_LEAVE,
        )

        view_model = DialogLogSavedPresenter().present(response)

        assert view_model == DialogLogSavedViewModel(
            tutor_session_id="ts-9",
            ended_at="2026-09-29T01:05:00+00:00",
            end_method="page_leave",
        )


class TestJsonAndHttp:
    _VIEW_MODEL = DialogLogSavedViewModel(
        tutor_session_id="ts-1",
        ended_at="2026-09-29T01:05:00+00:00",
        end_method="end_button",
    )

    def test_json_dict_has_exactly_the_three_shared_if_keys(self) -> None:
        body = json_encoding.dialog_log_saved_view_model_to_json_dict(self._VIEW_MODEL)

        assert body == {
            "tutor_session_id": "ts-1",
            "ended_at": "2026-09-29T01:05:00+00:00",
            "end_method": "end_button",
        }

    def test_http_response_is_200_with_the_json(self) -> None:
        with Flask("t").app_context():
            response, status = controller_result_to_flask_response(self._VIEW_MODEL)

            assert status == 200
            assert response.get_json() == {
                "tutor_session_id": "ts-1",
                "ended_at": "2026-09-29T01:05:00+00:00",
                "end_method": "end_button",
            }

    def test_a17_validation_error_maps_to_400(self) -> None:
        error = _controller(_FakeUseCase()).execute(None, received_at=RECEIVED_AT)
        assert isinstance(error, ErrorViewModel)

        with Flask("t").app_context():
            _, status = controller_result_to_flask_response(error)

        assert status == 400
