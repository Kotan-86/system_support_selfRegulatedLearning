"""
永続化レイヤー（学習データ用）: 視聴ログ・小テスト結果の挿入と取得。
接続先は db.config.get_learning_db_path() のみ。対話用 DB は読まない。
"""
import sqlite3
from pathlib import Path

from db.config import get_learning_db_path


def _get_connection() -> sqlite3.Connection:
    """学習データ用 DB への接続を返す。"""
    path = get_learning_db_path()
    return sqlite3.connect(str(path))


def insert_quiz_attempt(
    participant_id: str,
    created_at: str,
    score_numerator: int,
    score_denominator: int,
    answers: list[dict],
) -> int:
    """
    quiz_attempts に 1 行 INSERT し、quiz_attempt_answers に各問 1 行ずつ INSERT する。
    返り値は発行した attempt_id（last rowid）。
    answers の各要素は question_index, selected_answer, is_correct を持つこと。
    """
    conn = _get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO quiz_attempts
               (participant_id, created_at, score_numerator, score_denominator)
               VALUES (?, ?, ?, ?)""",
            (participant_id, created_at, score_numerator, score_denominator),
        )
        conn.commit()
        attempt_id = cur.lastrowid
        if attempt_id is None:
            attempt_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for a in answers:
            conn.execute(
                """INSERT INTO quiz_attempt_answers
                   (attempt_id, question_index, selected_answer, is_correct)
                   VALUES (?, ?, ?, ?)""",
                (
                    attempt_id,
                    int(a["question_index"]),
                    a["selected_answer"],
                    1 if a.get("is_correct") else 0,
                ),
            )
        conn.commit()
        return attempt_id
    finally:
        conn.close()


def insert_viewing_log(
    participant_id: str,
    time_stamp: str,
    current_time: int,
    action: str,
    duration: int,
) -> None:
    """viewing_logs に 1 行 INSERT する。"""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO viewing_logs
               (participant_id, time_stamp, "current_time", action, duration)
               VALUES (?, ?, ?, ?, ?)""",
            (participant_id, time_stamp, current_time, action, duration),
        )
        conn.commit()
    finally:
        conn.close()


def insert_viewing_logs(events: list[dict]) -> None:
    """viewing_logs に複数件をまとめて INSERT する。各要素は participant_id, time_stamp, current_time, action, duration を持つ。"""
    if not events:
        return
    conn = _get_connection()
    try:
        conn.executemany(
            """INSERT INTO viewing_logs
               (participant_id, time_stamp, "current_time", action, duration)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (
                    e["participant_id"],
                    e["time_stamp"],
                    int(e["current_time"]),
                    e["action"],
                    int(float(e["duration"])),
                )
                for e in events
            ],
        )
        conn.commit()
    finally:
        conn.close()


def get_last_updated() -> str | None:
    """
    viewing_logs の MAX(time_stamp) と quiz_attempts の MAX(created_at) のうち
    新しい方を ISO 形式の文字列で返す。どちらにも 1 件も無ければ None。
    """
    conn = _get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """SELECT MAX(time_stamp) AS ts FROM viewing_logs"""
        )
        row = cur.fetchone()
        max_viewing = row["ts"] if row and row["ts"] else None
        cur = conn.execute(
            """SELECT MAX(created_at) AS ts FROM quiz_attempts"""
        )
        row = cur.fetchone()
        max_quiz = row["ts"] if row and row["ts"] else None
        if max_viewing is None and max_quiz is None:
            return None
        if max_viewing is None:
            return max_quiz
        if max_quiz is None:
            return max_viewing
        return max_viewing if max_viewing >= max_quiz else max_quiz
    finally:
        conn.close()


def get_lad_data_for_participant(participant_id: str) -> dict:
    """
    指定参加者の LAD 用データを返す。
    キー: viewing_logs（視聴ログ一覧）, latest_quiz_attempt（直近 1 試行）, quiz_answers（その試行の各問回答）。
    """
    conn = _get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """SELECT id, participant_id, time_stamp, "current_time", action, duration
               FROM viewing_logs WHERE participant_id = ? ORDER BY time_stamp ASC""",
            (participant_id,),
        )
        viewing_logs = [
            {**dict(row), "current_time": int(row["current_time"]), "duration": int(row["duration"])}
            for row in cur.fetchall()
        ]

        cur = conn.execute(
            """SELECT id, participant_id, created_at, score_numerator, score_denominator
               FROM quiz_attempts WHERE participant_id = ?
               ORDER BY created_at DESC LIMIT 1""",
            (participant_id,),
        )
        row = cur.fetchone()
        latest_quiz_attempt = dict(row) if row else None
        quiz_answers = []
        if latest_quiz_attempt:
            cur = conn.execute(
                """SELECT id, attempt_id, question_index, selected_answer, is_correct
                   FROM quiz_attempt_answers WHERE attempt_id = ? ORDER BY question_index ASC""",
                (latest_quiz_attempt["id"],),
            )
            quiz_answers = [dict(r) for r in cur.fetchall()]

        return {
            "viewing_logs": viewing_logs,
            "latest_quiz_attempt": latest_quiz_attempt,
            "quiz_answers": quiz_answers,
        }
    finally:
        conn.close()
