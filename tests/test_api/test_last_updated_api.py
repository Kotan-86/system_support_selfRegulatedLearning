"""
Phase 2 Step 2.3: GET /api/last-updated

学習データ用 DB の最終更新時刻を返す。
JSON に last_updated キーがあること、データが無い場合は null でもよいことを期待する。
"""

import pytest

from tests.login_helpers import login_as


class TestGetLastUpdated:
    """GET /api/last-updated の振る舞い。"""

    def test_last_updated_returns_200_and_json(self, phase2_client) -> None:
        """GET /api/last-updated は 200 と JSON を返す。"""
        r = phase2_client.get("/api/last-updated")
        assert r.status_code == 200, (
            "GET /api/last-updated は 200 を返すこと"
        )
        data = r.get_json()
        assert data is not None
        assert "last_updated" in data, (
            "レスポンスに last_updated キーがあること（値は null 可）"
        )

    def test_last_updated_without_participant_id_returns_own_time(
        self, phase2_client
    ) -> None:
        """AC14(participant-login): participant_id を省略すると、ログインした本人の最終更新時刻を返す。

        (旧: 未指定なら last_updated は null。AC14 で「null ではなく本人の時刻」に変わった。)
        """
        # 仕様: docs/spec/participant-login.md#受入基準
        login_as(phase2_client, "A")
        r = phase2_client.post(
            "/api/viewing-log",
            json={
                "participant_id": "A",
                "time_stamp": "2026-02-23T11:18:42",
                "current_time": 10,
                "action": "play",
                "duration": 0,
            },
        )
        assert r.status_code == 201
        explicit = phase2_client.get("/api/last-updated?participant_id=A").get_json()
        assert explicit["last_updated"] is not None

        omitted = phase2_client.get("/api/last-updated")
        assert omitted.status_code == 200
        assert omitted.get_json()["last_updated"] == explicit["last_updated"]
