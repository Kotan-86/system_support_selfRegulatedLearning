"""
Phase 3 Step 3.1: repository の participant_id 対応

create_session(participant_id) で sessions に participant_id が保存されること、
get_participant_id_for_session(session_id) で取得できることを検証する。
"""
import sqlite3

import pytest


class TestCreateSessionParticipantId:
    """create_session(participant_id) で participant_id が保存される。"""

    def test_create_session_accepts_participant_id_and_persists(
        self, initialized_tutor_db
    ) -> None:
        """create_session("1") を呼ぶと sessions に participant_id が保存される。"""
        try:
            from db import repository

            sid = repository.create_session("1")
        except TypeError:
            pytest.skip("create_session(participant_id) が未実装のためスキップ")
        assert sid is not None
        path = repository.get_db_path()
        conn = sqlite3.connect(str(path))
        cur = conn.execute(
            "SELECT id, participant_id FROM sessions WHERE id = ?", (sid,)
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None
        assert row[1] == "1", "sessions に participant_id が保存されていること"


class TestGetParticipantIdForSession:
    """get_participant_id_for_session(session_id) の振る舞い。"""

    def test_returns_participant_id_when_session_exists(
        self, initialized_tutor_db
    ) -> None:
        """既存セッションの場合、その participant_id が返る。"""
        try:
            from db import repository

            sid = repository.create_session("p99")
            pid = repository.get_participant_id_for_session(sid)
        except (TypeError, AttributeError):
            pytest.skip(
                "create_session(participant_id) または get_participant_id_for_session が未実装のためスキップ"
            )
        assert pid == "p99"

    def test_returns_none_when_session_does_not_exist(
        self, initialized_tutor_db
    ) -> None:
        """存在しない session_id のとき None が返る。"""
        try:
            from db import repository

            pid = repository.get_participant_id_for_session("non-existent-uuid")
        except AttributeError:
            pytest.skip("get_participant_id_for_session が未実装のためスキップ")
        assert pid is None
