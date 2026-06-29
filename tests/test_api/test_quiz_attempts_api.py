"""
Phase 2 Step 2.1: POST /api/quiz-attempts

小テスト 1 試行を JSON で受け取り、学習データ用 DB に保存する。
成功時 201 と attempt_id、必須項目欠損時 400 を期待する。
"""

import pytest


def _valid_payload():
    return {
        "participant_id": "1",
        "timestamp": "2026-02-23T12:00:00",
        "score_numerator": 4,
        "score_denominator": 5,
        "answers": [
            {"question_index": 1, "selected_answer": "A", "is_correct": 1},
            {"question_index": 2, "selected_answer": "B", "is_correct": 0},
        ],
    }


class TestPostQuizAttempts:
    """POST /api/quiz-attempts の振る舞い。"""

    def test_quiz_attempts_accepts_valid_json_returns_201(
        self, phase2_client
    ) -> None:
        """必須項目を満たす JSON を送ると 201 と attempt_id を返す。"""
        r = phase2_client.post(
            "/api/quiz-attempts",
            json=_valid_payload(),
            content_type="application/json",
        )
        assert r.status_code == 201, (
            "POST /api/quiz-attempts は成功時 201 を返すこと"
        )
        data = r.get_json()
        assert data is not None
        assert "attempt_id" in data, "レスポンスに attempt_id を含むこと"

    def test_quiz_attempts_missing_participant_id_returns_400(
        self, phase2_client
    ) -> None:
        """participant_id を欠くと 400 を返す。"""
        payload = _valid_payload()
        del payload["participant_id"]
        r = phase2_client.post(
            "/api/quiz-attempts",
            json=payload,
            content_type="application/json",
        )
        assert r.status_code == 400, (
            "必須項目欠損時は 400 を返すこと"
        )
