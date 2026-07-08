"""
POST /api/quiz-attempts の API 契約テスト。

小テスト payload 形式でリクエストしたときに 201 と attempt_id が返ることを保証する。
仕様変更時は interfaces 層 ingress 規約とこのテストの payload を揃える。
"""

import pytest

from framework_drivers.db.learning.quiz_definitions import lecture_1


def _gas_quiz_attempt_payload():
    """POST /api/quiz-attempts の API 契約 JSON と同一の形（lecture-1 正答・5 問）。"""
    quiz = lecture_1.build_quiz_definition()
    answers = [
        {
            "question_index": question.index,
            "selected_answer": question.correct_answer,
            "is_correct": 1,
        }
        for question in quiz.questions
    ]
    return {
        "participant_id": "1",
        "timestamp": "2026-01-20T11:30:38",
        "score_numerator": 5,
        "score_denominator": 5,
        "answers": answers,
    }


class TestQuizAttemptsGasContract:
    """API 契約形式で POST /api/quiz-attempts が受理されること。"""

    def test_gas_payload_returns_201_and_attempt_id(self, phase2_client) -> None:
        """契約 payload で 201 と attempt_id が返る。"""
        r = phase2_client.post(
            "/api/quiz-attempts",
            json=_gas_quiz_attempt_payload(),
            content_type="application/json",
        )
        assert r.status_code == 201, (
            "API 契約形式の payload で POST /api/quiz-attempts は 201 を返すこと"
        )
        data = r.get_json()
        assert data is not None
        assert "attempt_id" in data, "レスポンスに attempt_id を含むこと"
