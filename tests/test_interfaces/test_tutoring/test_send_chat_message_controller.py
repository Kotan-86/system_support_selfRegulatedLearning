# 仕様: docs/spec/interfaces-layer.md#既存-API-対応表
"""SendChatMessageController の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.common.errors import ErrorCode
from application.tutoring.use_cases.send_chat_message import (
    FIRST_MESSAGE_CANNED_RESPONSE,
    SendChatMessageUseCase,
)
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.tutoring.controllers.send_chat_message_controller import (
    SendChatMessageController,
)
from interfaces.tutoring.presenters.chat_response_presenter import ChatResponsePresenter
from interfaces.tutoring.view_models.chat_response import ChatResponseViewModel
from tests.test_application.fakes.learning.fake_lecture_catalog import FakeLectureCatalog
from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway
from tests.test_application.test_tutoring.test_send_chat_message import (
    _FailingLlmGateway,
    _send_chat_use_case,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _chat_payload(**overrides: object) -> dict[str, object]:
    """POST /chat が送る想定の JSON と同一の形。"""
    payload: dict[str, object] = {
        "message": "こんにちは",
        "participant_id": "learner-1",
    }
    payload.update(overrides)
    return payload


def _controller(
    use_case: SendChatMessageUseCase | None = None,
) -> SendChatMessageController:
    return SendChatMessageController(
        use_case=use_case or _send_chat_use_case(),
        presenter=ChatResponsePresenter(),
    )


class TestSendChatMessageController:
    """Controller の ingress と UC 連携を検証する。"""

    def test_first_message_returns_chat_response_view_model(self) -> None:
        llm = FakeLlmGateway(response="AI 応答です")
        controller = _controller(_send_chat_use_case(llm_gateway=llm))

        result = controller.execute(_chat_payload(), sent_at=FIXED_NOW)

        assert isinstance(result, ChatResponseViewModel)
        assert result.response == "AI 応答です"
        assert result.session_id
        assert len(llm.generate_calls) == 1

    def test_digits_only_first_message_returns_canned_response(self) -> None:
        controller = _controller(_send_chat_use_case())

        result = controller.execute(
            _chat_payload(message="12345"),
            sent_at=FIXED_NOW,
        )

        assert isinstance(result, ChatResponseViewModel)
        assert result.response == FIRST_MESSAGE_CANNED_RESPONSE
        assert result.session_id

    def test_continuation_with_session_id_returns_chat_response_view_model(self) -> None:
        llm = FakeLlmGateway(response="継続応答")
        use_case = _send_chat_use_case(llm_gateway=llm)
        controller = _controller(use_case)
        first = controller.execute(
            _chat_payload(message="初回"),
            sent_at=FIXED_NOW,
        )
        assert isinstance(first, ChatResponseViewModel)

        result = controller.execute(
            _chat_payload(
                message="継続メッセージ",
                session_id=first.session_id,
                participant_id="learner-1",
            ),
            sent_at=FIXED_NOW,
        )

        assert isinstance(result, ChatResponseViewModel)
        assert result.response == "継続応答"
        assert result.session_id == first.session_id

    def test_empty_message_returns_empty_user_message_error_view_model(self) -> None:
        controller = _controller()

        result = controller.execute(_chat_payload(message=""), sent_at=FIXED_NOW)

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.EMPTY_USER_MESSAGE.value
        assert result.status_kind.value == "validation"

    def test_missing_message_returns_empty_user_message_error_view_model(self) -> None:
        controller = _controller()
        payload = _chat_payload()
        del payload["message"]

        result = controller.execute(payload, sent_at=FIXED_NOW)

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.EMPTY_USER_MESSAGE.value

    def test_empty_participant_id_returns_validation_error_view_model(self) -> None:
        controller = _controller()

        result = controller.execute(
            _chat_payload(participant_id=""),
            sent_at=FIXED_NOW,
        )

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.VALIDATION_ERROR.value
        assert result.status_kind.value == "validation"

    def test_unknown_session_id_returns_not_found_error_view_model(self) -> None:
        controller = _controller(_send_chat_use_case())

        result = controller.execute(
            _chat_payload(session_id="missing-tutor"),
            sent_at=FIXED_NOW,
        )

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.TUTOR_SESSION_NOT_FOUND.value
        assert result.status_kind.value == "not_found"

    def test_lecture_not_found_returns_not_found_error_view_model(self) -> None:
        controller = _controller(
            _send_chat_use_case(lecture_catalog=FakeLectureCatalog())
        )

        result = controller.execute(_chat_payload(), sent_at=FIXED_NOW)

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.LECTURE_NOT_FOUND.value
        assert result.status_kind.value == "not_found"

    def test_llm_failure_returns_gateway_error_view_model(self) -> None:
        controller = _controller(
            _send_chat_use_case(llm_gateway=_FailingLlmGateway())
        )

        result = controller.execute(_chat_payload(), sent_at=FIXED_NOW)

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.LLM_GATEWAY_ERROR.value
        assert result.status_kind.value == "gateway"
