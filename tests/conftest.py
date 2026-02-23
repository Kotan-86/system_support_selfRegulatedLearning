"""
pytest 共通設定・フィクスチャ。
プロジェクトルートを sys.path に追加し、db パッケージを import 可能にする。
"""
import os
import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加（db パッケージの import 用）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _project_root() -> Path:
    return PROJECT_ROOT


def _db_schema_path() -> Path:
    return PROJECT_ROOT / "db" / "schema.sql"


def _default_db_path() -> Path:
    return PROJECT_ROOT / "db" / "data" / "tutor.db"


def _db_data_dir() -> Path:
    return PROJECT_ROOT / "db" / "data"


def _gitignore_path() -> Path:
    return PROJECT_ROOT / ".gitignore"


# --- フィクスチャ（pytest が自動で注入） ---


@pytest.fixture
def project_root():
    """プロジェクトルートの Path。"""
    return _project_root()


@pytest.fixture
def db_schema_path():
    """db/schema.sql の Path。"""
    return _db_schema_path()


@pytest.fixture
def default_db_path():
    """デフォルト DB ファイルの Path（db/data/tutor.db）。"""
    return _default_db_path()


@pytest.fixture
def db_data_dir():
    """db/data/ ディレクトリの Path。"""
    return _db_data_dir()


@pytest.fixture
def gitignore_path():
    """.gitignore の Path。"""
    return _gitignore_path()


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
def app_client(env_tutor_db_path, tmp_path):
    """
    Flask アプリのテストクライアント。
    TUTOR_DB_PATH を tmp_path に設定し、init_db 済みの DB を使う。
    app.main が未実装のときは None を返し、各テストでスキップする。
    """
    env_tutor_db_path.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
    try:
        from app.main import app
        from db import init_db

        init_db.init_db()
        app.config["TESTING"] = True
        return app.test_client()
    except (ImportError, AttributeError):
        return None

