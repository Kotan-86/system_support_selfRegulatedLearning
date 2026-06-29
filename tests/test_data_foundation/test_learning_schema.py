"""
Phase 1 Step 1.3: 学習データ用 DB のスキーマを作成する

学習用スキーマに learning_sessions, viewing_logs, quiz_attempts, quiz_attempt_answers が定義され、
指定カラム（is_correct は INTEGER 0/1）があることを検証する。
仕様: docs/spec/framework-drivers-persistence.md
"""
import sqlite3
from pathlib import Path

import pytest


def _execute_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql)


def _get_columns(conn: sqlite3.Connection, table: str) -> list[tuple[str, str, int]]:
    """(name, type, notnull) のリストを返す。"""
    cur = conn.execute(
        f"SELECT name, type, [notnull] FROM pragma_table_info('{table}') ORDER BY cid"
    )
    return cur.fetchall()


class TestStep1_3LearningSchemaTablesExist:
    """学習用スキーマで 4 テーブルが作成されること。"""

    def test_learning_schema_file_exists(self, learning_schema_path: Path) -> None:
        """学習用スキーマファイルが存在する（前提）。"""
        assert learning_schema_path.exists(), "db/schema_learning.sql が存在すること"

    def test_learning_sessions_table_exists(
        self, learning_schema_path: Path
    ) -> None:
        """learning_sessions テーブルが作成される。"""
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, learning_schema_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='learning_sessions'"
        )
        assert cur.fetchone() is not None, "learning_sessions テーブルが存在すること"
        conn.close()

    def test_viewing_logs_table_exists(
        self, learning_schema_path: Path
    ) -> None:
        """viewing_logs テーブルが作成される。"""
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, learning_schema_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='viewing_logs'"
        )
        assert cur.fetchone() is not None, "viewing_logs テーブルが存在すること"
        conn.close()

    def test_quiz_attempts_table_exists(
        self, learning_schema_path: Path
    ) -> None:
        """quiz_attempts テーブルが作成される。"""
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, learning_schema_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='quiz_attempts'"
        )
        assert cur.fetchone() is not None, "quiz_attempts テーブルが存在すること"
        conn.close()

    def test_quiz_attempt_answers_table_exists(
        self, learning_schema_path: Path
    ) -> None:
        """quiz_attempt_answers テーブルが作成される。"""
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, learning_schema_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='quiz_attempt_answers'"
        )
        assert cur.fetchone() is not None, "quiz_attempt_answers テーブルが存在すること"
        conn.close()


class TestStep1_3LearningSessionsColumns:
    """learning_sessions のカラム: id, learner_id, lecture_id, started_at。"""

    def test_learning_sessions_has_required_columns(
        self, learning_schema_path: Path
    ) -> None:
        """learning_sessions に id, learner_id, lecture_id, started_at がある。"""
        if not learning_schema_path.exists():
            pytest.skip("学習用スキーマが未作成のためスキップ")
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, learning_schema_path)
        rows = _get_columns(conn, "learning_sessions")
        conn.close()
        names = [r[0] for r in rows]
        required = ["id", "learner_id", "lecture_id", "started_at"]
        for col in required:
            assert col in names, f"learning_sessions に {col} カラムがあること"


class TestStep1_3ViewingLogsColumns:
    """viewing_logs のカラム: id, learning_session_id, time_stamp, current_time, action, duration。"""

    def test_viewing_logs_has_required_columns(
        self, learning_schema_path: Path
    ) -> None:
        """viewing_logs に id, learning_session_id, time_stamp, current_time, action, duration がある。"""
        if not learning_schema_path.exists():
            pytest.skip("学習用スキーマが未作成のためスキップ")
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, learning_schema_path)
        rows = _get_columns(conn, "viewing_logs")
        conn.close()
        names = [r[0] for r in rows]
        required = [
            "id",
            "learning_session_id",
            "time_stamp",
            "current_time",
            "action",
            "duration",
        ]
        for col in required:
            assert col in names, f"viewing_logs に {col} カラムがあること"
        assert "participant_id" not in names, "participant_id は learning_session_id に置換されていること"


class TestStep1_3QuizAttemptsColumns:
    """quiz_attempts のカラム: id, learning_session_id, created_at, score_numerator, score_denominator。"""

    def test_quiz_attempts_has_required_columns(
        self, learning_schema_path: Path
    ) -> None:
        """quiz_attempts に id, learning_session_id, created_at, score_numerator, score_denominator がある。"""
        if not learning_schema_path.exists():
            pytest.skip("学習用スキーマが未作成のためスキップ")
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, learning_schema_path)
        rows = _get_columns(conn, "quiz_attempts")
        conn.close()
        names = [r[0] for r in rows]
        required = [
            "id",
            "learning_session_id",
            "created_at",
            "score_numerator",
            "score_denominator",
        ]
        for col in required:
            assert col in names, f"quiz_attempts に {col} カラムがあること"
        assert "participant_id" not in names, "participant_id は learning_session_id に置換されていること"


class TestStep1_3QuizAttemptAnswersColumns:
    """quiz_attempt_answers のカラム: id, attempt_id, question_index, selected_answer, is_correct (INTEGER 0/1)。"""

    def test_quiz_attempt_answers_has_required_columns(
        self, learning_schema_path: Path
    ) -> None:
        """quiz_attempt_answers に id, attempt_id, question_index, selected_answer, is_correct がある。"""
        if not learning_schema_path.exists():
            pytest.skip("学習用スキーマが未作成のためスキップ")
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, learning_schema_path)
        rows = _get_columns(conn, "quiz_attempt_answers")
        conn.close()
        names = [r[0] for r in rows]
        required = ["id", "attempt_id", "question_index", "selected_answer", "is_correct"]
        for col in required:
            assert col in names, f"quiz_attempt_answers に {col} カラムがあること"

    def test_is_correct_is_integer_type(
        self, learning_schema_path: Path
    ) -> None:
        """is_correct は SQLite で INTEGER（0/1 で BOOLEAN を表現）である。"""
        if not learning_schema_path.exists():
            pytest.skip("学習用スキーマが未作成のためスキップ")
        conn = sqlite3.connect(":memory:")
        _execute_schema(conn, learning_schema_path)
        rows = _get_columns(conn, "quiz_attempt_answers")
        conn.close()
        col_map = {r[0]: r[1].upper() for r in rows}
        assert "is_correct" in col_map, "is_correct カラムがあること"
        assert col_map["is_correct"] in ("INTEGER", "INT"), (
            "is_correct は INTEGER 型であること（SQLite では BOOLEAN を 0/1 で保存）"
        )
