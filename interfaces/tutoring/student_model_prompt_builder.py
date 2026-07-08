# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
"""ITS Student Model（Stage 1）プロンプト組み立て。"""
from __future__ import annotations

from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.interpretation_state import InterpretationStateCard
from domain.tutoring.message import Message

from interfaces.tutoring.context_formatters import (
    HISTORY_EMPTY_PLACEHOLDER,
    format_history,
    format_lecture_log,
    format_lecture_outline,
    format_lecture_transcript,
    format_quiz_result,
)
from interfaces.tutoring.prompts.student_model import STUDENT_MODEL_PROMPT
from interfaces.tutoring.tutoring_model_json import format_state_card_json


class StudentModelPromptBuilder:
    """LearningSnapshot と対話履歴から Stage 1 プロンプト文字列を組み立てる。"""

    def build(
        self,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
        previous_state_card: InterpretationStateCard | None = None,
    ) -> str:
        history_str = format_history(messages)
        state_card = previous_state_card or InterpretationStateCard.empty()
        return STUDENT_MODEL_PROMPT.format(
            history=history_str or HISTORY_EMPTY_PLACEHOLDER,
            user_message=user_message,
            lecture_log=format_lecture_log(snapshot),
            quiz_result=format_quiz_result(snapshot, lecture),
            lecture_transcript=format_lecture_transcript(snapshot, lecture),
            lecture_outline=format_lecture_outline(lecture.outline),
        ) + (
            "\n\n## 前ターンの Interpretation State Card\n"
            f"{format_state_card_json(state_card)}\n"
        )
