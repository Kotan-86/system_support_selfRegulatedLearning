"""
POST /api/quiz-attempts の API 契約テスト。

小テスト payload 形式でリクエストしたときに 201 と attempt_id が返ることを保証する。
仕様変更時は interfaces 層 ingress 規約とこのテストの payload を揃える。
"""

import pytest


def _gas_quiz_attempt_payload():
    """POST /api/quiz-attempts の API 契約 JSON と同一の形（5 問・4 択）。"""
    return {
        "participant_id": "1",
        "timestamp": "2026-01-20T11:30:38",
        "score_numerator": 4,
        "score_denominator": 5,
        "answers": [
            {"question_index": 1, "selected_answer": "統計学の視点：データの分布", "is_correct": 1},
            {"question_index": 2, "selected_answer": "大きさと向き", "is_correct": 1},
            {"question_index": 3, "selected_answer": "2次元", "is_correct": 1},
            {"question_index": 4, "selected_answer": "1つのベクトルの終点を別のベクトルの始点に重ね、新たなベクトルを作る", "is_correct": 1},
            {"question_index": 5, "selected_answer": "スケーリング", "is_correct": 0},
        ],
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
