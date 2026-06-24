# 仕様: docs/spec/domain-model.md#QuizAttempt（小テスト受験）
# 仕様: docs/spec/domain-model.md#QuizAnswer（小テスト回答）
# 仕様: docs/spec/domain-implementation-plan.md Phase 2
"""Learning コンテキストの小テスト受験 Entity。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.shared.ids import QuizAttemptId


@dataclass(frozen=True)
class QuizAnswer:
    """小テスト回答（設問定義は Lecture 側、回答結果のみ保持）。"""

    question_index: int
    selected_answer: str
    is_correct: bool


@dataclass(frozen=True)
class QuizAttempt:
    """小テスト受験 1 回分。"""

    id: QuizAttemptId
    attempted_at: datetime
    score_numerator: int
    score_denominator: int
    answers: tuple[QuizAnswer, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError("Use QuizAttempt.create to construct QuizAttempt")

    @classmethod
    def create(
        cls,
        *,
        id: QuizAttemptId,
        attempted_at: datetime,
        score_numerator: int,
        score_denominator: int,
        answers: tuple[QuizAnswer, ...],
    ) -> QuizAttempt:
        if score_denominator <= 0:
            raise ValueError("score_denominator must be greater than 0")
        if score_numerator < 0 or score_numerator > score_denominator:
            raise ValueError(
                "score_numerator must satisfy 0 <= score_numerator <= score_denominator"
            )
        if len(answers) < 1:
            raise ValueError("QuizAttempt must have at least one answer")

        indexes = [answer.question_index for answer in answers]
        if len(indexes) != len(set(indexes)):
            raise ValueError("question_index must be unique within QuizAttempt")

        instance = object.__new__(cls)
        object.__setattr__(instance, "id", id)
        object.__setattr__(instance, "attempted_at", attempted_at)
        object.__setattr__(instance, "score_numerator", score_numerator)
        object.__setattr__(instance, "score_denominator", score_denominator)
        object.__setattr__(instance, "answers", answers)
        return instance
