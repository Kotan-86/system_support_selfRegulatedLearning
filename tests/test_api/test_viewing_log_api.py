"""
Phase 2 Step 2.2: POST /api/viewing-log

視聴ログ 1 件を JSON で受け取り、学習データ用 DB に保存する。
成功時 201 を期待する。
"""

import pytest

from tests.login_helpers import login_as


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
        login_as(phase2_client, "truncate-test")
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
        data = lad.get_json()
        assert data is not None
        assert data["action_counts"].get("forward_seek") == 1


# ---------------------------------------------------------------------------
# 講義ID付きの視聴ログ (PBI #33)
# 仕様: docs/spec/humanities-lectures.md#受入基準 AC17(サーバー側)・AC20(後方互換)
# ---------------------------------------------------------------------------
import os  # noqa: E402
import sqlite3  # noqa: E402


def _viewing_log_lectures(participant_id: str) -> list[str]:
    conn = sqlite3.connect(os.environ["LEARNING_DB_PATH"])
    try:
        return sorted(
            r[0]
            for r in conn.execute(
                "SELECT s.lecture_id FROM viewing_logs v "
                "JOIN learning_sessions s ON s.id = v.learning_session_id "
                "WHERE s.learner_id = ?",
                (participant_id,),
            )
        )
    finally:
        conn.close()


@pytest.mark.parametrize("lecture_id", ["lecture-4", "lecture-5", "lecture-6", "lecture-2"])
def test_ac17_viewing_log_with_lecture_id_is_recorded_as_that_lecture(
    phase2_client, lecture_id: str
) -> None:
    """AC17: 講義ID付きの視聴ログは、その講義として記録される(P01 の固定割当は lecture-1)。"""
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC17
    login_as(phase2_client, "P01")
    payload = {**_valid_viewing_log_payload(), "participant_id": "P01", "lecture_id": lecture_id}
    response = phase2_client.post("/api/viewing-log", json=payload, content_type="application/json")
    assert response.status_code == 201, response.get_data(as_text=True)
    assert _viewing_log_lectures("P01") == [lecture_id]


def test_ac20_viewing_log_without_lecture_id_uses_fixed_assignment(phase2_client) -> None:
    """AC20: 講義IDなしの視聴ログは、従来どおり固定割当(P01 は lecture-1)で記録される。"""
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC20
    login_as(phase2_client, "P01")
    payload = {**_valid_viewing_log_payload(), "participant_id": "P01"}
    assert phase2_client.post("/api/viewing-log", json=payload).status_code == 201
    assert _viewing_log_lectures("P01") == ["lecture-1"]


def test_ac20_participant_3_without_lecture_id_is_lecture_3(phase2_client) -> None:
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC20, AC13(b)
    login_as(phase2_client, "3")
    payload = {**_valid_viewing_log_payload(), "participant_id": "3"}
    assert phase2_client.post("/api/viewing-log", json=payload).status_code == 201
    assert _viewing_log_lectures("3") == ["lecture-3"]
