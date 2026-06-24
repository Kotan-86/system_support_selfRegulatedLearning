# 仕様: docs/spec/application-usecase.md#ChatPromptBuilder（interfaces 層 ACL・Port）
"""LLM 向けプロンプト組み立て Port。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.message import Message


class ChatPromptBuilder(ABC):
    """LearningSnapshot と対話履歴から LLM プロンプト文字列を組み立てる。"""

    @abstractmethod
    def build(
        self,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
    ) -> str:
        """LLM へ渡すプロンプト文字列を返す。"""
