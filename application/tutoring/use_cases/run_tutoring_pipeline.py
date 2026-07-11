# 仕様: docs/spec/application-usecase.md#RunTutoringPipeline
"""ITS 3 段パイプライン（Student → Pedagogical → Interface）を実行する。"""
from __future__ import annotations

from application.common.errors import AppError, LlmGatewayError
from application.common.result import Result, err, ok
from application.tutoring.dto.tutoring_pipeline import (
    TutoringPipelineRequest,
    TutoringPipelineResult,
    TurnContext,
)
from application.tutoring.ports.interface_model_gateway import InterfaceModelGateway
from application.tutoring.ports.pedagogical_model_gateway import PedagogicalModelGateway
from application.tutoring.ports.student_model_gateway import StudentModelGateway
from domain.tutoring.interpretation_state import InterpretationStateCard


class RunTutoringPipelineUseCase:
    """Snapshot と対話履歴から 3 段 LLM パイプラインで応答を生成する。"""

    def __init__(
        self,
        student_model: StudentModelGateway,
        pedagogical_model: PedagogicalModelGateway,
        interface_model: InterfaceModelGateway,
    ) -> None:
        self._student_model = student_model
        self._pedagogical_model = pedagogical_model
        self._interface_model = interface_model

    def execute(
        self, request: TutoringPipelineRequest
    ) -> Result[TutoringPipelineResult, AppError]:
        previous_state_card = (
            request.previous_state_card
            if request.previous_state_card is not None
            else InterpretationStateCard.empty()
        )
        turn_context = TurnContext.from_messages(
            request.messages,
            lecture=request.lecture,
            snapshot=request.snapshot,
        )

        try:
            interpretation = self._student_model.interpret(
                request.snapshot,
                request.messages,
                request.user_message,
                request.lecture,
                previous_state_card,
            )
        except LlmGatewayError as error:
            return err(error)
        except Exception as exc:
            return err(LlmGatewayError(f"Student model failed: {exc}"))

        try:
            decision = self._pedagogical_model.select_move(
                interpretation,
                snapshot=request.snapshot,
                turn_context=turn_context,
            )
        except LlmGatewayError as error:
            return err(error)
        except Exception as exc:
            return err(LlmGatewayError(f"Pedagogical model failed: {exc}"))

        try:
            assistant_text = self._interface_model.generate(
                decision,
                interpretation,
                request.snapshot,
                request.messages,
                request.user_message,
                request.lecture,
            )
        except LlmGatewayError as error:
            return err(error)
        except Exception as exc:
            return err(LlmGatewayError(f"Interface model failed: {exc}"))

        if not assistant_text:
            return err(LlmGatewayError("Interface model returned empty response"))

        return ok(
            TutoringPipelineResult(
                assistant_text=assistant_text,
                interpretation=interpretation,
                decision=decision,
            )
        )
