# 仕様: docs/spec/application-usecase.md#ChatPromptBuilder（interfaces 層 ACL・Port）
"""ChatPromptBuilder の Fake 実装（テスト用）。"""
from __future__ import annotations

from dataclasses import dataclass

from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.message import Message

from application.tutoring.ports.chat_prompt_builder import ChatPromptBuilder


@dataclass(frozen=True)
class PromptBuildCall:
    """build 呼び出しの記録。"""

    snapshot: LearningSnapshot
    messages: tuple[Message, ...]
    user_message: str
    lecture: Lecture


class FakeChatPromptBuilder(ChatPromptBuilder):
    """プロンプト内容を記録し、固定文字列を返す Fake ChatPromptBuilder。"""

    def __init__(self, *, prompt: str = "fake-prompt") -> None:
        self._prompt = prompt
        self.build_calls: list[PromptBuildCall] = []

    def build(
        self,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
    ) -> str:
        self.build_calls.append(
            PromptBuildCall(
                snapshot=snapshot,
                messages=messages,
                user_message=user_message,
                lecture=lecture,
            )
        )
        return self._prompt

    def set_prompt(self, prompt: str) -> None:
        """テスト用: 返却するプロンプト文字列を変更する。"""
        self._prompt = prompt
