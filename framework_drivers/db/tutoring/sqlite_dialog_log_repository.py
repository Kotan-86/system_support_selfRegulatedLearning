# 仕様: docs/spec/dialog-log-save.md#tutordb-の表
"""DialogLogRepository の SQLite 実装。"""
from __future__ import annotations

import json
import sqlite3

from application.tutoring.dto.save_dialog_log import DialogLog
from application.tutoring.ports.dialog_log_repository import DialogLogRepository
from framework_drivers.db.learning.sqlite_learning_session_mapper import format_datetime
from framework_drivers.db.tutoring.dialog_log_json import dialog_log_to_json_dict

_UPSERT_SQL = """
INSERT INTO dialog_logs (
    session_id, participant_id, lecture_id, learning_session_id,
    end_method, ended_at, log_json
) VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(session_id) DO UPDATE SET
    participant_id = excluded.participant_id,
    lecture_id = excluded.lecture_id,
    learning_session_id = excluded.learning_session_id,
    end_method = excluded.end_method,
    ended_at = excluded.ended_at,
    log_json = excluded.log_json
"""


class SqliteDialogLogRepository(DialogLogRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def save(self, log: DialogLog) -> None:
        log_json = json.dumps(dialog_log_to_json_dict(log), ensure_ascii=False)
        try:
            self._conn.execute(
                _UPSERT_SQL,
                (
                    log.tutor_session_id,
                    log.participant_id,
                    log.lecture_id,
                    log.learning_session_id,
                    log.end_method.value,
                    format_datetime(log.ended_at),
                    log_json,
                ),
            )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
