# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
"""ChatPromptBuilder Port の具象実装。"""
from __future__ import annotations

from application.tutoring.ports.chat_prompt_builder import ChatPromptBuilder
from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.message import Message

from interfaces.tutoring.context_formatters import (
    HISTORY_EMPTY_PLACEHOLDER,
    format_history,
    format_lecture_log,
    format_lecture_transcript,
    format_quiz_result,
)
from interfaces.tutoring.prompts import SYSTEM_PROMPT


class DefaultChatPromptBuilder(ChatPromptBuilder):
    """LearningSnapshot と対話履歴から LLM プロンプト文字列を組み立てる。"""

    def build(
        self,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
    ) -> str:
        history_str = format_history(messages)
        return SYSTEM_PROMPT.format(
            history=history_str or HISTORY_EMPTY_PLACEHOLDER,
            user_message=user_message,
            lecture_log=format_lecture_log(snapshot),
            quiz_result=format_quiz_result(snapshot, lecture),
            lecture_transcript=format_lecture_transcript(snapshot, lecture),
        )
