# 仕様: docs/spec/framework-drivers-layer.md#HTTP-契約
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-5-講義動画フロント
"""講義別小テストの正答 payload で POST /api/quiz-attempts が受理されること。"""
from __future__ import annotations

import pytest

from tests.login_helpers import login_as

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
    payload = payload_builder()
    login_as(phase2_client, str(payload["participant_id"]))
    response = phase2_client.post(
        "/api/quiz-attempts",
        json=payload,
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data is not None
    assert "attempt_id" in data


# ---------------------------------------------------------------------------
# 文系レベル3講義 lecture-4〜6 の小テスト送信 (PBI #33)
# 仕様: docs/spec/humanities-lectures.md#受入基準 AC6・AC18(サーバー側)・AC20(後方互換)
# 期待値は tests/test_lectures/humanities_data.py(仕様の付録A)。
# ---------------------------------------------------------------------------
import os  # noqa: E402
import sqlite3  # noqa: E402

from tests.test_lectures.humanities_data import (  # noqa: E402
    HUMANITIES_BY_ID,
    HUMANITIES_IDS,
    correct_answers_payload,
)


def _quiz_attempt_lectures(participant_id: str) -> list[str]:
    """記録された小テスト試行の講義ID(learning_sessions 経由)。"""
    conn = sqlite3.connect(os.environ["LEARNING_DB_PATH"])
    try:
        return sorted(
            r[0]
            for r in conn.execute(
                "SELECT s.lecture_id FROM quiz_attempts a "
                "JOIN learning_sessions s ON s.id = a.learning_session_id "
                "WHERE s.learner_id = ?",
                (participant_id,),
            )
        )
    finally:
        conn.close()


def _quiz_payload_for(lecture_id: str, *, with_lecture_id: bool = True) -> dict:
    lec = HUMANITIES_BY_ID[lecture_id]
    body: dict[str, object] = {
        "participant_id": "P01",
        "timestamp": "2026-10-26T11:30:38",
        "score_numerator": 5,
        "score_denominator": 5,
        "answers": correct_answers_payload(lec),
    }
    if with_lecture_id:
        body["lecture_id"] = lecture_id
    return body


@pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
def test_ac6_ac18_humanities_correct_answers_are_recorded_as_that_lecture(
    phase2_client, lecture_id: str
) -> None:
    """AC6・AC18(サーバー側): lecture-4〜6 の全問正解で 201 と attempt_id。試行の講義IDは指定した講義。"""
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC6, AC18
    login_as(phase2_client, "P01")
    response = phase2_client.post(
        "/api/quiz-attempts",
        json=_quiz_payload_for(lecture_id),
        content_type="application/json",
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    assert "attempt_id" in response.get_json()
    assert _quiz_attempt_lectures("P01") == [lecture_id]


def test_ac20_quiz_attempt_without_lecture_id_uses_fixed_assignment(phase2_client) -> None:
    """AC20・AC13(a): 講義IDなしの送信は、従来どおり固定割当(P01 は lecture-1)で記録される。"""
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC20
    login_as(phase2_client, "P01")
    payload = _quiz_payload_for("lecture-4", with_lecture_id=False)
    payload["answers"] = [
        {"question_index": i, "selected_answer": "x", "is_correct": 0} for i in range(1, 6)
    ]
    payload["score_numerator"] = 0
    response = phase2_client.post("/api/quiz-attempts", json=payload, content_type="application/json")
    assert response.status_code == 201
    assert _quiz_attempt_lectures("P01") == ["lecture-1"]


def test_ac20_participant_2_without_lecture_id_is_lecture_2(phase2_client) -> None:
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC20, AC13(b)
    login_as(phase2_client, "2")
    payload = _all_correct_quiz_attempt_payload(participant_id="2", quiz=lecture_2.build_quiz_definition())
    response = phase2_client.post("/api/quiz-attempts", json=payload, content_type="application/json")
    assert response.status_code == 201
    assert _quiz_attempt_lectures("2") == ["lecture-2"]
