# 仕様: docs/spec/research-lad-csv-download.md#対象と並び順
# 仕様: docs/spec/research-lad-csv-download.md#何本目の列round_number共有if2つの-csv-に共通pbi-c決定-multi-video-learningmd-の-q7q-c1q-c42026-11-14
"""研究用の視聴ログ読み出しの SQLite 実装。learning.db を SELECT するだけ(書き込み・commit なし)。"""
from __future__ import annotations

import sqlite3

from application.learning.dto.export_viewing_logs import ResearchViewingLog
from application.learning.ports.viewing_log_export_query import ViewingLogExportQuery

# 何本目(round_number): 参加者の全学習セッションでの順位。記録のない学習セッションも数える。
# 開始時刻は時刻に直さず、保存された文字列のまま比べる(形の揃わない値でも失敗しない)。
# 定義は PBI-A の共有IF(started_at ASC, id ASC)と同じ。
ROUNDED_SESSIONS = (
    "(SELECT id, learner_id, lecture_id, ROW_NUMBER() OVER ("
    "PARTITION BY learner_id ORDER BY started_at ASC, id ASC) AS round_number "
    "FROM learning_sessions) s"
)

_SELECT = (
    "SELECT s.learner_id, s.round_number, s.lecture_id, s.id AS learning_session_id, v.id AS viewing_log_id, "
    'v.time_stamp, v."current_time" AS current_pos, v.action, v.duration '
    "FROM viewing_logs v JOIN " + ROUNDED_SESSIONS + " ON s.id = v.learning_session_id"
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
                round_number=int(r["round_number"]),
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
