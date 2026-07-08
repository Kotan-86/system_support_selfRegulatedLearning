# 仕様: docs/spec/application-usecase.md#SendChatMessage
"""SendChatMessageUseCase のパイプライン統合受入基準テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.common.errors import ErrorCode, LlmGatewayError
from application.common.result import Err, Ok
from application.learning.dto.record_quiz_attempt import RecordQuizAttemptRequest
from application.tutoring.ports.interface_model_gateway import InterfaceModelGateway
from application.tutoring.ports.pedagogical_model_gateway import PedagogicalModelGateway
from application.tutoring.ports.student_model_gateway import StudentModelGateway
from domain.learning.learning_snapshot import LearningSnapshot
from domain.shared.ids import MessageId, TutorSessionId
from domain.tutoring.message import MessageRole
from tests.test_application.fakes.tutoring.fake_interface_model_gateway import (
    FakeInterfaceModelGateway,
)
from tests.test_application.fakes.tutoring.fake_pedagogical_model_gateway import (
    FakePedagogicalModelGateway,
)
from tests.test_application.fakes.tutoring.fake_student_model_gateway import (
    FakeStudentModelGateway,
)
from tests.test_application.fakes.tutoring.in_memory_tutor_session_repository import (
    InMemoryTutorSessionRepository,
)
from tests.test_application.test_learning.test_get_learning_snapshot import (
    _five_answers,
    _record_quiz_use_case,
)
from application.tutoring.use_cases.send_chat_message import FIRST_MESSAGE_CANNED_RESPONSE
from tests.test_application.test_tutoring.test_send_chat_message import (
    _request,
    _send_chat_use_case,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


class _FailingPedagogicalModelGateway(PedagogicalModelGateway):
    def select_move(self, interpretation, *, turn_context):
        raise LlmGatewayError("Pedagogical model failed in test")


class TestSendChatMessagePipelineIntegration:
    """SendChatMessage が RunTutoringPipeline を経由する受入基準。"""

    def test_first_message_composes_sessions_and_calls_pipeline(self) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        interface = FakeInterfaceModelGateway(response="assistant reply")
        student = FakeStudentModelGateway()
        pedagogical = FakePedagogicalModelGateway()
        use_case = _send_chat_use_case(
            tutor_repository=tutor_repo,
            student_model=student,
            pedagogical_model=pedagogical,
            interface_model=interface,
        )

        result = use_case.execute(_request(user_message="初回メッセージ"))

        assert isinstance(result, Ok)
        assert result.value.tutor_session_id == TutorSessionId("ts-1")
        assert result.value.assistant_content == "assistant reply"
        assert result.value.user_message_id == MessageId("msg-1")
        assert result.value.assistant_message_id == MessageId("msg-2")
        assert len(student.interpret_calls) == 1
        assert len(pedagogical.select_move_calls) == 1
        assert len(interface.generate_calls) == 1

    def test_normal_message_calls_pipeline_three_stages(self) -> None:
        student = FakeStudentModelGateway()
        pedagogical = FakePedagogicalModelGateway()
        interface = FakeInterfaceModelGateway(response="pipeline reply")
        use_case = _send_chat_use_case(
            student_model=student,
            pedagogical_model=pedagogical,
            interface_model=interface,
        )

        result = use_case.execute(_request(user_message="小テストについて"))

        assert isinstance(result, Ok)
        assert result.value.assistant_content == "pipeline reply"
        assert len(student.interpret_calls) == 1
        assert len(pedagogical.select_move_calls) == 1
        assert len(interface.generate_calls) == 1

    def test_digits_only_first_message_returns_canned_response_without_pipeline(self) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        student = FakeStudentModelGateway()
        pedagogical = FakePedagogicalModelGateway()
        interface = FakeInterfaceModelGateway()
        use_case = _send_chat_use_case(
            tutor_repository=tutor_repo,
            student_model=student,
            pedagogical_model=pedagogical,
            interface_model=interface,
        )

        result = use_case.execute(_request(user_message="12345"))

        assert isinstance(result, Ok)
        assert result.value.assistant_content == FIRST_MESSAGE_CANNED_RESPONSE
        assert student.interpret_calls == []
        assert pedagogical.select_move_calls == []
        assert interface.generate_calls == []

    def test_snapshot_quiz_answers_are_passed_to_student_model(self) -> None:
        from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
            InMemoryLearningSessionRepository,
        )

        learning_repo = InMemoryLearningSessionRepository()
        record_quiz = _record_quiz_use_case(learning_repo)
        record_result = record_quiz.execute(
            RecordQuizAttemptRequest(
                learner_id=_request().learner_id,
                lecture_id=_request().lecture_id,
                attempted_at=FIXED_NOW,
                score_numerator=4,
                score_denominator=5,
                answers=_five_answers(wrong_at=3),
            )
        )
        assert isinstance(record_result, Ok)

        student = FakeStudentModelGateway()
        use_case = _send_chat_use_case(
            learning_repository=learning_repo,
            student_model=student,
        )

        result = use_case.execute(_request(user_message="小テストについて"))

        assert isinstance(result, Ok)
        assert len(student.interpret_calls) == 1
        snapshot = student.interpret_calls[0].snapshot
        assert isinstance(snapshot, LearningSnapshot)
        assert len(snapshot.quiz_answers) == 5
        assert snapshot.quiz_answers[2].question_index == 3
        assert snapshot.quiz_answers[2].is_correct is False

    def test_llm_failure_does_not_persist_messages(self) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        use_case = _send_chat_use_case(
            tutor_repository=tutor_repo,
            pedagogical_model=_FailingPedagogicalModelGateway(),
        )

        result = use_case.execute(_request(user_message="LLM 失敗テスト"))

        assert isinstance(result, Err)
        assert isinstance(result.error, LlmGatewayError)
        assert result.error.code == ErrorCode.LLM_GATEWAY_ERROR
        assert tutor_repo.save_count == 1
        saved = tutor_repo.all_sessions()[0]
        assert saved.messages == ()

    def test_second_message_reuses_persisted_state_card(self) -> None:
        from tests.test_application.fakes.tutoring.fake_student_model_gateway import (
            sample_updated_state_card,
        )

        updated_card = sample_updated_state_card()
        student = FakeStudentModelGateway(state_card=updated_card)
        interface = FakeInterfaceModelGateway(response="first reply")
        use_case = _send_chat_use_case(
            student_model=student,
            interface_model=interface,
        )

        first = use_case.execute(_request(user_message="1通目"))
        interface.set_response("second reply")
        assert isinstance(first, Ok)

        second = use_case.execute(
            _request(
                user_message="2通目",
                tutor_session_id=str(first.value.tutor_session_id),
            )
        )

        assert isinstance(second, Ok)
        assert len(student.interpret_calls) == 2
        assert student.interpret_calls[1].previous_state_card == updated_card

    def test_second_message_appends_to_existing_tutor_session(self) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        interface = FakeInterfaceModelGateway(response="first reply")
        use_case = _send_chat_use_case(
            tutor_repository=tutor_repo,
            interface_model=interface,
        )

        first = use_case.execute(_request(user_message="1通目"))
        interface.set_response("second reply")
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
        assert tutor_repo.save_count == 3

        saved = tutor_repo.find_by_id(first.value.tutor_session_id)
        assert saved is not None
        assert len(saved.messages) == 4
        assert saved.messages[2].content == "2通目"
        assert saved.messages[3].content == "second reply"


class _FailingStudentModelGateway(StudentModelGateway):
    def interpret(self, snapshot, messages, user_message, lecture, previous_state_card):
        raise LlmGatewayError("Student model failed in test")


class _FailingInterfaceModelGateway(InterfaceModelGateway):
    def generate(
        self, decision, interpretation, snapshot, messages, user_message, lecture
    ):
        raise LlmGatewayError("Interface model failed in test")


class TestSendChatMessagePipelineStageFailures:
    """各 Stage 失敗時に Message が永続化されない。"""

    def test_student_model_failure_does_not_persist_messages(self) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        use_case = _send_chat_use_case(
            tutor_repository=tutor_repo,
            student_model=_FailingStudentModelGateway(),
        )

        result = use_case.execute(_request(user_message="失敗テスト"))

        assert isinstance(result, Err)
        assert tutor_repo.save_count == 1
        assert tutor_repo.all_sessions()[0].messages == ()

    def test_interface_model_failure_does_not_persist_messages(self) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        use_case = _send_chat_use_case(
            tutor_repository=tutor_repo,
            interface_model=_FailingInterfaceModelGateway(),
        )

        result = use_case.execute(_request(user_message="失敗テスト"))

        assert isinstance(result, Err)
        assert tutor_repo.save_count == 1
        assert tutor_repo.all_sessions()[0].messages == ()
