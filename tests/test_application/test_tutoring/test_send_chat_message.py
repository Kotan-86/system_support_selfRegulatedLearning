# 仕様: docs/spec/application-usecase.md#SendChatMessage
"""SendChatMessageUseCase の受入基準テスト。"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

from application.common.errors import (
    ErrorCode,
    LectureNotFoundError,
    LlmGatewayError,
    TutorSessionNotFoundError,
    ValidationError,
)
from application.common.result import Err, Ok
from application.learning.adapters.get_learning_snapshot_query import (
    GetLearningSnapshotQuery,
)
from application.learning.dto.record_quiz_attempt import RecordQuizAttemptRequest
from application.learning.use_cases.get_learning_snapshot import GetLearningSnapshotUseCase
from application.learning.use_cases.record_quiz_attempt import RecordQuizAttemptUseCase
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from application.tutoring.dto.send_chat_message import SendChatMessageRequest
from application.tutoring.ports.llm_gateway import LlmGateway
from application.tutoring.use_cases.send_chat_message import (
    FIRST_MESSAGE_CANNED_RESPONSE,
    SendChatMessageUseCase,
)
from domain.learning.learning_snapshot import LearningSnapshot
from domain.shared.ids import (
    LectureId,
    LearnerId,
    MessageId,
    TutorSessionId,
)
from domain.tutoring.message import MessageRole
from tests.test_application.fakes.learning.fake_id_generators import (
    FakeLearningSessionIdGenerator,
)
from tests.test_application.fakes.learning.fake_lecture_catalog import FakeLectureCatalog
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)
from tests.test_application.fakes.tutoring.fake_chat_prompt_builder import (
    FakeChatPromptBuilder,
)
from tests.test_application.fakes.tutoring.fake_id_generators import FakeMessageIdGenerator
from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway
from tests.test_application.fakes.tutoring.in_memory_tutor_session_repository import (
    InMemoryTutorSessionRepository,
)
from tests.test_application.test_learning.test_get_learning_snapshot import (
    _five_answers,
    _get_snapshot_use_case,
    _lecture,
    _record_quiz_use_case,
)
from tests.test_application.test_tutoring.test_start_or_get_tutor_session import (
    _use_case as _start_or_get_tutor_use_case,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TUTORING_APP_DIR = PROJECT_ROOT / "application" / "tutoring"

FORBIDDEN_LEARNING_ENTITY_MODULES = {
    "domain.learning.learning_session",
    "domain.learning.viewing_event",
    "domain.learning.quiz_attempt",
    "domain.learning.quiz_definition",
}

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _imported_modules(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _request(
    *,
    user_message: str = "こんにちは",
    learner_id: str = "learner-1",
    lecture_id: str = "lecture-1",
    tutor_session_id: str | None = None,
    sent_at: datetime = FIXED_NOW,
) -> SendChatMessageRequest:
    return SendChatMessageRequest(
        user_message=user_message,
        sent_at=sent_at,
        tutor_session_id=(
            TutorSessionId(tutor_session_id) if tutor_session_id is not None else None
        ),
        learner_id=LearnerId(learner_id),
        lecture_id=LectureId(lecture_id),
    )


class _FailingLlmGateway(LlmGateway):
    """LLM 呼び出し失敗をシミュレートする Fake。"""

    def generate(self, prompt: str) -> str:
        raise LlmGatewayError("LLM gateway failed in test")


def _send_chat_use_case(
    *,
    learning_repository: InMemoryLearningSessionRepository | None = None,
    tutor_repository: InMemoryTutorSessionRepository | None = None,
    lecture_catalog: FakeLectureCatalog | None = None,
    chat_prompt_builder: FakeChatPromptBuilder | None = None,
    llm_gateway: FakeLlmGateway | LlmGateway | None = None,
    message_id_generator: FakeMessageIdGenerator | None = None,
) -> SendChatMessageUseCase:
    learning_repo = learning_repository or InMemoryLearningSessionRepository()
    tutor_repo = tutor_repository or InMemoryTutorSessionRepository()
    catalog = lecture_catalog or FakeLectureCatalog(lectures=(_lecture(),))
    snapshot_uc = _get_snapshot_use_case(repository=learning_repo)

    return SendChatMessageUseCase(
        start_or_get_learning=StartOrGetLearningSessionUseCase(
            repository=learning_repo,
            id_generator=FakeLearningSessionIdGenerator(),
        ),
        start_or_get_tutor=_start_or_get_tutor_use_case(repository=tutor_repo),
        learning_snapshot_query=GetLearningSnapshotQuery(snapshot_uc),
        chat_prompt_builder=chat_prompt_builder or FakeChatPromptBuilder(),
        llm_gateway=llm_gateway or FakeLlmGateway(),
        repository=tutor_repo,
        message_id_generator=message_id_generator or FakeMessageIdGenerator(),
        lecture_catalog=catalog,
    )


class TestSendChatMessageFirstCompose:
    """初回送信で Learning / Tutor Session を compose する。"""

    def test_first_message_composes_sessions_and_returns_tutor_session_id(self) -> None:
        learning_repo = InMemoryLearningSessionRepository()
        tutor_repo = InMemoryTutorSessionRepository()
        llm = FakeLlmGateway(response="assistant reply")
        use_case = _send_chat_use_case(
            learning_repository=learning_repo,
            tutor_repository=tutor_repo,
            llm_gateway=llm,
        )

        result = use_case.execute(_request(user_message="初回メッセージ"))

        assert isinstance(result, Ok)
        assert result.value.tutor_session_id == TutorSessionId("ts-1")
        assert result.value.assistant_content == "assistant reply"
        assert result.value.user_message_id == MessageId("msg-1")
        assert result.value.assistant_message_id == MessageId("msg-2")
        assert learning_repo.save_count == 1
        assert tutor_repo.save_count == 2
        assert len(learning_repo.all_sessions()) == 1
        assert len(tutor_repo.all_sessions()) == 1
        assert llm.generate_calls == ["fake-prompt"]


class TestSendChatMessageContinuation:
    """2 回目以降は同一 TutorSession に Message を追記する。"""

    def test_second_message_appends_to_existing_tutor_session(self) -> None:
        learning_repo = InMemoryLearningSessionRepository()
        tutor_repo = InMemoryTutorSessionRepository()
        llm = FakeLlmGateway(response="first reply")
        use_case = _send_chat_use_case(
            learning_repository=learning_repo,
            tutor_repository=tutor_repo,
            llm_gateway=llm,
        )

        first = use_case.execute(_request(user_message="1通目"))
        llm.set_response("second reply")
        assert isinstance(first, Ok)

        second = use_case.execute(
            _request(
                user_message="2通目",
                tutor_session_id=str(first.value.tutor_session_id),
            )
        )

        assert isinstance(second, Ok)
        assert second.value.tutor_session_id == first.value.tutor_session_id
        assert second.value.assistant_content == "second reply"
        assert learning_repo.save_count == 1
        assert tutor_repo.save_count == 3

        saved = tutor_repo.find_by_id(first.value.tutor_session_id)
        assert saved is not None
        assert len(saved.messages) == 4
        assert saved.messages[0].role is MessageRole.USER
        assert saved.messages[0].content == "1通目"
        assert saved.messages[2].role is MessageRole.USER
        assert saved.messages[2].content == "2通目"
        assert saved.messages[3].content == "second reply"


class TestSendChatMessageSnapshotIntegration:
    """LearningSnapshotQuery 経由で LAD 同契約の Snapshot がプロンプト入力になる。"""

    def test_snapshot_quiz_answers_are_passed_to_chat_prompt_builder(self) -> None:
        learning_repo = InMemoryLearningSessionRepository()
        record_quiz = _record_quiz_use_case(learning_repo)
        record_result = record_quiz.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                attempted_at=FIXED_NOW,
                score_numerator=4,
                score_denominator=5,
                answers=_five_answers(wrong_at=3),
            )
        )
        assert isinstance(record_result, Ok)

        builder = FakeChatPromptBuilder()
        use_case = _send_chat_use_case(
            learning_repository=learning_repo,
            chat_prompt_builder=builder,
        )

        result = use_case.execute(_request(user_message="小テストについて"))

        assert isinstance(result, Ok)
        assert len(builder.build_calls) == 1
        snapshot = builder.build_calls[0].snapshot
        assert isinstance(snapshot, LearningSnapshot)
        assert len(snapshot.quiz_answers) == 5
        assert snapshot.quiz_answers[2].question_index == 3
        assert snapshot.quiz_answers[2].is_correct is False


class TestSendChatMessageDigitsOnlyFirstMessage:
    """初回・半角数字のみのとき定型文を返し LLM を呼ばない。"""

    def test_digits_only_first_message_returns_canned_response_without_llm(self) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        llm = FakeLlmGateway()
        builder = FakeChatPromptBuilder()
        use_case = _send_chat_use_case(
            tutor_repository=tutor_repo,
            llm_gateway=llm,
            chat_prompt_builder=builder,
        )

        result = use_case.execute(_request(user_message="12345"))

        assert isinstance(result, Ok)
        assert result.value.assistant_content == FIRST_MESSAGE_CANNED_RESPONSE
        assert llm.generate_calls == []
        assert builder.build_calls == []
        assert tutor_repo.save_count == 2

        saved = tutor_repo.all_sessions()[0]
        assert len(saved.messages) == 2
        assert saved.messages[0].content == "12345"
        assert saved.messages[1].content == FIRST_MESSAGE_CANNED_RESPONSE

    def test_second_digits_only_message_still_calls_llm(self) -> None:
        llm = FakeLlmGateway(response="llm reply")
        use_case = _send_chat_use_case(llm_gateway=llm)

        first = use_case.execute(_request(user_message="1"))
        assert isinstance(first, Ok)

        llm.set_response("second llm reply")
        second = use_case.execute(
            _request(
                user_message="2",
                tutor_session_id=str(first.value.tutor_session_id),
            )
        )

        assert isinstance(second, Ok)
        assert second.value.assistant_content == "second llm reply"
        assert len(llm.generate_calls) == 1


class TestSendChatMessageErrors:
    """エラー系の受入基準。"""

    def test_empty_user_message_returns_validation_error(self) -> None:
        use_case = _send_chat_use_case()
        result = use_case.execute(_request(user_message=""))

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code == ErrorCode.EMPTY_USER_MESSAGE

    def test_unknown_tutor_session_id_returns_not_found(self) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        use_case = _send_chat_use_case(tutor_repository=tutor_repo)

        result = use_case.execute(
            _request(
                user_message="継続",
                tutor_session_id="missing-tutor",
            )
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, TutorSessionNotFoundError)
        assert result.error.code == ErrorCode.TUTOR_SESSION_NOT_FOUND
        assert tutor_repo.save_count == 0

    def test_missing_lecture_returns_lecture_not_found(self) -> None:
        catalog = FakeLectureCatalog()
        use_case = _send_chat_use_case(lecture_catalog=catalog)

        result = use_case.execute(_request(user_message="hello"))

        assert isinstance(result, Err)
        assert isinstance(result.error, LectureNotFoundError)
        assert result.error.code == ErrorCode.LECTURE_NOT_FOUND

    def test_llm_failure_does_not_persist_messages(self) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        use_case = _send_chat_use_case(
            tutor_repository=tutor_repo,
            llm_gateway=_FailingLlmGateway(),
        )

        result = use_case.execute(_request(user_message="LLM 失敗テスト"))

        assert isinstance(result, Err)
        assert isinstance(result.error, LlmGatewayError)
        assert result.error.code == ErrorCode.LLM_GATEWAY_ERROR
        assert tutor_repo.save_count == 1
        saved = tutor_repo.all_sessions()[0]
        assert saved.messages == ()


class TestSendChatMessageValidation:
    """Request 検証。"""

    def test_first_message_without_learner_id_returns_validation_error(self) -> None:
        request = SendChatMessageRequest(
            user_message="hello",
            sent_at=FIXED_NOW,
            learner_id=None,
            lecture_id=LectureId("lecture-1"),
        )
        use_case = _send_chat_use_case()

        result = use_case.execute(request)

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)


class TestSendChatMessageContextBoundaries:
    """Tutoring アプリケーション層が Learning Entity を直接 import しない。"""

    def test_tutoring_application_does_not_import_learning_entities(self) -> None:
        violations: list[str] = []
        for py_file in sorted(TUTORING_APP_DIR.rglob("*.py")):
            imported = _imported_modules(py_file)
            forbidden = imported & FORBIDDEN_LEARNING_ENTITY_MODULES
            if forbidden:
                rel = py_file.relative_to(PROJECT_ROOT)
                violations.append(f"{rel}: {sorted(forbidden)}")
        assert violations == []
