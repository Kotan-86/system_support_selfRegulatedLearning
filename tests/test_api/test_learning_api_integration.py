"""
Phase 2 学習データ用 API の結合テスト。

視聴ログ登録 → 小テスト登録 → last-updated → LAD 取得の一連の流れで、
学習データ用 DB のみが参照・更新され、データが一貫して返ることを検証する。
"""

import pytest


@pytest.fixture
def viewing_log_payload():
    return {
        "participant_id": "1",
        "time_stamp": "2026-02-23T11:18:42",
        "current_time": 0,
        "action": "play",
        "duration": 0.0,
    }


@pytest.fixture
def quiz_attempt_payload():
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


class TestLearningApiIntegration:
    """視聴ログ・小テスト登録から LAD 取得までの一連の流れ。"""

    def test_post_viewing_log_then_post_quiz_then_last_updated_and_lad(
        self, phase2_client, viewing_log_payload, quiz_attempt_payload
    ) -> None:
        """
        1. POST /api/viewing-log で 1 件登録
        2. POST /api/quiz-attempts で 1 試行登録
        3. GET /api/last-updated で最終更新時刻が返る
        4. GET /api/participants/1/lad で視聴ログ・小テスト結果が返る
        """
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")

        client = phase2_client

        # 1. 視聴ログ 1 件
        r1 = client.post(
            "/api/viewing-log",
            json=viewing_log_payload,
            content_type="application/json",
        )
        assert r1.status_code == 201, "視聴ログ登録は 201"

        # 2. 小テスト 1 試行
        r2 = client.post(
            "/api/quiz-attempts",
            json=quiz_attempt_payload,
            content_type="application/json",
        )
        assert r2.status_code == 201, "小テスト登録は 201"
        data2 = r2.get_json()
        assert data2 is not None and "attempt_id" in data2

        # 3. 最終更新時刻
        r3 = client.get("/api/last-updated")
        assert r3.status_code == 200
        data3 = r3.get_json()
        assert data3 is not None and "last_updated" in data3
        assert data3["last_updated"] is not None, "1 件以上登録済みなら last_updated が入る"

        # 4. LAD データ
        r4 = client.get("/api/participants/1/lad")
        assert r4.status_code == 200
        data4 = r4.get_json()
        assert data4 is not None
        assert "viewing_logs" in data4
        assert len(data4["viewing_logs"]) == 1, "視聴ログが 1 件返る"
        assert data4["viewing_logs"][0]["action"] == "play"
        assert "latest_quiz_attempt" in data4
        assert data4["latest_quiz_attempt"] is not None
        assert data4["latest_quiz_attempt"]["score_numerator"] == 4
        assert data4["latest_quiz_attempt"]["score_denominator"] == 5
        assert "quiz_answers" in data4
        assert len(data4["quiz_answers"]) == 2, "小テスト回答が 2 問分返る"
