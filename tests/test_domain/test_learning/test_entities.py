# 仕様: docs/spec/domain-model.md#Lecture（講義）
# 仕様: docs/spec/domain-model.md#QuizAttempt（小テスト受験）
# 仕様: docs/spec/domain-model.md#QuizAnswer（小テスト回答）
# 仕様: docs/spec/domain-implementation-plan.md Phase 2
"""
Learning コンテキストの Entity（Lecture, QuizAttempt, QuizAnswer）の単体テスト。

Phase 2 ではフィールド構成とスコア・設問参照の不変条件を定義する。
"""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest

from domain.learning.lecture import Lecture
from domain.learning.quiz_attempt import QuizAnswer, QuizAttempt
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.shared.ids import LectureId, QuizAttemptId

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _sample_quiz_definition() -> QuizDefinition:
    return QuizDefinition(
        questions=(
            Question(
                index=1,
                text="問1",
                choices=("A", "B"),
                correct_answer="A",
            ),
        )
    )


def _sample_lecture(*, video_url: str = "https://example.com/video.mp4") -> Lecture:
    return Lecture.create(
        id=LectureId("lecture-1"),
        title="サンプル講義",
        video_url=video_url,
        srt_path="/path/to/subtitles.srt",
        quiz_definition=_sample_quiz_definition(),
    )


def _sample_quiz_answer(*, question_index: int = 1) -> QuizAnswer:
    return QuizAnswer(
        question_index=question_index,
        selected_answer="A",
        is_correct=True,
    )


class TestLecture:
    """Lecture Entity の不変条件を検証する。"""

    def test_accepts_valid_lecture(self) -> None:
        """videoUrl と quizDefinition が有効な Lecture を生成できる。"""
        lecture = _sample_lecture()
        assert lecture.id == LectureId("lecture-1")
        assert lecture.title == "サンプル講義"
        assert lecture.video_url == "https://example.com/video.mp4"
        assert lecture.srt_path == "/path/to/subtitles.srt"
        assert len(lecture.quiz_definition.questions) == 1

    def test_has_quiz_definition_field(self) -> None:
        """Lecture は quizDefinition を 1 つ持つ。"""
        fields = {field.name for field in dataclasses.fields(Lecture)}
        assert "quiz_definition" in fields

    def test_rejects_empty_video_url(self) -> None:
        """videoUrl が空文字のとき ValueError で拒否される。"""
        with pytest.raises(ValueError):
            _sample_lecture(video_url="")


class TestQuizAnswer:
    """QuizAnswer Entity の不変条件を検証する。"""

    def test_has_answer_fields_only(self) -> None:
        """QuizAnswer は questionIndex, selectedAnswer, isCorrect のみを持つ。"""
        fields = {field.name for field in dataclasses.fields(QuizAnswer)}
        assert fields == {"question_index", "selected_answer", "is_correct"}

    def test_has_no_question_text_field(self) -> None:
        """QuizAnswer に問題文フィールドが存在しない（Lecture 定義参照のみ）。"""
        answer = _sample_quiz_answer()
        assert not hasattr(answer, "question_text")
        assert not hasattr(answer, "text")
        assert not hasattr(answer, "choices")

    def test_rejects_duplicate_question_index_within_attempt(self) -> None:
        """同一 QuizAttempt 内で questionIndex が重複すると拒否される。"""
        with pytest.raises(ValueError):
            QuizAttempt.create(
                id=QuizAttemptId("attempt-1"),
                attempted_at=FIXED_NOW,
                score_numerator=1,
                score_denominator=1,
                answers=(
                    _sample_quiz_answer(question_index=1),
                    _sample_quiz_answer(question_index=1),
                ),
            )


class TestQuizAttempt:
    """QuizAttempt Entity の不変条件を検証する。"""

    def test_accepts_valid_score(self) -> None:
        """0 <= scoreNumerator <= scoreDenominator かつ scoreDenominator > 0 を満たす。"""
        attempt = QuizAttempt.create(
            id=QuizAttemptId("attempt-1"),
            attempted_at=FIXED_NOW,
            score_numerator=2,
            score_denominator=3,
            answers=(_sample_quiz_answer(),),
        )
        assert attempt.score_numerator == 2
        assert attempt.score_denominator == 3

    def test_rejects_zero_denominator(self) -> None:
        """scoreDenominator が 0 のとき拒否される。"""
        with pytest.raises(ValueError):
            QuizAttempt.create(
                id=QuizAttemptId("attempt-1"),
                attempted_at=FIXED_NOW,
                score_numerator=0,
                score_denominator=0,
                answers=(_sample_quiz_answer(),),
            )

    def test_rejects_negative_denominator(self) -> None:
        """scoreDenominator が負のとき拒否される。"""
        with pytest.raises(ValueError):
            QuizAttempt.create(
                id=QuizAttemptId("attempt-1"),
                attempted_at=FIXED_NOW,
                score_numerator=0,
                score_denominator=-1,
                answers=(_sample_quiz_answer(),),
            )

    def test_rejects_numerator_greater_than_denominator(self) -> None:
        """scoreNumerator > scoreDenominator のとき拒否される。"""
        with pytest.raises(ValueError):
            QuizAttempt.create(
                id=QuizAttemptId("attempt-1"),
                attempted_at=FIXED_NOW,
                score_numerator=5,
                score_denominator=3,
                answers=(_sample_quiz_answer(),),
            )

    def test_rejects_negative_numerator(self) -> None:
        """scoreNumerator が負のとき拒否される。"""
        with pytest.raises(ValueError):
            QuizAttempt.create(
                id=QuizAttemptId("attempt-1"),
                attempted_at=FIXED_NOW,
                score_numerator=-1,
                score_denominator=3,
                answers=(_sample_quiz_answer(),),
            )

    def test_rejects_empty_answers(self) -> None:
        """answers が 0 件のとき拒否される。"""
        with pytest.raises(ValueError):
            QuizAttempt.create(
                id=QuizAttemptId("attempt-1"),
                attempted_at=FIXED_NOW,
                score_numerator=0,
                score_denominator=1,
                answers=(),
            )
