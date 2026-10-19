# 仕様: docs/spec/research-dialog-download.md#受入基準 (R4 R5 R7 R9)
# 仕様: docs/spec/research-dialog-download.md#json-の形
"""SqliteDialogLogExportQuery: 2つの DB(tutor.db・learning.db)を読むだけで、研究用の対話セッションを返す。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from application.tutoring.dto.save_dialog_log import EndMethod
from domain.tutoring.message import MessageRole
from framework_drivers.db.tutoring.sqlite_dialog_log_export_query import (
    SqliteDialogLogExportQuery,
)

T0 = datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)
STATE_JSON = json.dumps(
    {
        "task_understanding": {"status": "hypothesized", "note": "小テスト問3を曖昧に記憶"},
        "answer_rationale": {"status": "unknown", "note": ""},
        "felt_dissonance": {"status": "unknown", "note": ""},
        "domain_connection": {"status": "unknown", "note": ""},
        "process_memory": {"status": "unknown", "note": ""},
        "lad_connection": {"status": "unknown", "note": ""},
        "ai_hypotheses": {"status": "unknown", "note": ""},
        "learner_load": {"status": "unknown", "note": ""},
    },
    ensure_ascii=False,
)


class Db:
    """テスト用に tutor.db・learning.db へ行を直接入れる(実装の書き込みコードは使わない)。"""

    def __init__(self, tutor: sqlite3.Connection, learning: sqlite3.Connection) -> None:
        self.tutor = tutor
        self.learning = learning

    def learning_session(self, ls_id: str, learner: str, lecture: str = "lecture-1") -> None:
        self.learning.execute(
            "INSERT INTO learning_sessions (id, learner_id, lecture_id, started_at) VALUES (?,?,?,?)",
            (ls_id, learner, lecture, T0.isoformat()),
        )
        self.learning.commit()

    def tutor_session(self, ts_id: str, ls_id: str, created_at: str) -> None:
        # tutor.db の sessions.participant_id は常に空文字(参加者は learning.db 側)
        self.tutor.execute(
            "INSERT INTO sessions (id, created_at, participant_id, learning_session_id) VALUES (?,?,?,?)",
            (ts_id, created_at, "", ls_id),
        )
        self.tutor.commit()

    def message(
        self,
        ts_id: str,
        role: str,
        content: str,
        created_at: str,
        *,
        responded_at: str | None = None,
        utterance_type: str | None = None,
        dialogue_move: str | None = None,
        interpretation_state: str | None = None,
    ) -> None:
        self.tutor.execute(
            "INSERT INTO messages (session_id, role, content, created_at, utterance_type, "
            "dialogue_move, interpretation_state, responded_at) VALUES (?,?,?,?,?,?,?,?)",
            (ts_id, role, content, created_at, utterance_type, dialogue_move,
             interpretation_state, responded_at),
        )
        self.tutor.commit()

    def dialog_log(self, ts_id: str, pid: str, lecture: str, ls_id: str,
                   method: str, ended_at: str, log_json: str = "{}") -> None:
        self.tutor.execute(
            "INSERT INTO dialog_logs (session_id, participant_id, lecture_id, learning_session_id, "
            "end_method, ended_at, log_json) VALUES (?,?,?,?,?,?,?)",
            (ts_id, pid, lecture, ls_id, method, ended_at, log_json),
        )
        self.tutor.commit()

    def conversation(self, pid: str, ts_id: str, created_at: str = "2026-09-29T01:00:00+00:00",
                     lecture: str = "lecture-1") -> str:
        """学習セッション ls-<pid>-<lecture>、対話セッション ts_id、2往復を作る。"""
        ls_id = f"ls-{pid}-{lecture}"
        existing = self.learning.execute("SELECT 1 FROM learning_sessions WHERE id=?", (ls_id,)).fetchone()
        if existing is None:
            self.learning_session(ls_id, pid, lecture)
        self.tutor_session(ts_id, ls_id, created_at)
        self.message(ts_id, "user", f"{pid}の質問1", "2026-09-29T01:00:00+00:00")
        self.message(ts_id, "assistant", f"{pid}の回答1", "2026-09-29T01:00:00+00:00",
                     responded_at="2026-09-29T01:00:07+00:00", utterance_type="FACT_REQUEST",
                     dialogue_move="ELICIT_REASON", interpretation_state=STATE_JSON)
        self.message(ts_id, "user", f"{pid}の質問2", "2026-09-29T01:01:00+00:00")
        self.message(ts_id, "assistant", f"{pid}の回答2", "2026-09-29T01:01:00+00:00",
                     responded_at="2026-09-29T01:01:09+00:00", utterance_type="VAGUE_MEMORY",
                     dialogue_move="JOINT_EVIDENCE_CHECK", interpretation_state=STATE_JSON)
        return ls_id


@pytest.fixture
def db(tutor_db_conn: sqlite3.Connection, learning_db_conn: sqlite3.Connection) -> Db:
    return Db(tutor_db_conn, learning_db_conn)


@pytest.fixture
def query(tutor_db_conn, learning_db_conn) -> SqliteDialogLogExportQuery:
    return SqliteDialogLogExportQuery(
        tutor_connection=tutor_db_conn, learning_connection=learning_db_conn
    )


def _dump(conn: sqlite3.Connection) -> dict[str, list[tuple]]:
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    return {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2")] for t in tables}


class TestContents:
    def test_r4_identifiers_and_messages_match_the_database(self, db, query) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R4
        ls_id = db.conversation("1", "ts-1")
        db.conversation("2", "ts-2")

        (log,) = query.list_for_participant("1")

        assert log.participant_id == "1"
        assert log.lecture_id == "lecture-1"
        assert log.learning_session_id == ls_id
        assert log.tutor_session_id == "ts-1"
        assert [(m.role, m.content) for m in log.messages] == [
            (MessageRole.USER, "1の質問1"),
            (MessageRole.ASSISTANT, "1の回答1"),
            (MessageRole.USER, "1の質問2"),
            (MessageRole.ASSISTANT, "1の回答2"),
        ]

    def test_r4_message_times_and_pipeline_metadata_are_read_from_messages(self, db, query) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R4(内部判断は messages の値と一致)
        db.conversation("1", "ts-1")

        (log,) = query.list_for_participant("1")

        user, assistant = log.messages[0], log.messages[1]
        assert user.created_at == datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)
        assert assistant.responded_at == datetime(2026, 9, 29, 1, 0, 7, tzinfo=timezone.utc)
        assert assistant.utterance_type is not None and assistant.utterance_type.value == "FACT_REQUEST"
        assert assistant.dialogue_move is not None and assistant.dialogue_move.value == "ELICIT_REASON"
        card = assistant.interpretation_state
        assert card is not None
        assert card.task_understanding.note == "小テスト問3を曖昧に記憶"
        assert user.responded_at is None

    def test_r4_other_participants_are_not_included(self, db, query) -> None:
        db.conversation("1", "ts-1")
        db.conversation("2", "ts-2")

        logs = query.list_for_participant("2")

        assert [log.participant_id for log in logs] == ["2"]
        assert all("1の" not in m.content for log in logs for m in log.messages)

    def test_r4_messages_are_ordered_by_created_at_then_id(self, db, query) -> None:
        # 仕様: docs/spec/research-dialog-download.md#json-の形(messages の読み出しの順)
        db.learning_session("ls-x", "7")
        db.tutor_session("ts-x", "ls-x", "2026-09-29T01:00:00+00:00")
        db.message("ts-x", "user", "後(id 小)", "2026-09-29T01:00:05+00:00")
        db.message("ts-x", "user", "先", "2026-09-29T01:00:01+00:00")
        db.message("ts-x", "assistant", "同時刻の1", "2026-09-29T01:00:09+00:00")
        db.message("ts-x", "assistant", "同時刻の2", "2026-09-29T01:00:09+00:00")

        (log,) = query.list_for_participant("7")

        assert [m.content for m in log.messages] == ["先", "後(id 小)", "同時刻の1", "同時刻の2"]

    def test_r5_one_participant_with_two_sessions_returns_both(self, db, query) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R5
        db.conversation("2", "ts-l2", lecture="lecture-2")
        db.conversation("2", "ts-l3", lecture="lecture-3")

        logs = query.list_for_participant("2")

        assert sorted((l.tutor_session_id, l.lecture_id) for l in logs) == [
            ("ts-l2", "lecture-2"),
            ("ts-l3", "lecture-3"),
        ]
        assert len({l.learning_session_id for l in logs}) == 2

    def test_r5_ended_info_comes_from_dialog_logs_or_none(self, db, query) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R5(保存した側は dialog_logs の値、していない側は None)
        ls2 = db.conversation("2", "ts-l2", lecture="lecture-2")
        db.conversation("2", "ts-l3", lecture="lecture-3")
        db.dialog_log("ts-l2", "2", "lecture-2", ls2, "page_leave", "2026-09-29T01:05:00+00:00")

        by_id = {l.tutor_session_id: l for l in query.list_for_participant("2")}

        saved, unsaved = by_id["ts-l2"], by_id["ts-l3"]
        assert saved.ended_at == datetime(2026, 9, 29, 1, 5, 0, tzinfo=timezone.utc)
        assert saved.end_method == EndMethod.PAGE_LEAVE
        assert unsaved.ended_at is None
        assert unsaved.end_method is None

    def test_r5_messages_added_after_saving_are_included_and_log_json_is_not_used(
        self, db, query
    ) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R5(保存の後に追加した発言も含む。log_json は使わない)
        ls_id = db.conversation("2", "ts-1")
        stale_log_json = json.dumps({"messages": [{"role": "user", "content": "古い内容"}]})
        db.dialog_log("ts-1", "2", "lecture-1", ls_id, "end_button",
                      "2026-09-29T01:02:00+00:00", log_json=stale_log_json)
        db.message("ts-1", "user", "保存後の質問", "2026-09-29T01:10:00+00:00")

        (log,) = query.list_for_participant("2")

        contents = [m.content for m in log.messages]
        assert contents[-1] == "保存後の質問"
        assert len(contents) == 5
        assert "古い内容" not in contents

    def test_r5_session_with_zero_messages_is_included(self, db, query) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R5(発言0件の参加者 3)
        db.learning_session("ls-3", "3")
        db.tutor_session("ts-3", "ls-3", "2026-09-29T01:00:00+00:00")
        db.dialog_log("ts-3", "3", "lecture-1", "ls-3", "end_button", "2026-09-29T01:00:30+00:00")

        (log,) = query.list_for_participant("3")

        assert log.tutor_session_id == "ts-3"
        assert log.messages == ()
        assert log.end_method == EndMethod.END_BUTTON

    def test_r6_list_all_includes_every_session_unsaved_ones_too(self, db, query) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R6(1・2・foo)
        db.conversation("1", "ts-1")
        db.conversation("2", "ts-2")
        db.conversation("foo", "ts-foo")

        logs = query.list_all()

        assert sorted((l.participant_id, l.tutor_session_id) for l in logs) == [
            ("1", "ts-1"),
            ("2", "ts-2"),
            ("foo", "ts-foo"),
        ]
        assert all(l.ended_at is None and l.end_method is None for l in logs)

    def test_r4_content_is_not_altered(self, db, query) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R4(本文は加工しない)
        db.learning_session("ls-9", "9")
        db.tutor_session("ts-9", "ls-9", "2026-09-29T01:00:00+00:00")
        body = '  前後の空白と\n改行、"引用符"、<b>タグ</b>、日本語、emoji🙂  '
        db.message("ts-9", "user", body, "2026-09-29T01:00:00+00:00")

        (log,) = query.list_for_participant("9")

        assert log.messages[0].content == body


class TestParticipantMatching:
    def test_r7_participant_id_is_exact_match_only(self, db, query) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R7 (Q6)
        db.conversation("1", "ts-1")

        for raw in (" 1", "1 ", " ", "", "01", "１"):
            assert query.list_for_participant(raw) == ()
        assert len(query.list_for_participant("1")) == 1

    def test_r7_case_is_distinguished(self, db, query) -> None:
        db.conversation("Foo", "ts-1")

        assert query.list_for_participant("foo") == ()
        assert len(query.list_for_participant("Foo")) == 1

    def test_r7_unknown_participant_and_empty_database_give_empty_tuples(self, db, query) -> None:
        assert query.list_all() == ()
        assert query.list_for_participant("nobody") == ()
        db.conversation("1", "ts-1")
        assert query.list_for_participant("nobody") == ()

    def test_r7_participant_id_with_sql_metacharacters_is_matched_literally(self, db, query) -> None:
        db.conversation("1", "ts-1")

        assert query.list_for_participant("1' OR '1'='1") == ()
        assert query.list_for_participant("%") == ()


class TestCreatedAt:
    def test_m2_created_at_is_always_utc_aware_even_when_stored_naive(self, db, query) -> None:
        # 設計 DR-001 M2: タイムゾーン無し(CURRENT_TIMESTAMP 形式)の値は UTC とみなす
        db.conversation("1", "ts-naive", created_at="2026-09-29 01:00:00")
        db.conversation("1", "ts-aware", created_at="2026-09-29T02:00:00+00:00")

        logs = {l.tutor_session_id: l for l in query.list_for_participant("1")}

        naive = logs["ts-naive"].tutor_session_created_at
        aware = logs["ts-aware"].tutor_session_created_at
        assert naive.tzinfo is not None and naive.utcoffset() == timedelta(0)
        assert aware.tzinfo is not None and aware.utcoffset() == timedelta(0)
        assert naive == datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)
        assert aware == datetime(2026, 9, 29, 2, 0, 0, tzinfo=timezone.utc)
        # 混在していても比較・並べ替えで例外にならない
        assert sorted([aware, naive]) == [naive, aware]

    def test_m2_list_all_with_mixed_timezones_is_comparable(self, db, query) -> None:
        db.conversation("1", "ts-naive", created_at="2026-09-29 01:00:00")
        db.conversation("2", "ts-aware", created_at="2026-09-29T02:00:00+00:00")

        times = [l.tutor_session_created_at for l in query.list_all()]

        assert len(times) == 2
        assert sorted(times)[0] == datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)


class TestReadOnly:
    def test_r9_calls_do_not_change_any_row_in_either_database(
        self, db, query, tutor_db_conn, learning_db_conn
    ) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R9(全表の行と値が変わらない)
        ls_id = db.conversation("1", "ts-1")
        db.conversation("2", "ts-2")
        db.dialog_log("ts-1", "1", "lecture-1", ls_id, "end_button", "2026-09-29T01:05:00+00:00")
        tutor_before, learning_before = _dump(tutor_db_conn), _dump(learning_db_conn)
        tutor_changes, learning_changes = tutor_db_conn.total_changes, learning_db_conn.total_changes

        query.list_all()
        query.list_for_participant("1")
        query.list_for_participant("nobody")

        assert _dump(tutor_db_conn) == tutor_before
        assert _dump(learning_db_conn) == learning_before
        assert tutor_db_conn.total_changes == tutor_changes
        assert learning_db_conn.total_changes == learning_changes
        assert not tutor_db_conn.in_transaction
        assert not learning_db_conn.in_transaction


class TestNoContentLeak:
    def test_m5_content_does_not_appear_in_stdout_or_stderr(self, db, query, capsys) -> None:
        # 設計 DR-001 M5 / R9: 本文を print 等に出さない
        db.learning_session("ls-s", "5")
        db.tutor_session("ts-s", "ls-s", "2026-09-29T01:00:00+00:00")
        db.message("ts-s", "user", "SECRET-MARKER-文字列", "2026-09-29T01:00:00+00:00")

        query.list_all()
        query.list_for_participant("5")

        captured = capsys.readouterr()
        assert "SECRET-MARKER" not in captured.out + captured.err

    def test_m5_content_does_not_appear_in_logger_output(self, db, query, caplog) -> None:
        db.learning_session("ls-s", "5")
        db.tutor_session("ts-s", "ls-s", "2026-09-29T01:00:00+00:00")
        db.message("ts-s", "user", "SECRET-MARKER-文字列", "2026-09-29T01:00:00+00:00")

        with caplog.at_level("DEBUG"):
            query.list_all()
            query.list_for_participant("5")

        assert "SECRET-MARKER" not in caplog.text
