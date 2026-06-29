# 仕様: docs/spec/interfaces-layer.md#既存-API-対応表
"""RecordViewingEventController の単体テスト。"""
from __future__ import annotations

from application.common.errors import ErrorCode
from application.learning.use_cases.record_viewing_event import RecordViewingEventUseCase
from interfaces.learning.controllers.record_viewing_event_controller import (
    RecordViewingEventController,
)
from interfaces.learning.presenters.record_viewing_event_presenter import (
    RecordViewingEventPresenter,
)
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.learning.view_models.record_responses import (
    RecordViewingEventSuccessViewModel,
)
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)
from tests.test_application.test_learning.test_record_viewing_event import _use_case


def _gas_viewing_log_payload(**overrides: object) -> dict[str, object]:
    """POST /api/viewing-log の API 契約 JSON と同一の形。"""
    payload: dict[str, object] = {
        "participant_id": "1",
        "time_stamp": "2026-02-23T11:18:42.000Z",
        "current_time": 0,
        "action": "play",
        "duration": 0.0,
    }
    payload.update(overrides)
    return payload


def _controller(
    use_case: RecordViewingEventUseCase | None = None,
) -> RecordViewingEventController:
    return RecordViewingEventController(
        use_case=use_case or _use_case(),
        presenter=RecordViewingEventPresenter(),
    )


class TestRecordViewingEventController:
    """Controller の ingress と UC 連携を検証する。"""

    def test_gas_payload_returns_success_view_model(self) -> None:
        repository = InMemoryLearningSessionRepository()
        controller = _controller(_use_case(repository=repository))

        result = controller.execute(_gas_viewing_log_payload())

        assert isinstance(result, RecordViewingEventSuccessViewModel)
        assert result.ok is True
        assert len(repository.all_sessions()) == 1
        assert len(repository.all_sessions()[0].viewing_events) == 1

    def test_truncates_fractional_current_time_and_duration(self) -> None:
        repository = InMemoryLearningSessionRepository()
        controller = _controller(_use_case(repository=repository))

        result = controller.execute(
            _gas_viewing_log_payload(
                current_time=90.9,
                action="forward_skip",
                duration=10.5,
            )
        )

        assert isinstance(result, RecordViewingEventSuccessViewModel)
        event = repository.all_sessions()[0].viewing_events[0]
        assert event.video_position == 90
        assert event.position_delta == 10

    def test_empty_participant_id_returns_validation_error_view_model(self) -> None:
        controller = _controller()

        result = controller.execute(_gas_viewing_log_payload(participant_id=""))

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.VALIDATION_ERROR.value
        assert result.status_kind.value == "validation"

    def test_missing_current_time_returns_validation_error_view_model(self) -> None:
        controller = _controller()
        payload = _gas_viewing_log_payload()
        del payload["current_time"]

        result = controller.execute(payload)

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.VALIDATION_ERROR.value
        assert "current_time" in result.message

    def test_unknown_action_returns_validation_error_view_model(self) -> None:
        controller = _controller()

        result = controller.execute(_gas_viewing_log_payload(action="invalid_action"))

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.VALIDATION_ERROR.value
        assert "unknown action" in result.message

    def test_invalid_viewing_invariant_returns_invalid_viewing_event(self) -> None:
        controller = _controller()

        result = controller.execute(
            _gas_viewing_log_payload(action="play", duration=5)
        )

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.INVALID_VIEWING_EVENT.value
        assert result.status_kind.value == "validation"
