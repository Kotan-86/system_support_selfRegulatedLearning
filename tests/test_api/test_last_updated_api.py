"""
Phase 2 Step 2.3: GET /api/last-updated

学習データ用 DB の最終更新時刻を返す。
JSON に last_updated キーがあること、データが無い場合は null でもよいことを期待する。
"""

import pytest


class TestGetLastUpdated:
    """GET /api/last-updated の振る舞い。"""

    def test_last_updated_returns_200_and_json(self, phase2_client) -> None:
        """GET /api/last-updated は 200 と JSON を返す。"""
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = phase2_client.get("/api/last-updated")
        assert r.status_code == 200, (
            "GET /api/last-updated は 200 を返すこと"
        )
        data = r.get_json()
        assert data is not None
        assert "last_updated" in data, (
            "レスポンスに last_updated キーがあること（値は null 可）"
        )
