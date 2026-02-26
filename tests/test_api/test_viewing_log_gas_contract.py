"""
GAS 講義動画プラットフォームとの契約テスト。

GAS の recordLog が POST /api/viewing-log に送る payload 形式で
リクエストしたときに 201 が返ることを保証する。
payload の形は gas/payload/buildViewingLogPayload.js の出力と一致させること。
仕様変更時は gas/lectureVideoPlatform.gs と gas/payload/ およびこのテストの payload を揃える。
"""

import pytest


def _gas_viewing_log_payload():
    """GAS buildViewingLogPayload が送る想定の JSON と同一の形。"""
    return {
        "participant_id": "1",
        "time_stamp": "2026-02-23T11:18:42.000Z",
        "current_time": 0,
        "action": "play",
        "duration": 0.0,
    }


class TestViewingLogGasContract:
    """GAS 送信形式で POST /api/viewing-log が受理されること。"""

    def test_gas_payload_returns_201(self, phase2_client) -> None:
        """GAS の recordLog が送る想定の JSON で 201 が返る。"""
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        r = phase2_client.post(
            "/api/viewing-log",
            json=_gas_viewing_log_payload(),
            content_type="application/json",
        )
        assert r.status_code == 201, (
            "GAS 送信形式の payload で POST /api/viewing-log は 201 を返すこと"
        )
