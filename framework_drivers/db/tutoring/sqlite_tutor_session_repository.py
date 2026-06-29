# 仕様: docs/spec/framework-drivers-persistence.md#対話-dbtutordbとの接続
# 仕様: docs/spec/application-usecase.md#TutorSessionRepository
"""TutorSessionRepository の SQLite 実装。"""
from __future__ import annotations

import sqlite3

from application.tutoring.ports.tutor_session_repository import TutorSessionRepository
from domain.shared.ids import LearningSessionId, TutorSessionId
from domain.tutoring.tutor_session import TutorSession

from framework_drivers.db.tutoring.sqlite_tutor_session_mapper import (
    message_to_insert_params,
    rows_to_tutor_session,
    tutor_session_to_insert_params,
)


class SqliteTutorSessionRepository(TutorSessionRepository):
    """tutor.db 上の TutorSession 集約 Repository。"""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    def find_by_id(self, tutor_session_id: TutorSessionId) -> TutorSession | None:
        row = self._conn.execute(
            """
            SELECT id, created_at, participant_id, learning_session_id
            FROM sessions
            WHERE id = ?
            """,
            (str(tutor_session_id),),
        ).fetchone()
        if row is None:
            return None
        return self._load_session(TutorSessionId(str(row["id"])))

    def find_by_learning_session_id(
        self, learning_session_id: LearningSessionId
    ) -> TutorSession | None:
        row = self._conn.execute(
            """
            SELECT id
            FROM sessions
            WHERE learning_session_id = ?
            """,
            (str(learning_session_id),),
        ).fetchone()
        if row is None:
            return None
        return self._load_session(TutorSessionId(str(row["id"])))

    def list_all(self) -> tuple[TutorSession, ...]:
        rows = self._conn.execute(
            """
            SELECT id
            FROM sessions
            ORDER BY created_at ASC, id ASC
            """
        ).fetchall()
        return tuple(
            self._load_session(TutorSessionId(str(row["id"]))) for row in rows
        )

    def save(self, session: TutorSession) -> None:
        """集約を永続化する。Session upsert と未永続 Message の INSERT のみ行う。"""
        existing = self._conn.execute(
            "SELECT id FROM sessions WHERE id = ?",
            (str(session.id),),
        ).fetchone()
        if existing is None:
            self._conn.execute(
                """
                INSERT INTO sessions (id, created_at, participant_id, learning_session_id)
                VALUES (?, ?, ?, ?)
                """,
                tutor_session_to_insert_params(session),
            )

        current = self._load_session(session.id)
        for message in session.messages[len(current.messages) :]:
            self._conn.execute(
                """
                INSERT INTO messages (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                message_to_insert_params(message, session.id),
            )

        self._conn.commit()

    def _load_session(self, tutor_session_id: TutorSessionId) -> TutorSession:
        session_row = self._conn.execute(
            """
            SELECT id, created_at, participant_id, learning_session_id
            FROM sessions
            WHERE id = ?
            """,
            (str(tutor_session_id),),
        ).fetchone()
        if session_row is None:
            raise LookupError(f"TutorSession not found: {tutor_session_id}")

        message_rows = self._conn.execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (str(tutor_session_id),),
        ).fetchall()

        return rows_to_tutor_session(session_row, tuple(message_rows))
