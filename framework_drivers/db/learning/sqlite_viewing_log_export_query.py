# 仕様: docs/spec/research-lad-csv-download.md#対象と並び順
"""研究用の視聴ログ読み出しの SQLite 実装。learning.db を SELECT するだけ(書き込み・commit なし)。"""
from __future__ import annotations

import sqlite3

from application.learning.dto.export_viewing_logs import ResearchViewingLog
from application.learning.ports.viewing_log_export_query import ViewingLogExportQuery

_SELECT = (
    "SELECT s.learner_id, s.lecture_id, s.id AS learning_session_id, v.id AS viewing_log_id, "
    'v.time_stamp, v."current_time" AS current_pos, v.action, v.duration '
    "FROM viewing_logs v JOIN learning_sessions s ON s.id = v.learning_session_id"
)


class SqliteViewingLogExportQuery(ViewingLogExportQuery):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def list_for_participant(self, participant_id: str) -> tuple[ResearchViewingLog, ...]:
        return self._fetch(_SELECT + " WHERE s.learner_id = ?", (participant_id,))

    def list_all(self) -> tuple[ResearchViewingLog, ...]:
        return self._fetch(_SELECT, ())

    def _fetch(self, sql: str, params: tuple) -> tuple[ResearchViewingLog, ...]:
        cursor = self._conn.cursor()
        cursor.row_factory = sqlite3.Row
        rows = cursor.execute(sql, params).fetchall()
        return tuple(
            ResearchViewingLog(
                participant_id=str(r["learner_id"]),
                lecture_id=str(r["lecture_id"]),
                learning_session_id=str(r["learning_session_id"]),
                viewing_log_id=int(r["viewing_log_id"]),
                time_stamp=str(r["time_stamp"]),
                current_time=int(r["current_pos"]),
                action=str(r["action"]),
                duration=float(r["duration"]),
            )
            for r in rows
        )
