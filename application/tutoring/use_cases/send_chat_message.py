# 仕様: docs/spec/application-usecase.md#SendChatMessage
# 仕様: docs/spec/application-error-handling.md#SendChatMessage
"""SendChatMessage ユースケース。"""
from __future__ import annotations

import re

from application.common.errors import (
    AppError,
    LectureNotFoundError,
    LlmGatewayError,
    TutorSessionNotFoundError,
)
from application.common.result import Result, err, ok
from application.learning.dto.start_or_get_learning_session import (
    StartOrGetLearningSessionRequest,
)
from application.learning.ports.learning_snapshot_query import LearningSnapshotQuery
from application.learning.ports.lecture_catalog import LectureCatalog
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from application.tutoring.dto.send_chat_message import (
    SendChatMessageRequest,
    SendChatMessageResponse,
)
from application.tutoring.dto.start_or_get_tutor_session import (
    StartOrGetTutorSessionRequest,
)
from application.tutoring.ports.chat_prompt_builder import ChatPromptBuilder
from application.tutoring.ports.id_generators import MessageIdGenerator
from application.tutoring.ports.llm_gateway import LlmGateway
from application.tutoring.ports.tutor_session_repository import TutorSessionRepository
from application.tutoring.use_cases.start_or_get_tutor_session import (
    StartOrGetTutorSessionUseCase,
)
from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.message import MessageRole
from domain.tutoring.tutor_session import TutorSession

FIRST_MESSAGE_CANNED_RESPONSE = (
    "学習者IDを確認しました。学習で気になったことや質問があれば、いつでも送ってください。"
)

_DIGITS_ONLY_PATTERN = re.compile(r"^[0-9]+$")


class SendChatMessageUseCase:
    """学習者の 1 発話に対し AI 応答を生成し TutorSession に追記する。"""

    def __init__(
        self,
        start_or_get_learning: StartOrGetLearningSessionUseCase,
        start_or_get_tutor: StartOrGetTutorSessionUseCase,
        learning_snapshot_query: LearningSnapshotQuery,
        chat_prompt_builder: ChatPromptBuilder,
        llm_gateway: LlmGateway,
        repository: TutorSessionRepository,
        message_id_generator: MessageIdGenerator,
        lecture_catalog: LectureCatalog,
    ) -> None:
        self._start_or_get_learning = start_or_get_learning
        self._start_or_get_tutor = start_or_get_tutor
        self._learning_snapshot_query = learning_snapshot_query
        self._chat_prompt_builder = chat_prompt_builder
        self._llm_gateway = llm_gateway
        self._repository = repository
        self._message_id_generator = message_id_generator
        self._lecture_catalog = lecture_catalog

    def execute(
        self, request: SendChatMessageRequest
    ) -> Result[SendChatMessageResponse, AppError]:
        validated = request.validate()
        if validated.is_err:
            return validated  # type: ignore[return-value]

        req = validated.value
        tutor_session_result = self._resolve_tutor_session(req)
        if tutor_session_result.is_err:
            return tutor_session_result  # type: ignore[return-value]

        tutor_session = tutor_session_result.value
        snapshot_result = self._fetch_snapshot(req)
        if snapshot_result.is_err:
            return snapshot_result  # type: ignore[return-value]

        lecture = self._lecture_catalog.find_by_id(req.lecture_id)  # type: ignore[arg-type]
        if lecture is None:
            return err(
                LectureNotFoundError(
                    f"lecture not found: {req.lecture_id!s}"
                )
            )

        assistant_result = self._generate_assistant_content(
            user_message=req.user_message,
            tutor_session=tutor_session,
            snapshot=snapshot_result.value,
            lecture=lecture,
        )
        if assistant_result.is_err:
            return assistant_result  # type: ignore[return-value]

        user_msg_id = self._message_id_generator.next_id()
        asst_msg_id = self._message_id_generator.next_id()
        updated = (
            tutor_session.append_message(
                message_id=user_msg_id,
                role=MessageRole.USER,
                content=req.user_message,
                created_at=req.sent_at,
            ).append_message(
                message_id=asst_msg_id,
                role=MessageRole.ASSISTANT,
                content=assistant_result.value,
                created_at=req.sent_at,
            )
        )
        self._repository.save(updated)
        return ok(
            SendChatMessageResponse(
                tutor_session_id=updated.id,
                assistant_content=assistant_result.value,
                user_message_id=user_msg_id,
                assistant_message_id=asst_msg_id,
            )
        )

    def _resolve_tutor_session(
        self, req: SendChatMessageRequest
    ) -> Result[TutorSession, AppError]:
        if req.tutor_session_id is not None:
            session = self._repository.find_by_id(req.tutor_session_id)
            if session is None:
                return err(
                    TutorSessionNotFoundError(
                        f"tutor session not found: {req.tutor_session_id!s}"
                    )
                )
            return ok(session)

        learning_result = self._start_or_get_learning.execute(
            StartOrGetLearningSessionRequest(
                learner_id=req.learner_id,  # type: ignore[arg-type]
                lecture_id=req.lecture_id,  # type: ignore[arg-type]
                started_at=req.sent_at,
            )
        )
        if learning_result.is_err:
            return learning_result  # type: ignore[return-value]

        tutor_result = self._start_or_get_tutor.execute(
            StartOrGetTutorSessionRequest(
                learning_session_id=learning_result.value.session_id,
                started_at=req.sent_at,
            )
        )
        if tutor_result.is_err:
            return tutor_result  # type: ignore[return-value]

        return ok(tutor_result.value.session)

    def _fetch_snapshot(
        self, req: SendChatMessageRequest
    ) -> Result[LearningSnapshot, AppError]:
        try:
            snapshot = self._learning_snapshot_query.get_by_learner_and_lecture(
                req.learner_id,  # type: ignore[arg-type]
                req.lecture_id,  # type: ignore[arg-type]
            )
        except AppError as error:
            return err(error)
        return ok(snapshot)

    def _generate_assistant_content(
        self,
        *,
        user_message: str,
        tutor_session: TutorSession,
        snapshot: LearningSnapshot,
        lecture: Lecture,
    ) -> Result[str, AppError]:
        if (
            not tutor_session.messages
            and _DIGITS_ONLY_PATTERN.match(user_message.strip())
        ):
            return ok(FIRST_MESSAGE_CANNED_RESPONSE)

        prompt = self._chat_prompt_builder.build(
            snapshot,
            tutor_session.messages,
            user_message,
            lecture,
        )
        try:
            content = self._llm_gateway.generate(prompt)
        except LlmGatewayError as error:
            return err(error)
        except Exception as exc:
            return err(LlmGatewayError(f"LLM gateway failed: {exc}"))

        if not content:
            return err(LlmGatewayError("LLM gateway returned empty response"))

        return ok(content)
