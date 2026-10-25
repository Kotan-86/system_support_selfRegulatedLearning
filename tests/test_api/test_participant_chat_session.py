# 仕様: docs/spec/participant-login.md#受入基準
# AC15(HTTP の層): 他人の対話セッションへの POST /chat
"""他人の `session_id` を使った POST /chat は、存在しないセッションと同じ 404 で拒否する(30-T3)。"""
from __future__ import annotations

import sqlite3

import pytest

from tests.login_helpers import build_app, dump_databases, login_as

ME = "A"
OTHER = "B"


@pytest.fixture
def world(monkeypatch, tmp_path):
    app, llm = build_app(monkeypatch, tmp_path)
    owner = app.test_client()
    intruder = app.test_client()
    login_as(owner, OTHER)
    login_as(intruder, ME)
    return owner, intruder, llm, tmp_path


def _message_count(tmp_path, session_id: str) -> int:
    conn = sqlite3.connect(str(tmp_path / "tutor.db"))
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
    finally:
        conn.close()


class TestAc15OtherParticipantsChatSession:
    def test_ac15_other_participants_session_id_is_404_and_message_count_is_unchanged(
        self, world
    ) -> None:
        owner, intruder, llm, tmp_path = world
        first = owner.post("/chat", json={"message": "Bの質問", "participant_id": OTHER})
        assert first.status_code == 200
        session_id = first.get_json()["session_id"]
        count_before = _message_count(tmp_path, session_id)
        assert count_before > 0
        before = dump_databases(tmp_path)
        llm_before = (len(llm.generate_calls), len(llm.generate_json_calls))

        response = intruder.post("/chat", json={"message": "Aが割り込む", "session_id": session_id})

        assert response.status_code == 404
        assert _message_count(tmp_path, session_id) == count_before
        assert dump_databases(tmp_path) == before
        assert (len(llm.generate_calls), len(llm.generate_json_calls)) == llm_before

    def test_ac15_the_response_is_the_same_as_for_a_nonexistent_session(self, world) -> None:
        owner, intruder, _, _ = world
        session_id = owner.post(
            "/chat", json={"message": "Bの質問", "participant_id": OTHER}
        ).get_json()["session_id"]

        other_session = intruder.post("/chat", json={"message": "x", "session_id": session_id})
        missing = intruder.post("/chat", json={"message": "x", "session_id": "no-such-session"})

        assert other_session.status_code == missing.status_code == 404
        assert other_session.get_json() == missing.get_json()

    def test_ac15_own_session_continues_as_before(self, world) -> None:
        owner, _, _, tmp_path = world
        session_id = owner.post(
            "/chat", json={"message": "最初", "participant_id": OTHER}
        ).get_json()["session_id"]
        count_before = _message_count(tmp_path, session_id)

        response = owner.post("/chat", json={"message": "続き", "session_id": session_id})

        assert response.status_code == 200
        assert response.get_json()["session_id"] == session_id
        assert _message_count(tmp_path, session_id) > count_before

    def test_ac15_foreign_session_with_own_participant_id_in_body_is_still_404(self, world) -> None:
        owner, intruder, _, tmp_path = world
        session_id = owner.post(
            "/chat", json={"message": "Bの質問", "participant_id": OTHER}
        ).get_json()["session_id"]
        count_before = _message_count(tmp_path, session_id)

        response = intruder.post(
            "/chat", json={"message": "x", "session_id": session_id, "participant_id": ME}
        )

        assert response.status_code == 404
        assert _message_count(tmp_path, session_id) == count_before
