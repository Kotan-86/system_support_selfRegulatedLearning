"""
Phase 1 用フィクスチャ。
学習用 DB パス・スキーマパス・環境変数まわりを提供する。
"""
import os
from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """プロジェクトルートの Path。"""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def default_tutor_db_path(project_root: Path) -> Path:
    """デフォルトの対話用 DB パス（db/data/tutor.db）。"""
    return project_root / "db" / "data" / "tutor.db"


@pytest.fixture
def default_learning_db_path(project_root: Path) -> Path:
    """デフォルトの学習データ用 DB パス（db/data/learning.db）。"""
    return project_root / "db" / "data" / "learning.db"


@pytest.fixture
def db_data_dir(project_root: Path) -> Path:
    """db/data/ の Path。"""
    return project_root / "db" / "data"


@pytest.fixture
def tutor_schema_path(project_root: Path) -> Path:
    """対話用スキーマ（db/schema.sql）の Path。"""
    return project_root / "db" / "schema.sql"


@pytest.fixture
def learning_schema_path(project_root: Path) -> Path:
    """学習データ用スキーマの Path（db/schema_learning.sql）。"""
    return project_root / "db" / "schema_learning.sql"


@pytest.fixture
def env_tutor_db_path(monkeypatch):
    """TUTOR_DB_PATH を一時的に設定し、テスト後に復元する。"""
    old = os.environ.get("TUTOR_DB_PATH")
    yield monkeypatch
    if old is None:
        monkeypatch.delenv("TUTOR_DB_PATH", raising=False)
    else:
        monkeypatch.setenv("TUTOR_DB_PATH", old)


@pytest.fixture
def env_learning_db_path(monkeypatch):
    """LEARNING_DB_PATH を一時的に設定し、テスト後に復元する。"""
    old = os.environ.get("LEARNING_DB_PATH")
    yield monkeypatch
    if old is None:
        monkeypatch.delenv("LEARNING_DB_PATH", raising=False)
    else:
        monkeypatch.setenv("LEARNING_DB_PATH", old)
