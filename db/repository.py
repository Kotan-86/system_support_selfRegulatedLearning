"""
永続化レイヤー: セッション作成・メッセージ追加・履歴取得。
TUTOR_DB_PATH または db/data/tutor.db を使用する。
"""
import sqlite3
import uuid
from pathlib import Path

from db.init_db import get_db_path as _get_db_path


def get_db_path() -> Path:
    """環境変数 TUTOR_DB_PATH があればそのパス、なければ db/data/tutor.db を返す。"""
    return _get_db_path()


def create_session() -> str:
    """セッションを 1 件挿入し、発行した id（UUID 文字列）を返す。"""
    path = get_db_path()
    sid = str(uuid.uuid4())
    conn = sqlite3.connect(str(path))
    conn.execute(
        "INSERT INTO sessions (id, created_at) VALUES (?, CURRENT_TIMESTAMP)",
        (sid,),
    )
    conn.commit()
    conn.close()
    return sid


def add_message(session_id: str, role: str, content: str) -> None:
    """メッセージを 1 件挿入する。"""
    path = get_db_path()
    conn = sqlite3.connect(str(path))
    conn.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
        (session_id, role, content),
    )
    conn.commit()
    conn.close()


def get_history(session_id: str, limit: int = 100) -> list[dict]:
    """指定セッションのメッセージを created_at 昇順で直近 limit 件返す。各要素は role, content を含む dict。"""
    path = get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT id, session_id, role, content, created_at
        FROM messages
        WHERE session_id = ?
        ORDER BY created_at ASC
        """,
        (session_id,),
    )
    rows = cur.fetchall()
    conn.close()
    # 直近 limit 件 = 末尾の limit 件を昇順のまま返す
    subset = rows[-limit:] if limit else rows
    return [dict(row) for row in subset]
