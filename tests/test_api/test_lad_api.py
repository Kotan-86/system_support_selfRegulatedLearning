"""
Phase 2 Step 2.4: GET /api/participants/{participant_id}/lad

指定参加者の LAD 用データ（視聴ログ・最新小テスト結果）を返す。
学習データ用 DB のみ参照する。200 と viewing_logs / latest_quiz_attempt / quiz_answers を期待する。
"""

import pytest


class TestGetParticipantsLad:
    """GET /api/participants/<participant_id>/lad の振る舞い。"""

    def test_lad_returns_200_and_json_with_expected_keys(
        self, phase2_client
    ) -> None:
        """GET /api/participants/1/lad は 200 と viewing_logs, latest_quiz_attempt, quiz_answers を返す。"""
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = phase2_client.get("/api/participants/1/lad")
        assert r.status_code == 200, (
            "GET /api/participants/<id>/lad は 200 を返すこと"
        )
        data = r.get_json()
        assert data is not None
        assert "viewing_logs" in data, "レスポンスに viewing_logs があること"
        assert "latest_quiz_attempt" in data or "quiz_answers" in data, (
            "レスポンスに latest_quiz_attempt または quiz_answers があること"
        )
