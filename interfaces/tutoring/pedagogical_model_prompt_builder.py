# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
"""ITS Pedagogical Model（Stage 2）プロンプト組み立て。"""
from __future__ import annotations

from application.tutoring.dto.tutoring_pipeline import TurnContext
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.learner_interpretation import LearnerInterpretationResult

from interfaces.tutoring.context_formatters import (
    format_evidence_list,
    format_lad_digest,
    format_lecture_outline,
    format_move_history_json,
)
from interfaces.tutoring.prompts.pedagogical_model import PEDAGOGICAL_MODEL_PROMPT
from interfaces.tutoring.tutoring_model_json import format_state_card_json


class PedagogicalModelPromptBuilder:
    """Student Model 出力と TurnContext から Stage 2 プロンプト文字列を組み立てる。"""

    def build(
        self,
        interpretation: LearnerInterpretationResult,
        *,
        snapshot: LearningSnapshot,
        turn_context: TurnContext,
    ) -> str:
        return PEDAGOGICAL_MODEL_PROMPT.format(
            lecture_outline=format_lecture_outline(turn_context.lecture.outline),
        ) + (
            "\n\n## LAD データ要約\n"
            f"{format_lad_digest(snapshot, turn_context.lecture)}\n"
            "\n## Student evidence_references\n"
            f"{format_evidence_list(interpretation.evidence_references)}\n"
            "\n## Student Model 出力\n"
            f"* utterance_type: {interpretation.utterance_type.value}\n"
            f"* is_first_assistant_turn: {turn_context.is_first_assistant_turn}\n"
            f"* turn_index: {turn_context.turn_index}\n"
            f"* has_lad_data: {str(turn_context.has_lad_data).lower()}\n"
            f"* lad_check_pending: {str(turn_context.lad_check_pending).lower()}\n"
            f"* interpretation_state:\n{format_state_card_json(interpretation.state_card)}\n"
            "\n## Recent Coach Move History\n"
            f"{format_move_history_json(turn_context.move_history)}\n"
        )
