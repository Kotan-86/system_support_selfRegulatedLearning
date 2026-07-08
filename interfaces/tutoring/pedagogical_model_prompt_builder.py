# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
"""ITS Pedagogical Model（Stage 2）プロンプト組み立て。"""
from __future__ import annotations

from domain.learning.lecture_outline import LectureOutline
from domain.tutoring.learner_interpretation import LearnerInterpretationResult

from interfaces.tutoring.context_formatters import format_lecture_outline
from interfaces.tutoring.prompts.pedagogical_model import PEDAGOGICAL_MODEL_PROMPT
from interfaces.tutoring.tutoring_model_json import format_state_card_json


class PedagogicalModelPromptBuilder:
    """Student Model 出力と TurnContext から Stage 2 プロンプト文字列を組み立てる。"""

    def build(
        self,
        interpretation: LearnerInterpretationResult,
        *,
        is_first_assistant_turn: bool,
        lecture_outline: LectureOutline,
    ) -> str:
        return PEDAGOGICAL_MODEL_PROMPT.format(
            lecture_outline=format_lecture_outline(lecture_outline),
        ) + (
            "\n\n## Student Model 出力\n"
            f"* utterance_type: {interpretation.utterance_type.value}\n"
            f"* is_first_assistant_turn: {is_first_assistant_turn}\n"
            f"* interpretation_state:\n{format_state_card_json(interpretation.state_card)}\n"
        )
