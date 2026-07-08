# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
# 仕様: docs/spec/domain-model.md#LectureOutline
"""context_formatters の単体テスト。"""
from __future__ import annotations

from domain.learning.lecture_outline import (
    InVideoExercise,
    LectureOutline,
    LectureSection,
    QuizRubricNote,
)
from interfaces.tutoring.context_formatters import (
    EMPTY_PLACEHOLDER,
    format_lecture_outline,
)


def _sample_outline() -> LectureOutline:
    return LectureOutline(
        sections=(
            LectureSection(
                id="intro",
                title="行列の定義",
                start_sec=150,
                end_sec=525,
                summary="行列とは数を表形式に並べたもの",
            ),
        ),
        in_video_exercises=(
            InVideoExercise(
                id="ex-1",
                title="例題1",
                timestamp_sec=735,
                description="2次方程式の解き方",
                related_section_id="intro",
            ),
        ),
        quiz_rubric_notes=(
            QuizRubricNote(
                question_index=1,
                note="「同じ意味」判定は用語の厳密さを問う",
            ),
        ),
    )


class TestFormatLectureOutline:
    """format_lecture_outline の整形。"""

    def test_empty_outline_returns_placeholder(self) -> None:
        assert format_lecture_outline(LectureOutline.empty()) == EMPTY_PLACEHOLDER

    def test_includes_section_heading_and_time_range(self) -> None:
        text = format_lecture_outline(_sample_outline())

        assert "講義構造" in text
        assert "セクション: 行列の定義" in text
        assert "02:30" in text
        assert "08:45" in text
        assert "概要: 行列とは数を表形式に並べたもの" in text

    def test_includes_exercise_and_rubric(self) -> None:
        text = format_lecture_outline(_sample_outline())

        assert "演習: 例題1" in text
        assert "12:15" in text
        assert "2次方程式の解き方" in text
        assert "小テスト採点意図" in text
        assert "問1:" in text
        assert "「同じ意味」判定は用語の厳密さを問う" in text
