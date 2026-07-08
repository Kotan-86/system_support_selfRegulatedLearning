# 仕様: docs/spec/domain-model.md#LectureOutline
"""ITS Domain Model: 講義構造・演習・小テスト採点意図の Value Object。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LectureSection:
    """講義動画内のセクション（章）。"""

    id: str
    title: str
    start_sec: int
    end_sec: int | None = None
    summary: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("LectureSection id must not be empty")
        if not self.title:
            raise ValueError("LectureSection title must not be empty")
        if self.start_sec < 0:
            raise ValueError("LectureSection start_sec must be >= 0")
        if self.end_sec is not None and self.end_sec <= self.start_sec:
            raise ValueError("LectureSection end_sec must be greater than start_sec")


@dataclass(frozen=True)
class InVideoExercise:
    """動画内の演習・例題。"""

    id: str
    title: str
    timestamp_sec: int
    description: str
    related_section_id: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("InVideoExercise id must not be empty")
        if not self.title:
            raise ValueError("InVideoExercise title must not be empty")
        if self.timestamp_sec < 0:
            raise ValueError("InVideoExercise timestamp_sec must be >= 0")
        if not self.description:
            raise ValueError("InVideoExercise description must not be empty")


@dataclass(frozen=True)
class QuizRubricNote:
    """小テスト設問の採点意図・よくある誤解。"""

    question_index: int
    note: str

    def __post_init__(self) -> None:
        if self.question_index < 1:
            raise ValueError("QuizRubricNote question_index must be >= 1")
        if not self.note:
            raise ValueError("QuizRubricNote note must not be empty")


@dataclass(frozen=True)
class LectureOutline:
    """講義の静的構造メタデータ（ITS Domain Model / 知識ベース）。"""

    sections: tuple[LectureSection, ...]
    in_video_exercises: tuple[InVideoExercise, ...]
    quiz_rubric_notes: tuple[QuizRubricNote, ...] = ()

    def __post_init__(self) -> None:
        section_ids = [section.id for section in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("LectureOutline section ids must be unique")

        exercise_ids = [exercise.id for exercise in self.in_video_exercises]
        if len(exercise_ids) != len(set(exercise_ids)):
            raise ValueError("LectureOutline exercise ids must be unique")

    @classmethod
    def empty(cls) -> LectureOutline:
        """後方互換用の空 Outline。"""
        return cls(sections=(), in_video_exercises=())

    @property
    def is_empty(self) -> bool:
        return (
            len(self.sections) == 0
            and len(self.in_video_exercises) == 0
            and len(self.quiz_rubric_notes) == 0
        )
