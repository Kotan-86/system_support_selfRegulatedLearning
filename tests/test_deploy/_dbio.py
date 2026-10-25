# 仕様: docs/spec/db-persistence.md#受入基準
"""AC6 / AC8 が共有する、2つの DB への書き込み・読み出しの補助。

アプリの Repository(既存の実装)を通して書く。ジャーナルモードの操作は呼び出し側が行う。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from application.tutoring.dto.save_dialog_log import DialogLog, EndMethod
from domain.learning.learning_session import LearningSession
from domain.shared.ids import (
    LearnerId,
    LectureId,
    LearningSessionId,
    MessageId,
    TutorSessionId,
)
from domain.tutoring.message import MessageRole
from domain.tutoring.tutor_session import TutorSession
from framework_drivers.db.learning.sqlite_connection import connect_learning_db
from framework_drivers.db.learning.sqlite_learning_session_repository import (
    SqliteLearningSessionRepository,
)
from framework_drivers.db.tutoring.sqlite_connection import connect_tutor_db
from framework_drivers.db.tutoring.sqlite_dialog_log_repository import (
    SqliteDialogLogRepository,
)
from framework_drivers.db.tutoring.sqlite_tutor_session_repository import (
    SqliteTutorSessionRepository,
)

T0 = datetime(2026, 10, 26, 1, 0, 0, tzinfo=timezone.utc)
T7 = datetime(2026, 10, 26, 1, 0, 7, tzinfo=timezone.utc)
SAVED_AT = datetime(2026, 10, 26, 1, 5, 0, tzinfo=timezone.utc)

LEARNER = "learner-wal"
LECTURE = "lecture-1"
LEARNING_SESSION_ID = "ls-wal-1"
TUTOR_SESSION_ID = "ts-wal-1"
CONVERSATION = [("質問です", "回答です"), ("もう一つ質問", "もう一つの回答")]


def journal_mode(db_path: Path | str) -> str:
    conn = sqlite3.connect(str(db_path))
    try:
        return str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
    finally:
        conn.close()


def set_wal(db_path: Path | str) -> None:
    """DB を WAL モードにする(テストの前提づくり)。"""
    conn = sqlite3.connect(str(db_path))
    try:
        mode = str(conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]).lower()
        assert mode == "wal", f"WAL にできなかった: {mode}"
    finally:
        conn.close()


def write_sample_data(learning_db: Path | str, tutor_db: Path | str) -> None:
    """学習データ(視聴イベント付き)と対話データ(2往復と対話ログ)を書く。"""
    conn = connect_learning_db(learning_db)
    try:
        repo = SqliteLearningSessionRepository(conn)
        repo.save(
            LearningSession(
                id=LearningSessionId(LEARNING_SESSION_ID),
                learner_id=LearnerId(LEARNER),
                lecture_id=LectureId(LECTURE),
                started_at=T0,
            )
        )
        conn.commit()
    finally:
        conn.close()

    conn = connect_tutor_db(tutor_db)
    try:
        repo_t = SqliteTutorSessionRepository(conn)
        session = TutorSession.start(
            id=TutorSessionId(TUTOR_SESSION_ID),
            learning_session_id=LearningSessionId(LEARNING_SESSION_ID),
            started_at=T0,
        )
        counter = 0
        for user_text, ai_text in CONVERSATION:
            counter += 2
            session = session.append_message(
                message_id=MessageId(str(counter)),
                role=MessageRole.USER,
                content=user_text,
                created_at=T0,
            ).append_message(
                message_id=MessageId(str(counter + 1)),
                role=MessageRole.ASSISTANT,
                content=ai_text,
                created_at=T0,
                responded_at=T7,
            )
        repo_t.save(session)
        SqliteDialogLogRepository(conn).save(
            DialogLog(
                participant_id="1",
                lecture_id=LECTURE,
                learning_session_id=LEARNING_SESSION_ID,
                tutor_session_id=TUTOR_SESSION_ID,
                ended_at=SAVED_AT,
                end_method=EndMethod.END_BUTTON,
                messages=session.messages,
            )
        )
        conn.commit()
    finally:
        conn.close()


def read_sample_data(learning_db: Path | str, tutor_db: Path | str) -> dict:
    """write_sample_data で書いた内容を、新しい接続で読み出す。"""
    conn = connect_learning_db(learning_db)
    try:
        loaded = SqliteLearningSessionRepository(conn).find_by_learner_and_lecture(
            LearnerId(LEARNER), LectureId(LECTURE)
        )
        learning_ids = None if loaded is None else str(loaded.id)
    finally:
        conn.close()

    conn = connect_tutor_db(tutor_db)
    try:
        tutor = SqliteTutorSessionRepository(conn).find_by_id(
            TutorSessionId(TUTOR_SESSION_ID)
        )
        messages = (
            None
            if tutor is None
            else [(m.role.value, m.content) for m in tutor.messages]
        )
        log_rows = conn.execute(
            "SELECT session_id, end_method FROM dialog_logs"
        ).fetchall()
        logs = [(r["session_id"], r["end_method"]) for r in log_rows]
    finally:
        conn.close()
    return {"learning_session_id": learning_ids, "messages": messages, "dialog_logs": logs}


def expected_sample_data() -> dict:
    messages: list[tuple[str, str]] = []
    for user_text, ai_text in CONVERSATION:
        messages.append(("user", user_text))
        messages.append(("assistant", ai_text))
    return {
        "learning_session_id": LEARNING_SESSION_ID,
        "messages": messages,
        "dialog_logs": [(TUTOR_SESSION_ID, "end_button")],
    }
