"""
Phase 2 Step 2.2: POST /api/viewing-log

視聴ログ 1 件を JSON で受け取り、学習データ用 DB に保存する。
成功時 201 を期待する。
"""

import pytest


def _valid_viewing_log_payload():
    return {
        "participant_id": "1",
        "time_stamp": "2026-02-23T11:18:42",
        "current_time": 0,
        "action": "play",
        "duration": 0,
    }


class TestPostViewingLog:
    """POST /api/viewing-log の振る舞い。"""

    def test_viewing_log_accepts_valid_json_returns_201(
        self, phase2_client
    ) -> None:
        """必須項目を満たす JSON を送ると 201 を返す。"""
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = phase2_client.post(
            "/api/viewing-log",
            json=_valid_viewing_log_payload(),
            content_type="application/json",
        )
        assert r.status_code == 201, (
            "POST /api/viewing-log は成功時 201 を返すこと"
        )

    def test_viewing_log_truncates_fractional_seconds(
        self, phase2_client
    ) -> None:
        """current_time / duration の小数は 0 方向へ切り捨てて保存する。"""
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        payload = {
            "participant_id": "truncate-test",
            "time_stamp": "2026-02-23T11:18:42",
            "current_time": 90.9,
            "action": "forward_seek",
            "duration": 10.5,
        }
        r = phase2_client.post(
            "/api/viewing-log",
            json=payload,
            content_type="application/json",
        )
        assert r.status_code == 201

        lad = phase2_client.get("/api/participants/truncate-test/lad")
        assert lad.status_code == 200
        logs = lad.get_json()["viewing_logs"]
        assert len(logs) == 1
        assert logs[0]["current_time"] == 90
        assert logs[0]["duration"] == 10
