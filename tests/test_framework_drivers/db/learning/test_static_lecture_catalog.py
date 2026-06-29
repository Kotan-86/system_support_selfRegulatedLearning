# 仕様: docs/spec/application-usecase.md#LectureCatalog
# 仕様: docs/spec/framework-drivers-layer.md#db
"""StaticLectureCatalog の受入基準。"""
from __future__ import annotations

from pathlib import Path

from domain.shared.ids import LectureId
from framework_drivers.db.learning.static_lecture_catalog import (
    StaticLectureCatalog,
    build_near_term_lecture,
    build_near_term_lectures,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[4]


class TestBuildNearTermLecture:
    def test_lecture_1_video_and_srt(self) -> None:
        lecture = build_near_term_lecture(lecture_id="lecture-1")

        assert str(lecture.id) == "lecture-1"
        assert lecture.video_url == "https://www.youtube.com/watch?v=Y2HC0I8cTAI"
        assert lecture.srt_path == str(
            _PROJECT_ROOT / "lectures" / "lecture-1" / "subtitles.srt"
        )

    def test_lecture_2_video_and_srt(self) -> None:
        lecture = build_near_term_lecture(lecture_id="lecture-2")

        assert str(lecture.id) == "lecture-2"
        assert lecture.video_url == "https://www.youtube.com/watch?v=1MuwwFipX9o"
        assert lecture.srt_path == str(
            _PROJECT_ROOT / "lectures" / "lecture-2" / "subtitles.srt"
        )

    def test_lecture_3_video_and_srt(self) -> None:
        lecture = build_near_term_lecture(lecture_id="lecture-3")

        assert str(lecture.id) == "lecture-3"
        assert lecture.video_url == "https://www.youtube.com/watch?v=Sa06YB2oXyw"
        assert lecture.srt_path == str(
            _PROJECT_ROOT / "lectures" / "lecture-3" / "subtitles.srt"
        )

    def test_srt_paths_exist_on_disk(self) -> None:
        for lecture in build_near_term_lectures():
            assert Path(lecture.srt_path).is_file()


class TestStaticLectureCatalog:
    def test_find_by_id_returns_all_three_lectures(self) -> None:
        catalog = StaticLectureCatalog()

        for lecture_id in ("lecture-1", "lecture-2", "lecture-3"):
            lecture = catalog.find_by_id(LectureId(lecture_id))
            assert lecture is not None
            assert str(lecture.id) == lecture_id

    def test_find_by_id_unknown_returns_none(self) -> None:
        catalog = StaticLectureCatalog()

        assert catalog.find_by_id(LectureId("lecture-unknown")) is None
