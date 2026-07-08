# 仕様: docs/spec/application-usecase.md#InterfaceModelGateway
# 仕様: docs/spec/framework-drivers-layer.md#Port-対応表
"""LlmGateway を用いた InterfaceModelGateway 実装。"""
from __future__ import annotations

from application.common.errors import LlmGatewayError
from application.tutoring.ports.interface_model_gateway import InterfaceModelGateway
from application.tutoring.ports.llm_gateway import LlmGateway
from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.dialogue_move_decision import DialogueMoveDecision
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from domain.tutoring.message import Message
from interfaces.tutoring.interface_model_prompt_builder import InterfaceModelPromptBuilder


class LlmInterfaceModelGateway(InterfaceModelGateway):
    """Stage 3: 指定 Move に従い学習者向け発話を生成する。"""

    def __init__(
        self,
        llm_gateway: LlmGateway,
        prompt_builder: InterfaceModelPromptBuilder | None = None,
    ) -> None:
        self._llm_gateway = llm_gateway
        self._prompt_builder = prompt_builder or InterfaceModelPromptBuilder()

    def generate(
        self,
        decision: DialogueMoveDecision,
        interpretation: LearnerInterpretationResult,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
    ) -> str:
        del interpretation
        prompt = self._prompt_builder.build(
            decision,
            snapshot=snapshot,
            messages=messages,
            user_message=user_message,
            lecture=lecture,
        )
        try:
            return self._llm_gateway.generate(prompt)
        except LlmGatewayError:
            raise
        except Exception as exc:
            raise LlmGatewayError(f"Interface model failed: {exc}") from exc
