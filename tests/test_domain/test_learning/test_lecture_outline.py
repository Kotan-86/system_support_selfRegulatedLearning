# 仕様: docs/spec/domain-model.md#LectureOutline
"""LectureOutline および関連 Value Object の不変条件テスト。"""
from __future__ import annotations

import dataclasses

import pytest

from domain.learning.lecture_outline import (
    InVideoExercise,
    LectureOutline,
    LectureSection,
    QuizRubricNote,
)


class TestLectureSection:
    """LectureSection の不変条件。"""

    def test_accepts_valid_section(self) -> None:
        section = LectureSection(
            id="intro",
            title="導入",
            start_sec=0,
            end_sec=120,
            summary="講義の概要",
        )

        assert section.id == "intro"
        assert section.title == "導入"
        assert section.start_sec == 0
        assert section.end_sec == 120
        assert section.summary == "講義の概要"

    def test_end_sec_may_be_none(self) -> None:
        section = LectureSection(
            id="closing",
            title="まとめ",
            start_sec=600,
        )

        assert section.end_sec is None

    @pytest.mark.parametrize(
        ("field_name", "kwargs"),
        [
            ("id", {"id": "", "title": "導入", "start_sec": 0}),
            ("title", {"id": "intro", "title": "", "start_sec": 0}),
        ],
    )
    def test_rejects_empty_id_or_title(
        self, field_name: str, kwargs: dict[str, object]
    ) -> None:
        with pytest.raises(ValueError, match=field_name):
            LectureSection(**kwargs)  # type: ignore[arg-type]

    def test_rejects_negative_start_sec(self) -> None:
        with pytest.raises(ValueError, match="start_sec"):
            LectureSection(id="intro", title="導入", start_sec=-1)

    def test_rejects_end_sec_not_after_start_sec(self) -> None:
        with pytest.raises(ValueError, match="end_sec"):
            LectureSection(
                id="intro",
                title="導入",
                start_sec=100,
                end_sec=100,
            )


class TestInVideoExercise:
    """InVideoExercise の不変条件。"""

    def test_accepts_valid_exercise(self) -> None:
        exercise = InVideoExercise(
            id="ex-1",
            title="例題1",
            timestamp_sec=120,
            description="円柱との関係を確認する演習",
            related_section_id="approach-1",
        )

        assert exercise.id == "ex-1"
        assert exercise.related_section_id == "approach-1"

    @pytest.mark.parametrize(
        ("field_name", "kwargs"),
        [
            ("id", {"id": "", "title": "例題", "timestamp_sec": 0, "description": "説明"}),
            (
                "title",
                {"id": "ex-1", "title": "", "timestamp_sec": 0, "description": "説明"},
            ),
            (
                "description",
                {"id": "ex-1", "title": "例題", "timestamp_sec": 0, "description": ""},
            ),
        ],
    )
    def test_rejects_empty_required_fields(
        self, field_name: str, kwargs: dict[str, object]
    ) -> None:
        with pytest.raises(ValueError, match=field_name):
            InVideoExercise(**kwargs)  # type: ignore[arg-type]

    def test_rejects_negative_timestamp(self) -> None:
        with pytest.raises(ValueError, match="timestamp_sec"):
            InVideoExercise(
                id="ex-1",
                title="例題",
                timestamp_sec=-1,
                description="説明",
            )


class TestQuizRubricNote:
    """QuizRubricNote の不変条件。"""

    def test_accepts_valid_note(self) -> None:
        note = QuizRubricNote(
            question_index=1,
            note="用語の厳密さを問う",
        )

        assert note.question_index == 1
        assert note.note == "用語の厳密さを問う"

    def test_rejects_non_positive_question_index(self) -> None:
        with pytest.raises(ValueError, match="question_index"):
            QuizRubricNote(question_index=0, note="意図")

    def test_rejects_empty_note(self) -> None:
        with pytest.raises(ValueError, match="note"):
            QuizRubricNote(question_index=1, note="")


class TestLectureOutline:
    """LectureOutline の不変条件と空 Outline。"""

    def test_empty_outline_has_no_items(self) -> None:
        outline = LectureOutline.empty()

        assert outline.sections == ()
        assert outline.in_video_exercises == ()
        assert outline.quiz_rubric_notes == ()
        assert outline.is_empty is True

    def test_non_empty_outline_is_not_empty(self) -> None:
        outline = LectureOutline(
            sections=(
                LectureSection(id="intro", title="導入", start_sec=0),
            ),
            in_video_exercises=(),
        )

        assert outline.is_empty is False

    def test_is_frozen(self) -> None:
        outline = LectureOutline.empty()

        with pytest.raises(dataclasses.FrozenInstanceError):
            outline.sections = ()  # type: ignore[misc]

    def test_rejects_duplicate_section_ids(self) -> None:
        section = LectureSection(id="intro", title="導入", start_sec=0)

        with pytest.raises(ValueError, match="section"):
            LectureOutline(
                sections=(section, section),
                in_video_exercises=(),
            )

    def test_rejects_duplicate_exercise_ids(self) -> None:
        exercise = InVideoExercise(
            id="ex-1",
            title="例題",
            timestamp_sec=0,
            description="説明",
        )

        with pytest.raises(ValueError, match="exercise"):
            LectureOutline(
                sections=(),
                in_video_exercises=(exercise, exercise),
            )
