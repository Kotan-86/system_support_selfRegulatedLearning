# 仕様: docs/spec/interfaces-layer.md#ChatResponseViewModel
"""SendChatMessage の成功応答 ViewModel を生成する。"""
from __future__ import annotations

from application.tutoring.dto.send_chat_message import SendChatMessageResponse

from interfaces.tutoring.view_models.chat_response import ChatResponseViewModel


class ChatResponsePresenter:
    """SendChatMessageResponse を ChatResponseViewModel へ変換する。"""

    def present(self, response: SendChatMessageResponse) -> ChatResponseViewModel:
        return ChatResponseViewModel(
            response=response.assistant_content,
            session_id=str(response.tutor_session_id),
        )
