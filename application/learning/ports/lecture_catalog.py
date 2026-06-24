# 仕様: docs/spec/application-usecase.md#LectureCatalog
"""講義メタデータ参照 Port。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.learning.lecture import Lecture
from domain.shared.ids import LectureId


class LectureCatalog(ABC):
    """lecture_id から Lecture メタデータを解決する。"""

    @abstractmethod
    def find_by_id(self, lecture_id: LectureId) -> Lecture | None:
        """講義が存在すれば Lecture を返す。存在しなければ None。"""
