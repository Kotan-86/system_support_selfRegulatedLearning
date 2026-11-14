# 仕様: docs/spec/framework-drivers-persistence.md#repository-操作what
# 仕様: docs/spec/application-usecase.md#LearningSessionRepository
"""LearningSessionRepository の SQLite 実装（read + write）。"""
from __future__ import annotations

import sqlite3
from collections import defaultdict

from application.learning.ports.learning_session_repository import (
    LearningSessionRepository,
)
from domain.learning.learning_session import LearningSession
from domain.shared.ids import LectureId, LearnerId, LearningSessionId

from framework_drivers.db.learning.sqlite_learning_session_mapper import (
    learning_session_to_insert_params,
    quiz_answer_to_insert_params,
    quiz_attempt_to_insert_params,
    rows_to_learning_session,
    viewing_event_to_insert_params,
)


class SqliteLearningSessionRepository(LearningSessionRepository):
    """learning.db 上の LearningSession 集約 Repository。"""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    def find_by_learner_and_lecture(
        self, learner_id: LearnerId, lecture_id: LectureId
    ) -> LearningSession | None:
        row = self._conn.execute(
            """
            SELECT id, learner_id, lecture_id, started_at
            FROM learning_sessions
            WHERE learner_id = ? AND lecture_id = ?
            """,
            (str(learner_id), str(lecture_id)),
        ).fetchone()
        if row is None:
            return None
        return self._load_session(LearningSessionId(str(row["id"])))

    def list_by_learner(self, learner_id: LearnerId) -> tuple[LearningSession, ...]:
        rows = self._conn.execute(
            """
            SELECT id
            FROM learning_sessions
            WHERE learner_id = ?
            ORDER BY started_at ASC, id ASC
            """,
            (str(learner_id),),
        ).fetchall()
        return tuple(
            self._load_session(LearningSessionId(str(row["id"]))) for row in rows
        )

    def save(self, session: LearningSession) -> LearningSession:
        """集約を永続化する。Session upsert と未永続子行の INSERT のみ行う。"""
        existing = self._conn.execute(
            "SELECT id FROM learning_sessions WHERE id = ?",
            (str(session.id),),
        ).fetchone()
        if existing is None:
            self._conn.execute(
                """
                INSERT INTO learning_sessions (id, learner_id, lecture_id, started_at)
                VALUES (?, ?, ?, ?)
                """,
                learning_session_to_insert_params(session),
            )

        current = self._load_session(session.id)

        for event in session.viewing_events[len(current.viewing_events) :]:
            self._conn.execute(
                """
                INSERT INTO viewing_logs
                    (learning_session_id, time_stamp, "current_time", action, duration)
                VALUES (?, ?, ?, ?, ?)
                """,
                viewing_event_to_insert_params(event, session.id),
            )

        for attempt in session.quiz_attempts[len(current.quiz_attempts) :]:
            cursor = self._conn.execute(
                """
                INSERT INTO quiz_attempts
                    (learning_session_id, created_at, score_numerator, score_denominator)
                VALUES (?, ?, ?, ?)
                """,
                quiz_attempt_to_insert_params(attempt, session.id),
            )
            attempt_id = int(cursor.lastrowid)
            for answer in attempt.answers:
                self._conn.execute(
                    """
                    INSERT INTO quiz_attempt_answers
                        (attempt_id, question_index, selected_answer, is_correct)
                    VALUES (?, ?, ?, ?)
                    """,
                    quiz_answer_to_insert_params(answer, attempt_id),
                )

        self._conn.commit()
        return self._load_session(session.id)

    def save_if_learner_session_count(
        self, session: LearningSession, expected_count: int
    ) -> bool:
        """BEGIN IMMEDIATE で書き込みロックを先に取り、数の確認と INSERT を直列化する。"""
        self._conn.commit()
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            (count,) = self._conn.execute(
                "SELECT COUNT(*) FROM learning_sessions WHERE learner_id = ?",
                (str(session.learner_id),),
            ).fetchone()
            if count != expected_count:
                self._conn.rollback()
                return False
            self._conn.execute(
                """
                INSERT INTO learning_sessions (id, learner_id, lecture_id, started_at)
                VALUES (?, ?, ?, ?)
                """,
                learning_session_to_insert_params(session),
            )
            self._conn.commit()
        except BaseException:
            self._conn.rollback()
            raise
        return True

    def replace_if_no_records(
        self, current_id: LearningSessionId, session: LearningSession
    ) -> bool:
        """BEGIN IMMEDIATE の中で、記録がないことの確認と DELETE・INSERT を1つにする(選び直し)。

        視聴ログ・小テストの記録の要求も同じ書き込みロックを先に取る(main.py)ため、
        どちらか一方だけが成立し、消えた学習セッションを指す記録は残らない(AC14)。
        """
        self._conn.commit()
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            sid = str(current_id)
            exists = self._conn.execute(
                "SELECT 1 FROM learning_sessions WHERE id = ? AND learner_id = ?",
                (sid, str(session.learner_id)),
            ).fetchone()
            has_records = self._conn.execute(
                "SELECT EXISTS (SELECT 1 FROM viewing_logs WHERE learning_session_id = ?)"
                " OR EXISTS (SELECT 1 FROM quiz_attempts WHERE learning_session_id = ?)",
                (sid, sid),
            ).fetchone()[0]
            if exists is None or has_records:
                self._conn.rollback()
                return False
            self._conn.execute("DELETE FROM learning_sessions WHERE id = ?", (sid,))
            self._conn.execute(
                """
                INSERT INTO learning_sessions (id, learner_id, lecture_id, started_at)
                VALUES (?, ?, ?, ?)
                """,
                learning_session_to_insert_params(session),
            )
            self._conn.commit()
        except BaseException:
            self._conn.rollback()
            raise
        return True

    def _load_session(self, session_id: LearningSessionId) -> LearningSession:
        session_row = self._conn.execute(
            """
            SELECT id, learner_id, lecture_id, started_at
            FROM learning_sessions
            WHERE id = ?
            """,
            (str(session_id),),
        ).fetchone()
        if session_row is None:
            raise LookupError(f"LearningSession not found: {session_id}")

        viewing_rows = self._conn.execute(
            """
            SELECT id, learning_session_id, time_stamp, "current_time", action, duration
            FROM viewing_logs
            WHERE learning_session_id = ?
            ORDER BY time_stamp ASC, id ASC
            """,
            (str(session_id),),
        ).fetchall()

        attempt_rows = self._conn.execute(
            """
            SELECT id, learning_session_id, created_at, score_numerator, score_denominator
            FROM quiz_attempts
            WHERE learning_session_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (str(session_id),),
        ).fetchall()

        attempt_ids = [int(row["id"]) for row in attempt_rows]
        answers_by_attempt_id: dict[int, tuple[sqlite3.Row, ...]] = defaultdict(tuple)
        if attempt_ids:
            placeholders = ",".join("?" for _ in attempt_ids)
            answer_rows = self._conn.execute(
                f"""
                SELECT id, attempt_id, question_index, selected_answer, is_correct
                FROM quiz_attempt_answers
                WHERE attempt_id IN ({placeholders})
                ORDER BY attempt_id ASC, question_index ASC
                """,
                attempt_ids,
            ).fetchall()
            grouped: dict[int, list[sqlite3.Row]] = defaultdict(list)
            for row in answer_rows:
                grouped[int(row["attempt_id"])].append(row)
            answers_by_attempt_id = {
                attempt_id: tuple(rows) for attempt_id, rows in grouped.items()
            }

        return rows_to_learning_session(
            session_row,
            tuple(viewing_rows),
            tuple(attempt_rows),
            answers_by_attempt_id,
        )
