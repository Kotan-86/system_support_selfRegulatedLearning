# 仕様: docs/spec/interfaces-layer.md#既存-API-対応表
"""SendChatMessage の Controller。"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from application.common.errors import AppError
from application.common.result import Result
from application.tutoring.dto.send_chat_message import (
    SendChatMessageRequest,
    SendChatMessageResponse,
)
from application.tutoring.use_cases.send_chat_message import SendChatMessageUseCase

from interfaces.common.error_presenter import present_error
from interfaces.common.ingress import (
    parse_learner_id,
    parse_lecture_id,
    parse_tutor_session_id,
    parse_user_message,
)
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.tutoring.presenters.chat_response_presenter import ChatResponsePresenter
from interfaces.tutoring.view_models.chat_response import ChatResponseViewModel


class SendChatMessageController:
    """POST /chat payload を正規化し、UC 実行後に ChatResponseViewModel を返す。"""

    def __init__(
        self,
        use_case: SendChatMessageUseCase,
        presenter: ChatResponsePresenter,
    ) -> None:
        self._use_case = use_case
        self._presenter = presenter

    def execute(
        self,
        payload: Mapping[str, Any],
        *,
        sent_at: datetime,
    ) -> ChatResponseViewModel | ErrorViewModel:
        message_result = parse_user_message(payload.get("message"))
        if message_result.is_err:
            return present_error(message_result.error)

        session_result = parse_tutor_session_id(payload.get("session_id"))
        if session_result.is_err:
            return present_error(session_result.error)

        learner_result = parse_learner_id(str(payload.get("participant_id") or ""))
        if learner_result.is_err:
            return present_error(learner_result.error)

        lecture_result = parse_lecture_id(payload.get("lecture_id"))
        if lecture_result.is_err:
            return present_error(lecture_result.error)

        request = SendChatMessageRequest(
            user_message=message_result.value,
            sent_at=sent_at,
            tutor_session_id=session_result.value,
            learner_id=learner_result.value,
            lecture_id=lecture_result.value,
        )
        result = self._use_case.execute(request)
        return self._present_or_error(result)

    def _present_or_error(
        self,
        result: Result[SendChatMessageResponse, AppError],
    ) -> ChatResponseViewModel | ErrorViewModel:
        if result.is_err:
            return present_error(result.error)

        return self._presenter.present(result.value)
