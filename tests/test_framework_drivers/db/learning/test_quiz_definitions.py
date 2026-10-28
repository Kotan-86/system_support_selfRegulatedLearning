# 仕様: docs/spec/framework-drivers-layer.md#db
# 仕様: docs/spec/application-usecase.md#LectureCatalog
"""講義別 quiz_definitions モジュールの受入基準。"""
from __future__ import annotations

import pytest

from domain.learning.quiz_definition import QuizDefinition
from framework_drivers.db.learning.quiz_definitions import (
    lecture_1,
    lecture_2,
    lecture_3,
)


@pytest.mark.parametrize(
    "build_quiz",
    [
        lecture_1.build_quiz_definition,
        lecture_2.build_quiz_definition,
        lecture_3.build_quiz_definition,
    ],
)
def test_build_quiz_definition_has_five_questions_with_four_choices(build_quiz) -> None:
    """各講義の QuizDefinition は 5 問・各 4 択で、正解は選択肢に含まれる。"""
    quiz: QuizDefinition = build_quiz()

    assert len(quiz.questions) == 5
    for question in quiz.questions:
        assert len(question.choices) == 4, (
            f"Q{question.index} は 4 択であること"
        )
        assert question.correct_answer in question.choices, (
            f"Q{question.index} の correct_answer は choices に含まれること"
        )


@pytest.mark.parametrize(
    ("module", "expected_title", "expected_description"),
    [
        (lecture_1, lecture_1.QUIZ_TITLE, lecture_1.QUIZ_DESCRIPTION),
        (lecture_2, lecture_2.QUIZ_TITLE, lecture_2.QUIZ_DESCRIPTION),
        (lecture_3, lecture_3.QUIZ_TITLE, lecture_3.QUIZ_DESCRIPTION),
    ],
)
def test_quiz_metadata_constants(module, expected_title: str, expected_description: str) -> None:
    """各モジュールは QUIZ_TITLE / QUIZ_DESCRIPTION を公開する。"""
    assert module.QUIZ_TITLE == expected_title
    assert module.QUIZ_DESCRIPTION == expected_description


# ---------------------------------------------------------------------------
# 文系レベル3講義 lecture-4〜6 の小テスト (PBI #33)
# 仕様: docs/spec/humanities-lectures.md#受入基準 AC4(付録A と一致)
# 期待値は tests/test_lectures/humanities_data.py(仕様の付録Aのセルの文字列そのまま)。
# ---------------------------------------------------------------------------
import dataclasses  # noqa: E402
import importlib  # noqa: E402
import re  # noqa: E402

from tests.test_lectures.humanities_data import (  # noqa: E402
    HUMANITIES_BY_ID,
    HUMANITIES_IDS,
)


def _humanities_module(lecture_id: str):
    number = lecture_id.split("-")[1]
    return importlib.import_module(
        f"framework_drivers.db.learning.quiz_definitions.lecture_{number}"
    )


@pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
class TestHumanitiesQuizDefinition:
    def test_ac4_five_questions_four_choices_match_appendix(self, lecture_id: str) -> None:
        """AC4: 5 問・各 4 択で、問題文・選択肢(並び順を含む)・正解が付録A と一致する。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC4
        quiz: QuizDefinition = _humanities_module(lecture_id).build_quiz_definition()
        expected = HUMANITIES_BY_ID[lecture_id].questions

        assert len(quiz.questions) == 5
        for index, (actual, exp) in enumerate(zip(quiz.questions, expected), 1):
            assert actual.index == index
            assert actual.text == exp.text, f"Q{index} の問題文が付録A と違う"
            assert tuple(actual.choices) == exp.choices, f"Q{index} の選択肢(順序含む)が付録A と違う"
            assert actual.correct_answer == exp.correct_text, f"Q{index} の正解が付録A と違う"

    def test_ac4_no_option_marker_or_heading_in_text(self, lecture_id: str) -> None:
        """AC4: 記号「A.〜D.」と設問の見出しを文面に含めない。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC4
        quiz = _humanities_module(lecture_id).build_quiz_definition()
        for question in quiz.questions:
            for choice in question.choices:
                assert not re.match(r"^[A-DＡ-Ｄ][\.．:：)）]", choice), f"記号付き: {choice!r}"
            assert not re.match(r"^(Q|問)\s*\d", question.text), f"見出し付き: {question.text!r}"

    def test_ac4_quiz_definition_has_no_explanation_field(self, lecture_id: str) -> None:
        """AC4: 小テストのデータは解説を持たない(Question のフィールドは増えない)。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC4
        quiz = _humanities_module(lecture_id).build_quiz_definition()
        assert len(quiz.questions) == 5  # 実装があること(スタブでは not implemented)
        for question in quiz.questions:
            names = {f.name for f in dataclasses.fields(question)}
            assert names == {"index", "text", "choices", "correct_answer"}

    def test_ac5_quiz_title_and_description_constants(self, lecture_id: str) -> None:
        """AC5: 小テストの題名と説明(_QUIZ_MODULES の取得元の定数)。"""
        # 仕様: docs/spec/humanities-lectures.md#受入基準 AC5
        module = _humanities_module(lecture_id)
        exp = HUMANITIES_BY_ID[lecture_id]
        assert module.QUIZ_TITLE == exp.quiz_title
        assert module.QUIZ_DESCRIPTION == exp.quiz_description
