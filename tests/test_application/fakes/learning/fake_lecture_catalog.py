# 仕様: docs/spec/application-usecase.md#LectureCatalog
"""LectureCatalog の Fake 実装（テスト用）。"""
from __future__ import annotations

from domain.learning.lecture import Lecture
from domain.shared.ids import LectureId

from application.learning.ports.lecture_catalog import LectureCatalog


class FakeLectureCatalog(LectureCatalog):
    """固定 Lecture を返す Fake LectureCatalog。"""

    def __init__(self, lectures: tuple[Lecture, ...] = ()) -> None:
        self._lectures: dict[LectureId, Lecture] = {
            lecture.id: lecture for lecture in lectures
        }

    def find_by_id(self, lecture_id: LectureId) -> Lecture | None:
        return self._lectures.get(lecture_id)

    def add(self, lecture: Lecture) -> None:
        """テスト用: 講義をカタログに追加する。"""
        self._lectures[lecture.id] = lecture
