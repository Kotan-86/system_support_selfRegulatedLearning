# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-5-講義動画フロント
# 仕様: docs/spec/interfaces-layer.md#ingress-規約
"""GET /lecture と視聴ログ payload 契約の API テスト。"""
from __future__ import annotations

import pytest


class TestLectureRoute:
    """GET /lecture の HTML 配信。"""

    def test_lecture_without_participant_id_returns_400(self, phase2_client) -> None:
        """participant_id なしは 400 と入力促し HTML を返す。"""
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        response = phase2_client.get("/lecture")
        assert response.status_code == 400
        html = response.get_data(as_text=True)
        assert "participant_id" in html
        assert "必要" in html or "必須" in html

    def test_lecture_with_participant_id_returns_200(self, phase2_client) -> None:
        """participant_id ありは 200 とプレイヤー要素を返す。"""
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        response = phase2_client.get("/lecture?participant_id=learner-42")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "learner-42" in html
        assert 'id="player"' in html
        assert "youtube.com/iframe_api" in html
        assert "/static/js/lecture/player.js" in html

    def test_lecture_static_js_is_served(self, phase2_client) -> None:
        """講義用 JS が static から配信される。"""
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        for path in (
            "/static/js/common/participant_context.js",
            "/static/js/common/api_client.js",
            "/static/js/lecture/player.js",
        ):
            response = phase2_client.get(path)
            assert response.status_code == 200, path


def _gas_viewing_log_payload(*, participant_id: str, action: str, duration: float):
    """player.js / GAS buildViewingLogPayload と同一形状。"""
    return {
        "participant_id": participant_id,
        "time_stamp": "2026-02-23T11:18:42.000Z",
        "current_time": 120,
        "action": action,
        "duration": duration,
    }


class TestLectureViewingLogActions:
    """play / pause / skip / seek が GAS 契約 payload で 201 を返す。"""

    @pytest.mark.parametrize(
        ("action", "duration"),
        [
            ("play", 0.0),
            ("pause", 0.0),
            ("forward_skip", 5.0),
            ("backward_skip", -5.0),
            ("forward_seek", 10.0),
            ("backward_seek", -10.0),
        ],
    )
    def test_viewing_action_returns_201(
        self, phase2_client, action: str, duration: float
    ) -> None:
        if phase2_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        payload = _gas_viewing_log_payload(
            participant_id=f"lecture-action-{action}",
            action=action,
            duration=duration,
        )
        response = phase2_client.post(
            "/api/viewing-log",
            json=payload,
            content_type="application/json",
        )
        assert response.status_code == 201, (
            f"action={action!r} の payload は 201 を返すこと"
        )
