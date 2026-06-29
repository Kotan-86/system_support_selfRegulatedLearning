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
def fake_llm_gateway():
    """テスト用 Fake LlmGateway。"""
    from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway

    return FakeLlmGateway(response="スタブ応答")


@pytest.fixture
def app_client(env_tutor_db_path, tmp_path, monkeypatch, fake_llm_gateway):
    """
    Flask アプリのテストクライアント。
    TUTOR_DB_PATH / LEARNING_DB_PATH を tmp_path に設定し、LLM は Fake に差し替える。
    """
    env_tutor_db_path.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
    monkeypatch.setenv("LEARNING_DB_PATH", str(tmp_path / "learning.db"))
    monkeypatch.setattr(
        "framework_drivers.platform.wiring.build_llm_gateway",
        lambda: fake_llm_gateway,
    )
    from tests.test_interfaces.fakes.fake_video_duration_resolver import (
        FakeVideoDurationResolver,
    )

    monkeypatch.setattr(
        "framework_drivers.platform.wiring.build_video_duration_resolver",
        lambda: FakeVideoDurationResolver(duration_sec=600),
    )
    from framework_drivers.platform.main import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()

