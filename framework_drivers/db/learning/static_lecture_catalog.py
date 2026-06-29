# 仕様: docs/spec/application-usecase.md#LectureCatalog
# 仕様: docs/spec/framework-drivers-layer.md#db
"""近い実験向けの固定 LectureCatalog。"""
from __future__ import annotations

import os
from pathlib import Path

from application.learning.ports.lecture_catalog import LectureCatalog
from domain.learning.lecture import Lecture
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.shared.ids import LectureId
from interfaces.common.default_lecture import DEFAULT_LECTURE_ID_VALUE

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_VIDEO_URL = "https://www.youtube.com/watch?v=ZXuZHNjS2tA"
"""lecture_video_platform/lectureVideoPlatform.html と同一の YouTube 動画。"""


def _resolve_srt_path() -> str:
    explicit = os.environ.get("LECTURE_SRT_PATH")
    if explicit:
        return explicit
    return str(_PROJECT_ROOT / "demoLectureVideoSub.srt")


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
    return Lecture.create(
        id=LectureId(lecture_id),
        title="線形代数入門（近い実験）",
        video_url=_DEFAULT_VIDEO_URL,
        srt_path=_resolve_srt_path(),
        quiz_definition=_near_term_quiz_definition(),
    )


class StaticLectureCatalog(LectureCatalog):
    """近い実験 1 講義固定の LectureCatalog。"""

    def __init__(self, lecture: Lecture | None = None) -> None:
        self._lecture = lecture or build_near_term_lecture()

    def find_by_id(self, lecture_id: LectureId) -> Lecture | None:
        if lecture_id == self._lecture.id:
            return self._lecture
        return None
