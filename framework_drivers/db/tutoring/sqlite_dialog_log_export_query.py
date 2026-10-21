# 仕様: docs/spec/research-dialog-download.md#json-の形
# 仕様: docs/spec/research-dialog-download.md#受入基準 (R4 R5 R6 R7 R9)
"""研究用の対話ログ読み出しの SQLite 実装。

tutor.db と learning.db を SELECT するだけで、書き込み・commit はしない。
参加者ID・lecture_id は learning.db の learning_sessions から、対話セッションと発言は
tutor.db から、終了情報は dialog_logs の列から読む(log_json は使わない)。
例外の文言に発言の本文・interpretation_state の値を入れない。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from application.tutoring.dto.export_dialog_logs import ResearchDialogLog
from application.tutoring.dto.save_dialog_log import EndMethod
from application.tutoring.ports.dialog_log_export_query import DialogLogExportQuery
from domain.tutoring.message import Message
from framework_drivers.db.learning.sqlite_learning_session_mapper import parse_datetime
from framework_drivers.db.tutoring.sqlite_tutor_session_mapper import (
    message_row_to_message,
)


def _as_utc_aware(value: datetime) -> datetime:
    """タイムゾーン無しの値は UTC とみなす。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class SqliteDialogLogExportQuery(DialogLogExportQuery):
    def __init__(
        self,
        *,
        tutor_connection: sqlite3.Connection,
        learning_connection: sqlite3.Connection,
    ) -> None:
        self._tutor = tutor_connection
        self._learning = learning_connection

    def list_for_participant(self, participant_id: str) -> tuple[ResearchDialogLog, ...]:
        cursor = self._learning.cursor()
        cursor.row_factory = sqlite3.Row
        rows = cursor.execute(
            "SELECT id, learner_id, lecture_id FROM learning_sessions WHERE learner_id = ?",
            (participant_id,),
        ).fetchall()
        return self._build(rows)

    def list_all(self) -> tuple[ResearchDialogLog, ...]:
        cursor = self._learning.cursor()
        cursor.row_factory = sqlite3.Row
        rows = cursor.execute(
            "SELECT id, learner_id, lecture_id FROM learning_sessions"
        ).fetchall()
        return self._build(rows)

    def _build(self, learning_rows: list[sqlite3.Row]) -> tuple[ResearchDialogLog, ...]:
        owners = {str(r["id"]): (str(r["learner_id"]), str(r["lecture_id"])) for r in learning_rows}
        if not owners:
            return ()

        cursor = self._tutor.cursor()
        cursor.row_factory = sqlite3.Row
        sessions = cursor.execute(
            "SELECT id, created_at, learning_session_id FROM sessions"
        ).fetchall()
        ended = {
            str(r["session_id"]): (r["ended_at"], r["end_method"])
            for r in cursor.execute(
                "SELECT session_id, ended_at, end_method FROM dialog_logs"
            ).fetchall()
        }

        logs: list[ResearchDialogLog] = []
        for session in sessions:
            owner = owners.get(str(session["learning_session_id"]))
            if owner is None:
                continue
            session_id = str(session["id"])
            message_rows = cursor.execute(
                "SELECT id, role, content, created_at, utterance_type, dialogue_move, "
                "interpretation_state, responded_at FROM messages "
                "WHERE session_id = ? ORDER BY created_at ASC, id ASC",
                (session_id,),
            ).fetchall()
            messages: tuple[Message, ...] = tuple(
                message_row_to_message(row) for row in message_rows
            )
            ended_raw, method_raw = ended.get(session_id, (None, None))
            logs.append(
                ResearchDialogLog(
                    participant_id=owner[0],
                    lecture_id=owner[1],
                    learning_session_id=str(session["learning_session_id"]),
                    tutor_session_id=session_id,
                    tutor_session_created_at=_as_utc_aware(
                        parse_datetime(str(session["created_at"]))
                    ),
                    ended_at=(
                        _as_utc_aware(parse_datetime(str(ended_raw)))
                        if ended_raw not in (None, "")
                        else None
                    ),
                    end_method=(
                        EndMethod(str(method_raw)) if method_raw not in (None, "") else None
                    ),
                    messages=messages,
                )
            )
        return tuple(logs)
