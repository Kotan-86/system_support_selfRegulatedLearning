# 仕様: docs/spec/multi-video-learning.md#制約関連機能(2つの DB にまたがる判定)
"""RoundRecordQuery の SQLite 実装(tutor.db を読むだけ。索引は足さない。AC23)。"""
from __future__ import annotations

import sqlite3
from collections.abc import Collection

from application.learning.ports.round_record_query import RoundRecordQuery
from application.tutoring.dto.save_dialog_log import EndMethod
from domain.shared.ids import LearningSessionId


class SqliteRoundRecordQuery(RoundRecordQuery):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def _matching(
        self, sql: str, ids: Collection[LearningSessionId], *params: str
    ) -> frozenset[LearningSessionId]:
        keys = [str(i) for i in ids]
        if not keys:
            return frozenset()
        placeholders = ",".join("?" for _ in keys)
        rows = self._conn.execute(sql.format(placeholders), (*params, *keys)).fetchall()
        return frozenset(LearningSessionId(str(row[0])) for row in rows)

    def ended_learning_session_ids(
        self, ids: Collection[LearningSessionId]
    ) -> frozenset[LearningSessionId]:
        return self._matching(
            "SELECT DISTINCT learning_session_id FROM dialog_logs"
            " WHERE end_method = ? AND learning_session_id IN ({})",
            ids,
            EndMethod.END_BUTTON.value,
        )

    def learning_session_ids_with_tutor_session(
        self, ids: Collection[LearningSessionId]
    ) -> frozenset[LearningSessionId]:
        return self._matching(
            "SELECT DISTINCT learning_session_id FROM sessions"
            " WHERE learning_session_id IN ({})",
            ids,
        )
