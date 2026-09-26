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


def _use_video_duration(monkeypatch, duration_sec: int) -> None:
    from tests.test_interfaces.fakes.fake_video_duration_resolver import (
        FakeVideoDurationResolver,
    )

    monkeypatch.setattr(
        "framework_drivers.platform.wiring.build_video_duration_resolver",
        lambda: FakeVideoDurationResolver(duration_sec=duration_sec),
    )


class TestGetParticipantsLadOver10Min:
    """仕様: docs/spec/bugs/lad-video-segments-over-10min.md#受入基準 AC1 / AC2 / AC5 / AC7。"""

    def test_duration_818_returns_seven_dense_segments_with_operations_after_10min(
        self, phase2_client, monkeypatch
    ) -> None:
        _use_video_duration(monkeypatch, 818)
        for position, action in ((650, "pause"), (790, "play")):
            r = phase2_client.post(
                "/api/viewing-log",
                json={
                    "participant_id": "1",
                    "time_stamp": "2026-02-23T11:18:42",
                    "current_time": position,
                    "action": action,
                    "duration": 0,
                },
                content_type="application/json",
            )
            assert r.status_code == 201

        r = phase2_client.get("/api/participants/1/lad")

        assert r.status_code == 200
        data = r.get_json()
        assert set(data.keys()) == LAD_VIEW_MODEL_KEYS
        segments = data["video_segments"]
        assert [s["segment_start_sec"] for s in segments] == [
            0, 120, 240, 360, 480, 600, 720,
        ]
        by_start = {s["segment_start_sec"]: s["action_counts"] for s in segments}
        assert by_start[600]["pause"] == 1
        assert by_start[720]["play"] == 1
        assert sum(sum(s["action_counts"].values()) for s in segments) == sum(
            data["action_counts"].values()
        )

    def test_empty_snapshot_duration_818_returns_seven_zero_segments(
        self, phase2_client, monkeypatch
    ) -> None:
        _use_video_duration(monkeypatch, 818)

        r = phase2_client.get("/api/participants/1/lad")

        assert r.status_code == 200
        segments = r.get_json()["video_segments"]
        assert [s["segment_start_sec"] for s in segments] == [
            120 * i for i in range(7)
        ]
        assert all(sum(s["action_counts"].values()) == 0 for s in segments)

    def test_empty_snapshot_duration_600_returns_five_zero_segments(
        self, phase2_client
    ) -> None:
        r = phase2_client.get("/api/participants/1/lad")

        assert r.status_code == 200
        segments = r.get_json()["video_segments"]
        assert [s["segment_start_sec"] for s in segments] == [0, 120, 240, 360, 480]
