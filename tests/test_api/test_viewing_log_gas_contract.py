"""
POST /api/viewing-log の API 契約テスト。

視聴ログ payload 形式でリクエストしたときに 201 が返ることを保証する。
payload の形は framework_drivers/platform/static/js/common/api_client.js の
buildViewingLogPayload 出力と一致させること。
仕様変更時は api_client.js とこのテストの payload を揃える。
"""

import pytest


def _gas_viewing_log_payload():
    """POST /api/viewing-log の API 契約 JSON と同一の形。"""
    return {
        "participant_id": "1",
        "time_stamp": "2026-02-23T11:18:42.000Z",
        "current_time": 0,
        "action": "play",
        "duration": 0.0,
    }


class TestViewingLogGasContract:
    """API 契約形式で POST /api/viewing-log が受理されること。"""

    def test_gas_payload_returns_201(self, phase2_client) -> None:
        """契約 payload で 201 が返る。"""
        r = phase2_client.post(
            "/api/viewing-log",
            json=_gas_viewing_log_payload(),
            content_type="application/json",
        )
        assert r.status_code == 201, (
            "API 契約形式の payload で POST /api/viewing-log は 201 を返すこと"
        )
