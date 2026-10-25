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


# ---------------------------------------------------------------------------
# 文系レベル3講義 lecture-4〜6 の講義情報の構造 (PBI #33)
# 仕様: docs/spec/humanities-lectures.md#受入基準 AC9
# (内容の妥当性は AC10 = PO確認。ここでは構造だけを検査する。)
# 字幕の最終終了時刻は仕様の表の値(tests/test_lectures/humanities_data.py)。
# ---------------------------------------------------------------------------
import importlib  # noqa: E402

from tests.test_lectures.humanities_data import (  # noqa: E402
    HUMANITIES_BY_ID,
    HUMANITIES_IDS,
)


def _humanities_outline(lecture_id: str):
    number = lecture_id.split("-")[1]
    module = importlib.import_module(
        f"framework_drivers.db.learning.lecture_outlines.lecture_{number}"
    )
    return module.build_lecture_outline()


@pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
class TestHumanitiesLectureOutlineStructure:
    def test_ac9_has_at_least_one_section_with_ascending_starts(self, lecture_id: str) -> None:
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC9
        outline = _humanities_outline(lecture_id)
        assert len(outline.sections) >= 1
        assert all(section.id and section.title for section in outline.sections)
        starts = [section.start_sec for section in outline.sections]
        assert starts == sorted(starts), "章の開始秒が昇順でない"

    def test_ac9_all_times_within_zero_and_last_subtitle_end(self, lecture_id: str) -> None:
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC9
        last_end = HUMANITIES_BY_ID[lecture_id].srt_last_end_sec
        outline = _humanities_outline(lecture_id)
        assert len(outline.sections) >= 1
        for section in outline.sections:
            assert section.end_sec is not None, f"{section.id}: 終了秒がない"
            assert 0 <= section.start_sec <= last_end, f"{section.id}: 開始秒が範囲外"
            assert 0 <= section.end_sec <= last_end, f"{section.id}: 終了秒が範囲外"
        for exercise in outline.in_video_exercises:  # 0 件でもよい
            assert 0 <= exercise.timestamp_sec <= last_end, f"{exercise.id}: 位置が範囲外"

    def test_ac9_one_rubric_note_for_each_of_questions_1_to_5(self, lecture_id: str) -> None:
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC9
        outline = _humanities_outline(lecture_id)
        indices = sorted(note.question_index for note in outline.quiz_rubric_notes)
        assert indices == [1, 2, 3, 4, 5]
        assert all(note.note.strip() for note in outline.quiz_rubric_notes)

    def test_ac9_catalog_lecture_carries_the_outline(self, lecture_id: str) -> None:
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC9(カタログ経由で講義情報が付く)
        lecture = StaticLectureCatalog().find_by_id(LectureId(lecture_id))
        assert lecture is not None
        assert lecture.outline.is_empty is False
        assert sorted(n.question_index for n in lecture.outline.quiz_rubric_notes) == [1, 2, 3, 4, 5]
