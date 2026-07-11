# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
"""InterfaceModelPromptBuilder の Stage 3 プロンプト注入テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from domain.learning.learning_snapshot import LearningSnapshot
from domain.shared.ids import (
    LearnerId,
    LearningSessionId,
    LectureId,
    MessageId,
)
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.dialogue_move_decision import (
    DialogueMoveDecision,
    ResponseBudget,
    ScaffoldingLevel,
)
from domain.tutoring.message import Message, MessageRole
from interfaces.tutoring.interface_model_prompt_builder import (
    InterfaceModelPromptBuilder,
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


def _decision(*, budget: ResponseBudget) -> DialogueMoveDecision:
    return DialogueMoveDecision(
        dialogue_move=DialogueMove.JOINT_EVIDENCE_CHECK,
        response_budget=budget,
        interface_instructions="選択肢一覧を提示する",
    )


class TestInterfaceModelPromptBuilder:
    """Stage 3 プロンプトへの動的 Response Budget 注入。"""

    def test_high_scaffolding_uses_strict_budget_template(self) -> None:
        prompt = InterfaceModelPromptBuilder().build(
            _decision(
                budget=ResponseBudget(
                    max_sentences=5,
                    max_questions=1,
                    scaffolding_level=ScaffoldingLevel.HIGH,
                )
            ),
            snapshot=_empty_snapshot(),
            messages=(),
            user_message="続きを教えて",
            lecture=_lecture(),
        )

        assert "足場かけ強度: HIGH（厳格）" in prompt
        assert "4文以内" in prompt
        assert "問いは1つだけ" in prompt
        assert "* scaffolding_level: high" in prompt
        assert "* allow_composite_turn: false" in prompt

    def test_medium_composite_budget_includes_pattern(self) -> None:
        prompt = InterfaceModelPromptBuilder().build(
            _decision(
                budget=ResponseBudget(
                    max_sentences=6,
                    max_questions=1,
                    scaffolding_level=ScaffoldingLevel.MEDIUM,
                    allow_composite_turn=True,
                    composite_pattern="CONFIRM_AND_ADVANCE",
                )
            ),
            snapshot=_empty_snapshot(),
            messages=(),
            user_message="続きを教えて",
            lecture=_lecture(),
        )

        assert "足場かけ強度: MEDIUM（複合発話可）" in prompt
        assert "複合パターン: CONFIRM_AND_ADVANCE" in prompt
        assert "修辞的確認は問いカウントに含めない" in prompt
        assert "6文以内" in prompt
        assert "* scaffolding_level: medium" in prompt
        assert "* allow_composite_turn: true" in prompt

    def test_standard_budget_reflects_variable_limits(self) -> None:
        prompt = InterfaceModelPromptBuilder().build(
            _decision(
                budget=ResponseBudget(
                    max_sentences=3,
                    max_questions=0,
                    scaffolding_level=ScaffoldingLevel.LOW,
                )
            ),
            snapshot=_empty_snapshot(),
            messages=(
                Message.create(
                    id=MessageId("msg-1"),
                    role=MessageRole.USER,
                    content="前の質問",
                    created_at=FIXED_NOW,
                ),
            ),
            user_message="続きを教えて",
            lecture=_lecture(),
        )

        assert "足場かけ強度: low" in prompt
        assert "3文以内" in prompt
        assert "問いは0個まで" in prompt

    def test_includes_evidence_to_surface(self) -> None:
        prompt = InterfaceModelPromptBuilder().build(
            DialogueMoveDecision(
                dialogue_move=DialogueMove.DATA_CHECK,
                response_budget=ResponseBudget(
                    max_sentences=4,
                    max_questions=1,
                    scaffolding_level=ScaffoldingLevel.MEDIUM,
                ),
                interface_instructions="LADログを提示する",
                evidence_to_surface=("lad_log_timeline", "quiz_q1_choices"),
            ),
            snapshot=_empty_snapshot(),
            messages=(),
            user_message="続きを教えて",
            lecture=_lecture(),
        )

        assert "* 提示必須の証拠: lad_log_timeline, quiz_q1_choices" in prompt
        assert "## Evidence Surfacing Rule" in prompt
        assert "`lad_log`, `lad_log_*`, `lad_digest`" in prompt
        assert "`quiz_q*`" in prompt
        assert "`transcript_*`" in prompt

    def test_empty_evidence_to_surface_uses_placeholder(self) -> None:
        prompt = InterfaceModelPromptBuilder().build(
            _decision(
                budget=ResponseBudget(
                    max_sentences=4,
                    max_questions=1,
                    scaffolding_level=ScaffoldingLevel.MEDIUM,
                )
            ),
            snapshot=_empty_snapshot(),
            messages=(),
            user_message="続きを教えて",
            lecture=_lecture(),
        )

        assert "* 提示必須の証拠: (なし)" in prompt
