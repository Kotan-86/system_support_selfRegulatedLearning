# 仕様: docs/spec/application-usecase.md#RunTutoringPipeline
"""RunTutoringPipelineUseCase の受入基準テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.common.errors import ErrorCode, LlmGatewayError
from application.common.result import Err, Ok
from application.tutoring.dto.tutoring_pipeline import TutoringPipelineRequest
from application.tutoring.ports.interface_model_gateway import InterfaceModelGateway
from application.tutoring.ports.pedagogical_model_gateway import PedagogicalModelGateway
from application.tutoring.ports.student_model_gateway import StudentModelGateway
from application.tutoring.use_cases.run_tutoring_pipeline import RunTutoringPipelineUseCase
from domain.learning.learning_snapshot import LearningSnapshot
from domain.shared.ids import LectureId, LearnerId, LearningSessionId, MessageId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.interpretation_state import InterpretationStateCard
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from domain.tutoring.message import Message, MessageRole
from tests.test_application.fakes.tutoring.fake_interface_model_gateway import (
    FakeInterfaceModelGateway,
)
from tests.test_application.fakes.tutoring.fake_pedagogical_model_gateway import (
    FakePedagogicalModelGateway,
)
from tests.test_application.fakes.tutoring.fake_student_model_gateway import (
    FakeStudentModelGateway,
    sample_updated_state_card,
)
from tests.test_application.test_learning.test_get_learning_snapshot import (
    _five_answers,
    _get_snapshot_use_case,
    _lecture,
    _record_quiz_use_case,
)
from application.learning.dto.record_quiz_attempt import RecordQuizAttemptRequest
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _pipeline_use_case(
    *,
    student: FakeStudentModelGateway | None = None,
    pedagogical: FakePedagogicalModelGateway | None = None,
    interface: FakeInterfaceModelGateway | None = None,
) -> RunTutoringPipelineUseCase:
    return RunTutoringPipelineUseCase(
        student_model=student or FakeStudentModelGateway(),
        pedagogical_model=pedagogical or FakePedagogicalModelGateway(),
        interface_model=interface or FakeInterfaceModelGateway(),
    )


def _empty_snapshot() -> LearningSnapshot:
    return LearningSnapshot(
        session_id=LearningSessionId("ls-1"),
        learner_id=LearnerId("learner-1"),
        lecture_id=LectureId("lecture-1"),
        viewing_events=(),
        latest_quiz_attempt=None,
        quiz_answers=(),
    )


def _request(
    *,
    user_message: str = "小テストについて",
    snapshot: LearningSnapshot | None = None,
    messages: tuple[Message, ...] = (),
    previous_state_card: InterpretationStateCard | None = None,
) -> TutoringPipelineRequest:
    return TutoringPipelineRequest(
        snapshot=snapshot or _empty_snapshot(),
        messages=messages,
        user_message=user_message,
        lecture=_lecture(),
        previous_state_card=previous_state_card,
    )


def _assistant_message(*, content: str = "前ターンの応答") -> Message:
    return Message.create(
        id=MessageId("msg-asst-1"),
        role=MessageRole.ASSISTANT,
        content=content,
        created_at=FIXED_NOW,
    )


def _user_message_entity(*, content: str = "1通目") -> Message:
    return Message.create(
        id=MessageId("msg-user-1"),
        role=MessageRole.USER,
        content=content,
        created_at=FIXED_NOW,
    )


class TestTutoringPipelineStageOrder:
    """interpret → select_move → generate の順序と各 1 回。"""

    def test_pipeline_calls_three_stages_in_order(self) -> None:
        student = FakeStudentModelGateway()
        pedagogical = FakePedagogicalModelGateway()
        interface = FakeInterfaceModelGateway(response="pipeline reply")
        use_case = _pipeline_use_case(
            student=student,
            pedagogical=pedagogical,
            interface=interface,
        )

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert result.value.assistant_text == "pipeline reply"
        assert len(student.interpret_calls) == 1
        assert len(pedagogical.select_move_calls) == 1
        assert len(interface.generate_calls) == 1
        interpretation = pedagogical.select_move_calls[0].interpretation
        decision = interface.generate_calls[0].decision
        assert interpretation.utterance_type is LearnerUtteranceType.VAGUE_MEMORY
        assert decision.dialogue_move is DialogueMove.JOINT_EVIDENCE_CHECK


class TestTutoringPipelineSnapshotIntegration:
    """Stage 1 interpret() に Snapshot（quiz_answers 含む）が渡る。"""

    def test_snapshot_quiz_answers_are_passed_to_student_model(self) -> None:
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

        from application.learning.dto.get_learning_snapshot import GetLearningSnapshotRequest

        snapshot_uc = _get_snapshot_use_case(repository=learning_repo)
        snapshot_result = snapshot_uc.execute(
            GetLearningSnapshotRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
            )
        )
        assert isinstance(snapshot_result, Ok)
        snapshot = snapshot_result.value.snapshot

        student = FakeStudentModelGateway()
        use_case = _pipeline_use_case(student=student)
        result = use_case.execute(_request(snapshot=snapshot))

        assert isinstance(result, Ok)
        assert len(student.interpret_calls) == 1
        passed_snapshot = student.interpret_calls[0].snapshot
        assert isinstance(passed_snapshot, LearningSnapshot)
        assert len(passed_snapshot.quiz_answers) == 5
        assert passed_snapshot.quiz_answers[2].question_index == 3
        assert passed_snapshot.quiz_answers[2].is_correct is False


class TestTutoringPipelineStateCardCarryover:
    """2 ターン目に previous_state_card が Stage 1 へ渡る。"""

    def test_second_turn_passes_previous_state_card_to_interpret(self) -> None:
        updated_card = sample_updated_state_card()
        student = FakeStudentModelGateway(state_card=updated_card)
        use_case = _pipeline_use_case(student=student)

        first = use_case.execute(_request(user_message="1通目"))
        assert isinstance(first, Ok)
        assert first.value.interpretation.state_card == updated_card

        second = use_case.execute(
            _request(
                user_message="2通目",
                messages=(_user_message_entity(), _assistant_message()),
                previous_state_card=first.value.interpretation.state_card,
            )
        )

        assert isinstance(second, Ok)
        assert len(student.interpret_calls) == 2
        assert student.interpret_calls[1].previous_state_card == updated_card


class TestTutoringPipelineTurnContext:
    """TurnContext の is_first_assistant_turn。"""

    def test_first_turn_has_is_first_assistant_turn_true(self) -> None:
        pedagogical = FakePedagogicalModelGateway()
        use_case = _pipeline_use_case(pedagogical=pedagogical)

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert pedagogical.select_move_calls[0].turn_context.is_first_assistant_turn is True

    def test_second_turn_has_is_first_assistant_turn_false(self) -> None:
        pedagogical = FakePedagogicalModelGateway()
        use_case = _pipeline_use_case(pedagogical=pedagogical)

        result = use_case.execute(
            _request(
                messages=(_user_message_entity(), _assistant_message()),
            )
        )

        assert isinstance(result, Ok)
        assert pedagogical.select_move_calls[0].turn_context.is_first_assistant_turn is False


class TestTutoringPipelineMetadata:
    """TutoringPipelineResult に interpretation / decision が含まれる。"""

    def test_result_includes_interpretation_and_decision(self) -> None:
        student = FakeStudentModelGateway(
            utterance_type=LearnerUtteranceType.FACT_REQUEST,
        )
        pedagogical = FakePedagogicalModelGateway(
            dialogue_move=DialogueMove.ORIENT_SHARED_REVIEW,
        )
        use_case = _pipeline_use_case(student=student, pedagogical=pedagogical)

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert (
            result.value.interpretation.utterance_type
            is LearnerUtteranceType.FACT_REQUEST
        )
        assert (
            result.value.decision.dialogue_move
            is DialogueMove.ORIENT_SHARED_REVIEW
        )


class _FailingStudentModelGateway(StudentModelGateway):
    def interpret(self, snapshot, messages, user_message, lecture, previous_state_card):
        raise LlmGatewayError("Student model failed in test")


class _FailingPedagogicalModelGateway(PedagogicalModelGateway):
    def select_move(self, interpretation, *, turn_context):
        raise LlmGatewayError("Pedagogical model failed in test")


class _FailingInterfaceModelGateway(InterfaceModelGateway):
    def generate(
        self, decision, interpretation, snapshot, messages, user_message, lecture
    ):
        raise LlmGatewayError("Interface model failed in test")


class _EmptyInterfaceModelGateway(InterfaceModelGateway):
    def generate(
        self, decision, interpretation, snapshot, messages, user_message, lecture
    ):
        return ""


class TestTutoringPipelineErrors:
    """Stage 1/2/3 の LlmGatewayError と空応答。"""

    def test_student_model_failure_returns_err(self) -> None:
        use_case = _pipeline_use_case(student=_FailingStudentModelGateway())
        result = use_case.execute(_request())

        assert isinstance(result, Err)
        assert isinstance(result.error, LlmGatewayError)
        assert result.error.code == ErrorCode.LLM_GATEWAY_ERROR

    def test_pedagogical_model_failure_returns_err(self) -> None:
        use_case = _pipeline_use_case(pedagogical=_FailingPedagogicalModelGateway())
        result = use_case.execute(_request())

        assert isinstance(result, Err)
        assert isinstance(result.error, LlmGatewayError)

    def test_interface_model_failure_returns_err(self) -> None:
        use_case = _pipeline_use_case(interface=_FailingInterfaceModelGateway())
        result = use_case.execute(_request())

        assert isinstance(result, Err)
        assert isinstance(result.error, LlmGatewayError)

    def test_empty_interface_response_returns_err(self) -> None:
        use_case = _pipeline_use_case(interface=_EmptyInterfaceModelGateway())
        result = use_case.execute(_request())

        assert isinstance(result, Err)
        assert isinstance(result.error, LlmGatewayError)
