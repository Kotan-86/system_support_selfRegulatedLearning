# 仕様: docs/spec/application-usecase.md#PedagogicalModelGateway
"""LlmPedagogicalModelGateway の単体テスト（LLM はモック）。"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from application.tutoring.dto.tutoring_pipeline import TurnContext
from application.tutoring.ports.llm_gateway import LlmGateway
from domain.learning.learning_snapshot import LearningSnapshot
from domain.shared.ids import LectureId, LearnerId, LearningSessionId, MessageId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.interpretation_state import InterpretationStateCard
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from domain.tutoring.message import Message, MessageRole
from framework_drivers.external.vertex.llm_pedagogical_model_gateway import (
    LlmPedagogicalModelGateway,
)
from interfaces.tutoring.pedagogical_model_prompt_builder import (
    PedagogicalModelPromptBuilder,
)
from tests.test_application.test_learning.test_get_learning_snapshot import _lecture

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _empty_snapshot() -> LearningSnapshot:
    return LearningSnapshot(
        session_id=LearningSessionId("session-1"),
        learner_id=LearnerId("learner-1"),
        lecture_id=LectureId("lecture-1"),
        viewing_events=(),
        latest_quiz_attempt=None,
        quiz_answers=(),
    )


class _FakeLlmGateway(LlmGateway):
    def __init__(self, *, payload: dict) -> None:
        self._payload = payload
        self.last_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    def generate_json(self, prompt: str, schema_hint: str | None = None) -> dict:
        self.last_prompt = prompt
        return self._payload


def _interpretation() -> LearnerInterpretationResult:
    return LearnerInterpretationResult(
        utterance_type=LearnerUtteranceType.VAGUE_MEMORY,
        state_card=InterpretationStateCard.empty(),
    )


def _turn_context_with_history() -> TurnContext:
    messages = (
        Message.create(
            id=MessageId("msg-user"),
            role=MessageRole.USER,
            content="質問",
            created_at=FIXED_NOW,
        ),
        Message.create(
            id=MessageId("msg-asst"),
            role=MessageRole.ASSISTANT,
            content="応答",
            created_at=FIXED_NOW,
            dialogue_move=DialogueMove.ORIENT_SHARED_REVIEW,
        ),
    )
    return TurnContext.from_messages(
        messages, lecture=_lecture(), snapshot=_empty_snapshot()
    )


class TestLlmPedagogicalModelGateway:
    """TurnContext / Snapshot を prompt builder に渡し、拡張 response_budget をパースする。"""

    def test_select_move_passes_turn_context_and_snapshot_to_prompt_builder(self) -> None:
        llm = _FakeLlmGateway(
            payload={
                "dialogue_move": "ELICIT_REASON",
                "response_budget": {
                    "max_sentences": 4,
                    "max_questions": 1,
                    "scaffolding_level": "medium",
                    "allow_composite_turn": True,
                    "composite_pattern": "CONFIRM_AND_ADVANCE",
                },
                "interface_instructions": "理由を聞く",
            }
        )
        builder = MagicMock(spec=PedagogicalModelPromptBuilder)
        builder.build.return_value = "pedagogical prompt"
        gateway = LlmPedagogicalModelGateway(llm, prompt_builder=builder)
        turn_context = _turn_context_with_history()
        interpretation = _interpretation()
        snapshot = _empty_snapshot()

        decision = gateway.select_move(
            interpretation,
            snapshot=snapshot,
            turn_context=turn_context,
        )

        builder.build.assert_called_once_with(
            interpretation,
            snapshot=snapshot,
            turn_context=turn_context,
        )
        assert decision.dialogue_move is DialogueMove.ELICIT_REASON
        assert decision.response_budget.scaffolding_level.value == "medium"
        assert decision.response_budget.allow_composite_turn is True
        assert decision.response_budget.composite_pattern == "CONFIRM_AND_ADVANCE"

    def test_select_move_includes_move_history_in_prompt(self) -> None:
        llm = _FakeLlmGateway(
            payload={
                "dialogue_move": "ELICIT_REASON",
                "response_budget": {"max_sentences": 4, "max_questions": 1},
                "interface_instructions": "理由を聞く",
            }
        )
        gateway = LlmPedagogicalModelGateway(llm)
        turn_context = _turn_context_with_history()

        gateway.select_move(
            _interpretation(),
            snapshot=_empty_snapshot(),
            turn_context=turn_context,
        )

        assert llm.last_prompt is not None
        assert "## Recent Coach Move History" in llm.last_prompt
        assert '"dialogue_move": "ORIENT_SHARED_REVIEW"' in llm.last_prompt
