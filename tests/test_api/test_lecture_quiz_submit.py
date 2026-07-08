# 仕様: docs/spec/framework-drivers-layer.md#HTTP-契約
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-5-講義動画フロント
"""講義別小テストの正答 payload で POST /api/quiz-attempts が受理されること。"""
from __future__ import annotations

import pytest

from framework_drivers.db.learning.quiz_definitions import (
    lecture_1,
    lecture_2,
    lecture_3,
)
from domain.learning.quiz_definition import QuizDefinition


def _all_correct_quiz_attempt_payload(
    *,
    participant_id: str,
    quiz: QuizDefinition,
) -> dict[str, object]:
    """QuizDefinition の正答のみで GAS 契約と同一形状の payload を組み立てる。"""
    answers = [
        {
            "question_index": question.index,
            "selected_answer": question.correct_answer,
            "is_correct": 1,
        }
        for question in quiz.questions
    ]
    return {
        "participant_id": participant_id,
        "timestamp": "2026-01-20T11:30:38",
        "score_numerator": len(answers),
        "score_denominator": len(answers),
        "answers": answers,
    }


def _lecture_1_correct_payload() -> dict[str, object]:
    return _all_correct_quiz_attempt_payload(
        participant_id="1",
        quiz=lecture_1.build_quiz_definition(),
    )


def _lecture_2_correct_payload() -> dict[str, object]:
    return _all_correct_quiz_attempt_payload(
        participant_id="2",
        quiz=lecture_2.build_quiz_definition(),
    )


def _lecture_3_correct_payload() -> dict[str, object]:
    return _all_correct_quiz_attempt_payload(
        participant_id="3",
        quiz=lecture_3.build_quiz_definition(),
    )


@pytest.mark.parametrize(
    ("payload_builder",),
    [
        (_lecture_1_correct_payload,),
        (_lecture_2_correct_payload,),
        (_lecture_3_correct_payload,),
    ],
)
def test_lecture_quiz_correct_payload_returns_201(
    phase2_client,
    payload_builder,
) -> None:
    """各講義の正答 payload で POST /api/quiz-attempts は 201 と attempt_id を返す。"""
    response = phase2_client.post(
        "/api/quiz-attempts",
        json=payload_builder(),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data is not None
    assert "attempt_id" in data
