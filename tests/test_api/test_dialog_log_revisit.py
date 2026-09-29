"""
PBI-A-2 (11-T6): 再訪(終了後に同じ URL を開き直す)の保存内容。

仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-2) A16
「開き直す」= ページを新規に読み込むこと。画面は session_id を持ち越さないので、再訪後の送信は session_id なしで送られる。
それを、`session_id` なしの POST /chat と POST /api/dialog-log で再現する。
通常の画面が表示されること(見た目)は PO確認。
"""
import json
import sqlite3
from pathlib import Path

import pytest

from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway

PID = "1"


@pytest.fixture
def revisit_env(monkeypatch, tmp_path: Path):
    llm = FakeLlmGateway(response="応答-1")
    monkeypatch.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
    monkeypatch.setenv("LEARNING_DB_PATH", str(tmp_path / "learning.db"))
    monkeypatch.setattr("framework_drivers.platform.wiring.build_llm_gateway", lambda: llm)
    from tests.test_interfaces.fakes.fake_video_duration_resolver import (
        FakeVideoDurationResolver,
    )

    monkeypatch.setattr(
        "framework_drivers.platform.wiring.build_video_duration_resolver",
        lambda: FakeVideoDurationResolver(duration_sec=600),
    )
    from framework_drivers.platform.main import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client(), llm, tmp_path / "tutor.db"


def _chat(client, message: str) -> dict:
    # 再訪後の画面と同じく session_id は付けない
    r = client.post("/chat", json={"message": message, "participant_id": PID})
    assert r.status_code == 200, r.get_data(as_text=True)
    return r.get_json()


def _save(client):
    return client.post(
        "/api/dialog-log", json={"participant_id": PID, "end_method": "end_button"}
    )


def _rows(db_path: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM dialog_logs").fetchall()
    finally:
        conn.close()


def test_a16_revisit_saves_same_session_with_both_visits_and_latest_ended_at(revisit_env) -> None:
    # 仕様: docs/spec/dialog-log-save.md#受入基準 A16(自動テスト部分)
    client, llm, db_path = revisit_env

    # 1回目の訪問: 送信 → 終了ボタン相当の保存
    first = _chat(client, "1回目の発言")
    llm.set_response("応答-2")
    r1 = _save(client)
    assert r1.status_code == 200, r1.get_data(as_text=True)
    session_id_1 = r1.get_json()["tutor_session_id"]
    assert session_id_1 == first["session_id"]
    assert len(_rows(db_path)) == 1

    # 1回目の ended_at を、2回目で置き換わったか判別できる値にする(時刻の分解能が秒のため)
    sentinel = "2000-01-01T00:00:00+00:00"
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE dialog_logs SET ended_at = ?", (sentinel,))
    conn.commit()
    conn.close()

    # 2回目の訪問(開き直し): session_id なしで送信 → 保存
    second = _chat(client, "2回目の発言")
    r2 = _save(client)
    assert r2.status_code == 200, r2.get_data(as_text=True)
    body2 = r2.get_json()

    assert second["session_id"] == first["session_id"], "再訪後の発言は1回目と同じ対話セッションに保存される"
    assert body2["tutor_session_id"] == session_id_1

    rows = _rows(db_path)
    assert len(rows) == 1, "対話ログは1件のまま(上書き)"
    row = rows[0]
    assert row["session_id"] == session_id_1
    assert row["end_method"] == "end_button"
    assert row["ended_at"] != sentinel, "ended_at は2回目の保存の時刻になる"
    assert row["ended_at"] == body2["ended_at"]

    log = json.loads(row["log_json"])
    assert log["tutor_session_id"] == session_id_1
    assert log["ended_at"] == body2["ended_at"]
    assert log["end_method"] == "end_button"
    assert [(m["role"], m["content"]) for m in log["messages"]] == [
        ("user", "1回目の発言"),
        ("assistant", "応答-1"),
        ("user", "2回目の発言"),
        ("assistant", "応答-2"),
    ], "発言の並びは1回目と2回目の訪問の発言を時系列の順にすべて含む"


def test_a16_revisit_after_empty_first_visit_keeps_single_log(revisit_env) -> None:
    # 仕様: docs/spec/dialog-log-save.md#受入基準 A16, A9(発言0件で終了 → 開き直して発言 → 再び終了)
    client, _llm, db_path = revisit_env
    r1 = _save(client)
    assert r1.status_code == 200, r1.get_data(as_text=True)
    sid = r1.get_json()["tutor_session_id"]
    assert json.loads(_rows(db_path)[0]["log_json"])["messages"] == []

    reply = _chat(client, "再訪の発言")
    assert reply["session_id"] == sid, "発言0件で作られた対話セッションに追加される"
    r2 = _save(client)
    assert r2.status_code == 200
    rows = _rows(db_path)
    assert len(rows) == 1
    msgs = json.loads(rows[0]["log_json"])["messages"]
    assert [(m["role"], m["content"]) for m in msgs] == [
        ("user", "再訪の発言"),
        ("assistant", "応答-1"),
    ]
