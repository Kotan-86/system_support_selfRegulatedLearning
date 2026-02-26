"""
GAS 小テスト（quiz_form）との契約テスト。

GAS の onFormSubmit が POST /api/quiz-attempts に送る payload 形式で
リクエストしたときに 201 と attempt_id が返ることを保証する。
payload の形は quiz_form/quizForm.gs の送信形式と一致させること。
仕様変更時は .gs とこの payload を揃える。
"""

import pytest


def _gas_quiz_attempt_payload():
    """GAS quizForm.gs が送る想定の JSON と同一の形（5 問・4 択の Form 対応）。"""
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
    """GAS 送信形式で POST /api/quiz-attempts が受理されること。"""

    def test_gas_payload_returns_201_and_attempt_id(self, phase2_client) -> None:
        """GAS の onFormSubmit が送る想定の JSON で 201 と attempt_id が返る。"""
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = phase2_client.post(
            "/api/quiz-attempts",
            json=_gas_quiz_attempt_payload(),
            content_type="application/json",
        )
        assert r.status_code == 201, (
            "GAS 送信形式の payload で POST /api/quiz-attempts は 201 を返すこと"
        )
        data = r.get_json()
        assert data is not None
        assert "attempt_id" in data, "レスポンスに attempt_id を含むこと"
