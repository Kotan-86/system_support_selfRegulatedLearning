"""
DB 初期化: TUTOR_DB_PATH またはデフォルトパスに SQLite ファイルを作成し、
schema.sql を流して sessions / messages テーブルを作る。
"""
import os
import sqlite3
from pathlib import Path

_DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "tutor.db"
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


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
