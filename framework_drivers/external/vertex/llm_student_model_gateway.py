# 仕様: docs/spec/application-usecase.md#StudentModelGateway
# 仕様: docs/spec/framework-drivers-layer.md#Port-対応表
"""LlmGateway を用いた StudentModelGateway 実装。"""
from __future__ import annotations

from application.common.errors import LlmGatewayError
from application.tutoring.ports.llm_gateway import LlmGateway
from application.tutoring.ports.student_model_gateway import StudentModelGateway
from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.interpretation_state import InterpretationStateCard
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from domain.tutoring.message import Message
from interfaces.tutoring.student_model_prompt_builder import StudentModelPromptBuilder
from interfaces.tutoring.tutoring_model_json import parse_student_model_output


class LlmStudentModelGateway(StudentModelGateway):
    """Stage 1: プロンプト組み立て + generate_json で学習者状態を診断する。"""

    def __init__(
        self,
        llm_gateway: LlmGateway,
        prompt_builder: StudentModelPromptBuilder | None = None,
    ) -> None:
        self._llm_gateway = llm_gateway
        self._prompt_builder = prompt_builder or StudentModelPromptBuilder()

    def interpret(
        self,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
        previous_state_card: InterpretationStateCard,
    ) -> LearnerInterpretationResult:
        prompt = self._prompt_builder.build(
            snapshot,
            messages,
            user_message,
            lecture,
            previous_state_card=previous_state_card,
        )
        try:
            payload = self._llm_gateway.generate_json(prompt)
        except LlmGatewayError:
            raise
        except Exception as exc:
            raise LlmGatewayError(f"Student model JSON parse failed: {exc}") from exc
        try:
            return parse_student_model_output(payload)
        except LlmGatewayError:
            raise
        except Exception as exc:
            raise LlmGatewayError(f"Student model output invalid: {exc}") from exc
