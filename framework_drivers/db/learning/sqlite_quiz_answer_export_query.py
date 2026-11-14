# 仕様: docs/spec/research-lad-csv-download.md#対象と並び順
"""研究用の小テスト回答読み出しの SQLite 実装。learning.db を SELECT するだけ(書き込み・commit なし)。"""
from __future__ import annotations

import sqlite3

from application.learning.dto.export_quiz_answers import ResearchQuizAnswerRow
from application.learning.ports.quiz_answer_export_query import QuizAnswerExportQuery

# 回答のない受験を落とさないため、回答は LEFT JOIN。
_SELECT = (
    "SELECT s.learner_id, s.lecture_id, s.id AS learning_session_id, "
    "q.id AS attempt_id, q.created_at, q.score_numerator, q.score_denominator, "
    "a.question_index, a.selected_answer, a.is_correct "
    "FROM quiz_attempts q JOIN learning_sessions s ON s.id = q.learning_session_id "
    "LEFT JOIN quiz_attempt_answers a ON a.attempt_id = q.id"
)


def _opt(value, cast):
    return None if value is None else cast(value)


class SqliteQuizAnswerExportQuery(QuizAnswerExportQuery):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def list_for_participant(self, participant_id: str) -> tuple[ResearchQuizAnswerRow, ...]:
        return self._fetch(_SELECT + " WHERE s.learner_id = ?", (participant_id,))

    def list_all(self) -> tuple[ResearchQuizAnswerRow, ...]:
        return self._fetch(_SELECT, ())

    def _fetch(self, sql: str, params: tuple) -> tuple[ResearchQuizAnswerRow, ...]:
        cursor = self._conn.cursor()
        cursor.row_factory = sqlite3.Row
        rows = cursor.execute(sql, params).fetchall()
        return tuple(
            ResearchQuizAnswerRow(
                participant_id=str(r["learner_id"]),
                lecture_id=str(r["lecture_id"]),
                learning_session_id=str(r["learning_session_id"]),
                attempt_id=int(r["attempt_id"]),
                attempted_at=str(r["created_at"]),
                score_numerator=int(r["score_numerator"]),
                score_denominator=int(r["score_denominator"]),
                question_index=_opt(r["question_index"], int),
                selected_answer=_opt(r["selected_answer"], str),
                is_correct=_opt(r["is_correct"], int),
            )
            for r in rows
        )
