# 仕様: docs/spec/application-usecase.md#LectureCatalog
# 仕様: docs/spec/framework-drivers-layer.md#db
"""近い実験向けの固定 LectureCatalog。"""
from __future__ import annotations

from pathlib import Path

from application.learning.ports.lecture_catalog import LectureCatalog
from domain.learning.lecture import Lecture
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.shared.ids import LectureId
from interfaces.common.default_lecture import DEFAULT_LECTURE_ID_VALUE

_PROJECT_ROOT = Path(__file__).resolve().parents[3]

_NEAR_TERM_LECTURES: tuple[tuple[str, str, str], ...] = (
    (
        "lecture-1",
        "線形代数入門（近い実験 1）",
        "https://www.youtube.com/watch?v=Y2HC0I8cTAI",
    ),
    (
        "lecture-2",
        "線形代数入門（近い実験 2）",
        "https://www.youtube.com/watch?v=1MuwwFipX9o",
    ),
    (
        "lecture-3",
        "線形代数入門（近い実験 3）",
        "https://www.youtube.com/watch?v=Sa06YB2oXyw",
    ),
)


def _srt_path_for(lecture_id: str) -> str:
    return str(_PROJECT_ROOT / "lectures" / lecture_id / "subtitles.srt")


def _lecture_definition_for(lecture_id: str) -> tuple[str, str, str] | None:
    for definition in _NEAR_TERM_LECTURES:
        if definition[0] == lecture_id:
            return definition
    return None


def _near_term_quiz_definition() -> QuizDefinition:
    """Google Form 小テスト（問 1〜5）に対応する QuizDefinition。"""
    return QuizDefinition(
        questions=tuple(
            Question(
                index=index,
                text=f"問{index}",
                choices=("A", "B", "C", "D"),
                correct_answer="A",
            )
            for index in range(1, 6)
        )
    )


def build_near_term_lecture(*, lecture_id: str = DEFAULT_LECTURE_ID_VALUE) -> Lecture:
    """近い実験の固定 Lecture を構築する。"""
    definition = _lecture_definition_for(lecture_id)
    if definition is None:
        raise ValueError(f"Unknown near-term lecture_id: {lecture_id!r}")
    lid, title, video_url = definition
    return Lecture.create(
        id=LectureId(lid),
        title=title,
        video_url=video_url,
        srt_path=_srt_path_for(lid),
        quiz_definition=_near_term_quiz_definition(),
    )


def build_near_term_lectures() -> tuple[Lecture, ...]:
    """近い実験の 3 講義を構築する（テスト・Composition Root 向け）。"""
    return tuple(
        build_near_term_lecture(lecture_id=lid) for lid, _, _ in _NEAR_TERM_LECTURES
    )


class StaticLectureCatalog(LectureCatalog):
    """近い実験 3 講義固定の LectureCatalog。"""

    def __init__(self, lectures: tuple[Lecture, ...] | None = None) -> None:
        items = lectures or build_near_term_lectures()
        self._lectures: dict[LectureId, Lecture] = {
            lecture.id: lecture for lecture in items
        }

    def find_by_id(self, lecture_id: LectureId) -> Lecture | None:
        return self._lectures.get(lecture_id)
