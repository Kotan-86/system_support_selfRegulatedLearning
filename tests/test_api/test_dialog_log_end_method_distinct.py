"""終了ボタンの保存と離脱時の保存が end_method で区別できること。

仕様: docs/spec/dialog-log-save.md#受入基準 B5(PBI-B)
保存 API(PBI-A-1)の共有IFを、実装ではなく仕様の契約どおりに使う。LLM は偽物に差し替える。
"""

import json
import sqlite3
from pathlib import Path

import pytest

from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway


@pytest.fixture
def client_and_db(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
    monkeypatch.setenv("LEARNING_DB_PATH", str(tmp_path / "learning.db"))
    monkeypatch.setattr(
        "framework_drivers.platform.wiring.build_llm_gateway",
        lambda: FakeLlmGateway(response="スタブ応答"),
    )
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
    return app.test_client(), tmp_path / "tutor.db"


def _chat(client, pid: str, text: str) -> None:
    resp = client.post("/chat", json={"message": text, "participant_id": pid})
    assert resp.status_code == 200, resp.get_data(as_text=True)


def _log_rows(db: Path) -> dict[str, tuple[str, dict]]:
    """participant_id -> (列 end_method, log_json の解釈結果)"""
    con = sqlite3.connect(db)
    try:
        rows = con.execute(
            "SELECT participant_id, end_method, log_json FROM dialog_logs"
        ).fetchall()
    finally:
        con.close()
    return {pid: (em, json.loads(lj)) for pid, em, lj in rows}


def test_b5_end_button_and_page_leave_are_distinguishable(client_and_db) -> None:
    # 仕様: docs/spec/dialog-log-save.md#受入基準 B5
    client, db = client_and_db
    _chat(client, "1", "こんにちは")
    _chat(client, "2", "こんばんは")

    r1 = client.post("/api/dialog-log", json={"participant_id": "1", "end_method": "end_button"})
    r2 = client.post("/api/dialog-log", json={"participant_id": "2", "end_method": "page_leave"})
    assert r1.status_code == 200, r1.get_data(as_text=True)
    assert r2.status_code == 200, r2.get_data(as_text=True)
    assert r1.get_json()["end_method"] == "end_button"
    assert r2.get_json()["end_method"] == "page_leave"

    rows = _log_rows(db)
    assert set(rows) == {"1", "2"}
    col1, doc1 = rows["1"]
    col2, doc2 = rows["2"]
    assert (col1, doc1["end_method"]) == ("end_button", "end_button")
    assert (col2, doc2["end_method"]) == ("page_leave", "page_leave")
    # 発言の並びは同じ規則(user, assistant の順)で、区別は end_method だけに現れる
    assert [m["role"] for m in doc1["messages"]] == ["user", "assistant"]
    assert [m["role"] for m in doc2["messages"]] == ["user", "assistant"]


def test_b5_page_leave_after_end_button_overwrites_with_page_leave(client_and_db) -> None:
    # 仕様: docs/spec/dialog-log-save.md#受入基準 B5(同一対話セッション。上書き規則は A12)
    client, db = client_and_db
    _chat(client, "1", "こんにちは")
    first = client.post("/api/dialog-log", json={"participant_id": "1", "end_method": "end_button"})
    assert first.status_code == 200, first.get_data(as_text=True)
    assert _log_rows(db)["1"][0] == "end_button"
    second = client.post("/api/dialog-log", json={"participant_id": "1", "end_method": "page_leave"})
    assert second.status_code == 200, second.get_data(as_text=True)
    col, doc = _log_rows(db)["1"]
    assert (col, doc["end_method"]) == ("page_leave", "page_leave")
