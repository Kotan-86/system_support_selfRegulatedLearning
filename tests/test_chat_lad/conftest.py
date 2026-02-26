"""
チャット・LAD 統合テスト用フィクスチャ。
対話用・学習用 DB を tmp_path に設定したクライアントと、repository 用の初期化 DB を提供する。
"""
from pathlib import Path

import pytest


@pytest.fixture
def chat_lad_client(monkeypatch, tmp_path: Path):
    """
    Flask テストクライアント。TUTOR_DB_PATH と LEARNING_DB_PATH を tmp_path に設定。
    app.main が未実装のときは None を返す。
    """
    monkeypatch.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
    monkeypatch.setenv("LEARNING_DB_PATH", str(tmp_path / "learning.db"))
    try:
        from app.main import app
        from db import init_db

        init_db.init_db()
        init_db.init_learning_db()
        app.config["TESTING"] = True
        return app.test_client()
    except (ImportError, AttributeError):
        return None


@pytest.fixture
def initialized_tutor_db(monkeypatch, tmp_path: Path):
    """対話用 DB のみ tmp_path に初期化する。repository の単体テスト用。"""
    monkeypatch.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
    try:
        from db import init_db

        init_db.init_db()
    except ImportError:
        pytest.skip("db.init_db が未実装のためスキップ")
    return tmp_path / "tutor.db"
