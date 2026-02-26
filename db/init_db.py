"""
DB 初期化: TUTOR_DB_PATH またはデフォルトパスに SQLite ファイルを作成し、
schema.sql を流して sessions / messages テーブルを作る。
学習データ用 DB は init_learning_db() で schema_learning.sql を流す。
"""
import os
import sqlite3
from pathlib import Path

_DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "tutor.db"
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
_SCHEMA_LEARNING_PATH = Path(__file__).resolve().parent / "schema_learning.sql"


def get_db_path() -> Path:
    """環境変数 TUTOR_DB_PATH があればそのパス、なければ db/data/tutor.db を返す。"""
    path = os.environ.get("TUTOR_DB_PATH")
    return Path(path) if path else _DEFAULT_DB_PATH


def init_db() -> None:
    """DB ファイルが無い、または未初期化の場合に schema.sql を実行してテーブルを作成する。"""
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(path))
    conn.executescript(schema_sql)
    conn.close()


def init_learning_db() -> None:
    """学習データ用 DB に schema_learning.sql を実行して viewing_logs / quiz_attempts / quiz_attempt_answers を作成する。"""
    from db.config import get_learning_db_path

    path = get_learning_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = _SCHEMA_LEARNING_PATH.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(path))
    conn.executescript(schema_sql)
    conn.close()
