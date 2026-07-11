# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
"""ITS Interface Model（Stage 3）プロンプト組み立て。"""
from __future__ import annotations

from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.dialogue_move_decision import DialogueMoveDecision
from domain.tutoring.message import Message

from interfaces.tutoring.context_formatters import (
    HISTORY_EMPTY_PLACEHOLDER,
    format_evidence_list,
    format_history,
    format_lad_digest,
    format_lecture_outline,
    format_lecture_transcript,
    format_quiz_result,
)
from interfaces.tutoring.prompts.interface_model import (
    INTERFACE_MODEL_PROMPT,
    format_response_budget_section,
)


class InterfaceModelPromptBuilder:
    """Dialogue Move 決定とコンテキストから Stage 3 プロンプト文字列を組み立てる。"""

    def build(
        self,
        decision: DialogueMoveDecision,
        *,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
    ) -> str:
        history_str = format_history(messages)
        return INTERFACE_MODEL_PROMPT.format(
            response_budget_section=format_response_budget_section(
                decision.response_budget
            ),
            history=history_str or HISTORY_EMPTY_PLACEHOLDER,
            user_message=user_message,
            lecture_log=format_lad_digest(snapshot, lecture),
            quiz_result=format_quiz_result(snapshot, lecture),
            lecture_transcript=format_lecture_transcript(snapshot, lecture),
            lecture_outline=format_lecture_outline(lecture.outline),
            dialogue_move=decision.dialogue_move.value,
            evidence_to_surface=format_evidence_list(decision.evidence_to_surface),
            interface_instructions=decision.interface_instructions,
            scaffolding_level=decision.response_budget.scaffolding_level.value,
            allow_composite_turn=str(
                decision.response_budget.allow_composite_turn
            ).lower(),
        )
