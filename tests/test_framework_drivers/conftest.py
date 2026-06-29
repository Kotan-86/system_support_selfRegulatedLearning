# 仕様: docs/spec/framework-drivers-persistence.md
"""framework_drivers テスト用フィクスチャ。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from framework_drivers.db.learning.sqlite_connection import connect_in_memory_learning_db
from framework_drivers.db.learning.sqlite_learning_session_repository import (
    SqliteLearningSessionRepository,
)
from framework_drivers.db.tutoring.sqlite_connection import connect_in_memory_tutor_db
from framework_drivers.db.tutoring.sqlite_tutor_session_repository import (
    SqliteTutorSessionRepository,
)


@pytest.fixture
def learning_schema_path(project_root: Path) -> Path:
    """学習データ用スキーマ（db/schema_learning.sql）の Path。"""
    return project_root / "db" / "schema_learning.sql"


@pytest.fixture
def learning_db_conn(learning_schema_path: Path) -> sqlite3.Connection:
    """スキーマ適用済みの :memory: learning.db 接続。"""
    conn = connect_in_memory_learning_db(learning_schema_path)
    yield conn
    conn.close()


@pytest.fixture
def sqlite_learning_session_repository(
    learning_db_conn: sqlite3.Connection,
) -> SqliteLearningSessionRepository:
    """SqliteLearningSessionRepository（:memory: DB）。"""
    return SqliteLearningSessionRepository(learning_db_conn)


@pytest.fixture
def tutor_schema_path(project_root: Path) -> Path:
    """対話用スキーマ（db/schema.sql）の Path。"""
    return project_root / "db" / "schema.sql"


@pytest.fixture
def tutor_db_conn(tutor_schema_path: Path) -> sqlite3.Connection:
    """スキーマ適用済みの :memory: tutor.db 接続。"""
    conn = connect_in_memory_tutor_db(tutor_schema_path)
    yield conn
    conn.close()


@pytest.fixture
def sqlite_tutor_session_repository(
    tutor_db_conn: sqlite3.Connection,
) -> SqliteTutorSessionRepository:
    """SqliteTutorSessionRepository（:memory: DB）。"""
    return SqliteTutorSessionRepository(tutor_db_conn)
