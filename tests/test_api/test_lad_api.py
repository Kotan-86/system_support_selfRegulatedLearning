"""
Phase 2: GET /api/participants/{participant_id}/lad

指定参加者の LAD 用 ViewModel（LadDashboardViewModel）を返す。
空 Snapshot でも 200。旧 viewing_logs 生 dict は返さない。
"""

import pytest

LAD_VIEW_MODEL_KEYS = frozenset(
    {
        "action_counts",
        "video_segments",
        "quiz_results",
        "score",
        "learner_profile",
        "content_updated_at",
    }
)

LEGACY_LAD_KEYS = frozenset(
    {
        "viewing_logs",
        "latest_quiz_attempt",
        "quiz_answers",
    }
)


class TestGetParticipantsLad:
    """GET /api/participants/<participant_id>/lad の振る舞い。"""

    def test_lad_returns_200_and_lad_dashboard_view_model_keys(
        self, phase2_client
    ) -> None:
        """空 Snapshot でも 200 と LadDashboardViewModel キーを返す。"""
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = phase2_client.get("/api/participants/1/lad")
        assert r.status_code == 200, (
            "GET /api/participants/<id>/lad は 200 を返すこと"
        )
        data = r.get_json()
        assert data is not None
        assert set(data.keys()) == LAD_VIEW_MODEL_KEYS
        assert LEGACY_LAD_KEYS.isdisjoint(data.keys())
        assert isinstance(data["action_counts"], dict)
        assert isinstance(data["video_segments"], list)
        assert isinstance(data["quiz_results"], list)
        assert isinstance(data["learner_profile"], dict)
        assert data["content_updated_at"] is None
