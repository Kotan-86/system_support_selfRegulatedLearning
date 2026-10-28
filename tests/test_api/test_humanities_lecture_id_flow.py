# 仕様: docs/spec/humanities-lectures.md#受入基準 (PBI #33) AC19(e)・AC20・AC21(b)(c)(d)
"""講義IDを付けた視聴ログ・小テスト・チャット・LAD・対話ログの保存を、API を通して確認する。

ログイン ID P01 が、param の講義を「選択した」状態(PBI #34)で、講義IDを付けた記録・保存が、その講義になる。
LLM は Fake。講義の選択(1人1講義)により、選択と異なる講義IDは 403(lecture-selection.md AC14)。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tests.login_helpers import build_app, dump_databases, login_as
from tests.test_lectures.humanities_data import HUMANITIES_BY_ID, correct_answers_payload

NEW_LECTURES = ["lecture-4", "lecture-5", "lecture-6"]


@pytest.fixture
def make_env(monkeypatch, tmp_path: Path):
    """P01 が lecture を選択した状態のクライアント一式を作る(1テストで1回)。"""

    def _make(lecture: str = "lecture-1"):
        app, llm = build_app(monkeypatch, tmp_path)
        client = app.test_client()
        login_as(client, "P01", lecture=lecture)
        return client, llm, tmp_path

    return _make


@pytest.fixture
def app_env(make_env):
    return make_env("lecture-1")


def _chat(client, lecture_id: str | None, message: str):
    body = {"message": message, "participant_id": "P01"}
    if lecture_id is not None:
        body["lecture_id"] = lecture_id
    return client.post("/chat", json=body)


def _dialog_logs(tmp_path: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(str(tmp_path / "tutor.db"))
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM dialog_logs ORDER BY session_id").fetchall()
    finally:
        conn.close()


# ---------------- AC19(e): LAD の講義ID指定 ----------------
@pytest.mark.parametrize("lecture_id", NEW_LECTURES)
def test_ac19e_lad_with_lecture_id_returns_that_lectures_viewing_and_quiz(
    make_env, lecture_id: str
) -> None:
    """AC19(e): P01 で講義ID付きの視聴ログと小テストを記録した後、lecture_id 付きの LAD はその結果を返す。"""
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC19(e)
    client, _llm, _tmp = make_env(lecture_id)
    lec = HUMANITIES_BY_ID[lecture_id]
    r1 = client.post(
        "/api/viewing-log",
        json={
            "participant_id": "P01", "lecture_id": lecture_id,
            "time_stamp": "2026-10-26T11:18:42", "current_time": 15, "action": "play", "duration": 0,
        },
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/api/quiz-attempts",
        json={
            "participant_id": "P01", "lecture_id": lecture_id, "timestamp": "2026-10-26T11:20:00",
            "score_numerator": 5, "score_denominator": 5, "answers": correct_answers_payload(lec),
        },
    )
    assert r2.status_code == 201

    lad = client.get(f"/api/participants/P01/lad?lecture_id={lecture_id}")
    assert lad.status_code == 200
    data = lad.get_json()
    assert data["action_counts"].get("play") == 1
    assert len(data["quiz_results"]) == 5
    assert data["content_updated_at"] is not None

    # 講義IDなしの LAD も、選択した講義の記録を返す(lecture-selection.md AC11)
    without = client.get("/api/participants/P01/lad").get_json()
    assert without["action_counts"].get("play") == 1
    assert len(without["quiz_results"]) == 5


# ---------------- AC21(b): 講義ID付きの対話ログの保存 ----------------
@pytest.mark.parametrize("end_method", ["end_button", "page_leave"])
@pytest.mark.parametrize("lecture_id", NEW_LECTURES + ["lecture-2"])
def test_ac21b_dialog_log_with_lecture_id_saves_that_lectures_conversation(
    make_env, lecture_id: str, end_method: str
) -> None:
    """AC21(b): 講義ID付きの /chat 2 回の後、講義ID付きの保存で、その講義の対話ログが 1 件・発言 4 件。"""
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC21(b)
    client, _llm, tmp_path = make_env(lecture_id)
    assert _chat(client, lecture_id, "質問1").status_code == 200
    assert _chat(client, lecture_id, "質問2").status_code == 200

    response = client.post(
        "/api/dialog-log",
        json={"participant_id": "P01", "lecture_id": lecture_id, "end_method": end_method},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert set(response.get_json()) == {"tutor_session_id", "ended_at", "end_method"}
    rows = _dialog_logs(tmp_path)
    assert len(rows) == 1, "対話ログは講義 1 件だけ(lecture-1 の空の対話ログを作らない)"
    log = json.loads(rows[0]["log_json"])
    assert rows[0]["lecture_id"] == lecture_id == log["lecture_id"]
    assert rows[0]["end_method"] == end_method == log["end_method"]
    assert [m["role"] for m in log["messages"]] == ["user", "assistant", "user", "assistant"]
    assert [m["content"] for m in log["messages"] if m["role"] == "user"] == ["質問1", "質問2"]


# ---------------- AC21(c)・AC13(d): 講義IDなしは選択済みの講義 ----------------
def test_ac21c_dialog_log_without_lecture_id_saves_selected_lecture(app_env) -> None:
    """AC21(c): 講義IDなしの保存は、選択した講義(P01 は lecture-1 を選択)で保存される。"""
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC21(c), AC13(d)
    client, _llm, tmp_path = app_env
    assert _chat(client, None, "質問").status_code == 200
    response = client.post("/api/dialog-log", json={"participant_id": "P01", "end_method": "end_button"})
    assert response.status_code == 200
    (row,) = _dialog_logs(tmp_path)
    assert row["lecture_id"] == "lecture-1"
    assert [m["role"] for m in json.loads(row["log_json"])["messages"]] == ["user", "assistant"]


# ---------------- AC21(d): 未登録の講義ID ----------------
@pytest.mark.parametrize("bad", ["lecture-7", "lecture-99"])
def test_ac21d_dialog_log_with_unregistered_lecture_id_is_403_and_changes_nothing(
    app_env, bad: str
) -> None:
    """AC21(d)(置き換え): 未登録の講義ID(lecture-7)は、選択と異なる値なので 403。対話ログも他の DB も変わらない。"""
    # 仕様: docs/spec/lecture-selection.md#受入基準 AC14(旧: humanities-lectures.md AC21(d) は 404)
    client, _llm, tmp_path = app_env
    assert _chat(client, None, "質問").status_code == 200  # 既存の状態を作る
    before = dump_databases(tmp_path)

    response = client.post(
        "/api/dialog-log",
        json={"participant_id": "P01", "lecture_id": bad, "end_method": "end_button"},
    )

    assert response.status_code == 403, response.get_data(as_text=True)
    assert dump_databases(tmp_path) == before
    assert _dialog_logs(tmp_path) == []


# ---------------- AC11 の前提(別ファイル test_chat_lad)ではなく、AC20: チャットの後方互換 ----------------
def test_ac20_chat_without_lecture_id_uses_selected_lecture(app_env) -> None:
    """AC20: 講義IDなしの /chat は選択した講義(P01 は lecture-1)の字幕で答える(プロンプトに lecture-1 の字幕)。"""
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC20
    client, llm, _tmp = app_env
    client.post(
        "/api/viewing-log",
        json={"participant_id": "P01", "time_stamp": "2026-10-26T11:18:42",
              "current_time": 15, "action": "play", "duration": 0},
    )
    llm.generate_calls.clear()
    assert _chat(client, None, "このあたりがわかりません").status_code == 200
    assert "整数倍" in llm.generate_calls[-1]  # lecture-1 の 15 秒付近の字幕(既存の test_srt_in_prompt と同じ根拠)
