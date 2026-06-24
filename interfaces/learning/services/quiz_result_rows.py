# 仕様: docs/spec/interfaces-layer.md#QuizResultRowViewModel
"""quiz_answers と Lecture.quiz_definition を結合する。"""
from __future__ import annotations

from domain.learning.quiz_attempt import QuizAnswer
from domain.learning.quiz_definition import QuizDefinition

from interfaces.learning.view_models.lad_dashboard import QuizResultRowViewModel


def build_quiz_result_rows(
    quiz_answers: tuple[QuizAnswer, ...],
    quiz_definition: QuizDefinition,
) -> tuple[QuizResultRowViewModel, ...]:
    """question_index で設問文を結合し、表示用の行を生成する。"""
    questions_by_index = {
        question.index: question for question in quiz_definition.questions
    }
    rows: list[QuizResultRowViewModel] = []
    for answer in sorted(quiz_answers, key=lambda item: item.question_index):
        question = questions_by_index.get(answer.question_index)
        if question is None:
            continue
        rows.append(
            QuizResultRowViewModel(
                question_index=answer.question_index,
                question_text=question.text,
                selected_choice=answer.selected_answer,
                is_correct=answer.is_correct,
            )
        )
    return tuple(rows)
