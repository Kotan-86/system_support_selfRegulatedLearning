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
