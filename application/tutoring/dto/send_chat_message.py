# 仕様: docs/spec/application-usecase.md#SendChatMessage
"""SendChatMessage の Request / Response DTO。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.common.errors import ErrorCode, ValidationError
from application.common.result import Result, err, ok
from domain.shared.ids import LectureId, LearnerId, MessageId, TutorSessionId


@dataclass(frozen=True)
class SendChatMessageRequest:
    """SendChatMessage の入力。"""

    user_message: str
    sent_at: datetime
    tutor_session_id: TutorSessionId | None = None
    learner_id: LearnerId | None = None
    lecture_id: LectureId | None = None

    def validate(self) -> Result[SendChatMessageRequest, ValidationError]:
        if not self.user_message:
            return err(
                ValidationError(
                    "user_message must not be empty",
                    code=ErrorCode.EMPTY_USER_MESSAGE,
                )
            )

        if self.tutor_session_id is None:
            if not self.learner_id:
                return err(ValidationError("learner_id must not be empty"))
            if not self.lecture_id:
                return err(ValidationError("lecture_id must not be empty"))
        elif not self.learner_id:
            return err(ValidationError("learner_id must not be empty"))
        elif not self.lecture_id:
            return err(ValidationError("lecture_id must not be empty"))

        return ok(self)


@dataclass(frozen=True)
class SendChatMessageResponse:
    """SendChatMessage の出力。"""

    tutor_session_id: TutorSessionId
    assistant_content: str
    user_message_id: MessageId
    assistant_message_id: MessageId
