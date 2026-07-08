# 仕様: docs/spec/domain-model.md#LectureOutline
# 仕様: docs/spec/framework-drivers-layer.md#db
"""lecture_outlines モジュールと StaticLectureCatalog への outline 注入。"""
from __future__ import annotations

import pytest

from domain.shared.ids import LectureId
from framework_drivers.db.learning.lecture_outlines import (
    lecture_1,
    lecture_2,
    lecture_3,
)
from framework_drivers.db.learning.static_lecture_catalog import (
    StaticLectureCatalog,
    build_near_term_lecture,
)


class TestBuildLectureOutline:
    """各講義の build_lecture_outline() が非空 Outline を返す。"""

    @pytest.mark.parametrize(
        ("module", "lecture_id"),
        [
            (lecture_1, "lecture-1"),
            (lecture_2, "lecture-2"),
            (lecture_3, "lecture-3"),
        ],
    )
    def test_build_lecture_outline_is_non_empty(
        self, module: object, lecture_id: str
    ) -> None:
        outline = module.build_lecture_outline()  # type: ignore[attr-defined]

        assert outline.is_empty is False
        assert len(outline.sections) >= 1
        assert all(section.id for section in outline.sections)


class TestStaticLectureCatalogOutline:
    """StaticLectureCatalog が outline 付き Lecture を返す。"""

    def test_lecture_has_outline_field(self) -> None:
        lecture = build_near_term_lecture(lecture_id="lecture-1")

        assert len(lecture.outline.sections) >= 1

    def test_static_catalog_injects_outline(self) -> None:
        catalog = StaticLectureCatalog()
        lecture = catalog.find_by_id(LectureId("lecture-1"))

        assert lecture is not None
        assert lecture.outline.is_empty is False
        assert len(lecture.outline.sections) >= 1

    @pytest.mark.parametrize("lecture_id", ("lecture-1", "lecture-2", "lecture-3"))
    def test_all_near_term_lectures_have_outline(self, lecture_id: str) -> None:
        catalog = StaticLectureCatalog()
        lecture = catalog.find_by_id(LectureId(lecture_id))

        assert lecture is not None
        assert lecture.outline.is_empty is False
