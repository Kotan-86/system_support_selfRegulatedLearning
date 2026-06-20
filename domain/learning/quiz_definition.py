# 仕様: docs/spec/domain-model.md#Value Object（Learning）
# 仕様: docs/spec/domain-implementation-plan.md Phase 1
"""Learning コンテキストの小テスト定義 Value Object。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    """小テストの設問（仕様: index, text, choices, correctAnswer）。"""

    index: int
    text: str
    choices: tuple[str, ...]
    correct_answer: str

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("Question text must not be empty")


@dataclass(frozen=True)
class QuizDefinition:
    """講義に紐づく小テスト定義。"""

    questions: tuple[Question, ...]

    def __post_init__(self) -> None:
        if len(self.questions) < 1:
            raise ValueError("QuizDefinition must have at least one question")

        indexes = [question.index for question in self.questions]
        if len(indexes) != len(set(indexes)):
            raise ValueError("Question index must be unique within QuizDefinition")
