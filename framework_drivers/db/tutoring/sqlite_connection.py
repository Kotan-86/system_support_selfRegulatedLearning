# 仕様: docs/spec/framework-drivers-persistence.md#対話-dbtutordbとの接続
"""tutor.db 向け SQLite 接続ヘルパ。"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_tutor_db(db_path: Path | str) -> sqlite3.Connection:
    """tutor.db 用接続を開き、外部キー制約を有効にする。"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connect_in_memory_tutor_db(schema_path: Path) -> sqlite3.Connection:
    """スキーマ適用済みの :memory: 接続を返す（テスト用）。"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_tutor_schema(conn, schema_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_tutor_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    """db/schema.sql を接続に適用する。"""
    conn.executescript(schema_path.read_text(encoding="utf-8"))
