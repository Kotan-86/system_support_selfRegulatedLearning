# 仕様: docs/spec/application-usecase.md#PedagogicalModelGateway
# 仕様: docs/spec/framework-drivers-layer.md#Port-対応表
"""LlmGateway を用いた PedagogicalModelGateway 実装。"""
from __future__ import annotations

from application.common.errors import LlmGatewayError
from application.tutoring.dto.tutoring_pipeline import TurnContext
from application.tutoring.ports.llm_gateway import LlmGateway
from application.tutoring.ports.pedagogical_model_gateway import PedagogicalModelGateway
from domain.tutoring.dialogue_move_decision import DialogueMoveDecision
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from interfaces.tutoring.pedagogical_model_prompt_builder import (
    PedagogicalModelPromptBuilder,
)
from interfaces.tutoring.tutoring_model_json import parse_pedagogical_model_output


class LlmPedagogicalModelGateway(PedagogicalModelGateway):
    """Stage 2: 解釈結果から Dialogue Move を選択する。"""

    def __init__(
        self,
        llm_gateway: LlmGateway,
        prompt_builder: PedagogicalModelPromptBuilder | None = None,
    ) -> None:
        self._llm_gateway = llm_gateway
        self._prompt_builder = prompt_builder or PedagogicalModelPromptBuilder()

    def select_move(
        self,
        interpretation: LearnerInterpretationResult,
        *,
        turn_context: TurnContext,
    ) -> DialogueMoveDecision:
        prompt = self._prompt_builder.build(
            interpretation,
            is_first_assistant_turn=turn_context.is_first_assistant_turn,
            lecture_outline=turn_context.lecture.outline,
        )
        try:
            payload = self._llm_gateway.generate_json(prompt)
        except LlmGatewayError:
            raise
        except Exception as exc:
            raise LlmGatewayError(f"Pedagogical model JSON parse failed: {exc}") from exc
        try:
            return parse_pedagogical_model_output(payload)
        except LlmGatewayError:
            raise
        except Exception as exc:
            raise LlmGatewayError(f"Pedagogical model output invalid: {exc}") from exc
