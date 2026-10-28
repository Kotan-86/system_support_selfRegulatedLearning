# 仕様: docs/spec/application-usecase.md#LectureCatalog
# 仕様: docs/spec/framework-drivers-layer.md#db
"""StaticLectureCatalog の受入基準。"""
from __future__ import annotations

from pathlib import Path

import pytest

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

    @pytest.mark.parametrize(
        ("lecture_id", "q1_snippet"),
        [
            (
                "lecture-1",
                "動画では、球の表面積は、同じ半径 r、高さ 2r の円柱のどの部分の面積と等しいと説明されていますか。",
            ),
            (
                "lecture-2",
                "標準的なモンティ・ホール問題で、司会者がハズレの扉を1つ開けた後、",
            ),
            (
                "lecture-3",
                "A・B・Cのうち1人だけが恩赦を受けます。",
            ),
        ],
    )
    def test_quiz_definition_has_five_questions_with_lecture_specific_q1(
        self, lecture_id: str, q1_snippet: str
    ) -> None:
        """各講義の QuizDefinition は 5 問で、Q1 文言が講義別定義と一致する。"""
        catalog = StaticLectureCatalog()
        lecture = catalog.find_by_id(LectureId(lecture_id))
        assert lecture is not None

        questions = lecture.quiz_definition.questions
        assert len(questions) == 5
        assert q1_snippet in questions[0].text


# ---------------------------------------------------------------------------
# 文系レベル3講義 lecture-4〜6 の登録 (PBI #33)
# 仕様: docs/spec/humanities-lectures.md#受入基準 AC1・AC2
# 期待値は tests/test_lectures/humanities_data.py(仕様のみが出典)。
# ---------------------------------------------------------------------------
from tests.test_lectures.humanities_data import (  # noqa: E402
    HUMANITIES_BY_ID,
    HUMANITIES_IDS,
)


class TestHumanitiesLecturesRegistered:
    @pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
    def test_ac1_catalog_returns_lecture_with_video_and_title(
        self, lecture_id: str
    ) -> None:
        """AC1: 講義カタログで lecture-4〜6 を引くと、動画 URL と題名が仕様どおり。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC1
        expected = HUMANITIES_BY_ID[lecture_id]
        lecture = StaticLectureCatalog().find_by_id(LectureId(lecture_id))

        assert lecture is not None
        assert str(lecture.id) == lecture_id
        assert lecture.video_url == expected.video_url
        assert lecture.title == expected.title

    @pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
    def test_ac1_build_near_term_lecture_includes_humanities(
        self, lecture_id: str
    ) -> None:
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC1
        lecture = build_near_term_lecture(lecture_id=lecture_id)
        assert lecture.video_url == HUMANITIES_BY_ID[lecture_id].video_url

    @pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
    def test_ac2_srt_path_is_lectures_dir_and_file_exists(self, lecture_id: str) -> None:
        """AC2: 字幕のパスは lectures/<講義ID>/subtitles.srt で、ファイルが実在する。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC2
        lecture = StaticLectureCatalog().find_by_id(LectureId(lecture_id))
        assert lecture is not None
        assert lecture.srt_path == str(
            _PROJECT_ROOT / "lectures" / lecture_id / "subtitles.srt"
        )
        assert Path(lecture.srt_path).is_file()

    def test_ac1_existing_lectures_unchanged(self) -> None:
        """AC13(c): lecture-1〜3 の動画は変わらない(登録後も)。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC13(c)
        expected = {
            "lecture-1": "https://www.youtube.com/watch?v=Y2HC0I8cTAI",
            "lecture-2": "https://www.youtube.com/watch?v=1MuwwFipX9o",
            "lecture-3": "https://www.youtube.com/watch?v=Sa06YB2oXyw",
        }
        catalog = StaticLectureCatalog()
        for lecture_id, url in expected.items():
            lecture = catalog.find_by_id(LectureId(lecture_id))
            assert lecture is not None and lecture.video_url == url
