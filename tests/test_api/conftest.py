"""
Phase 2 用フィクスチャ。
学習データ用 API のテストで LEARNING_DB_PATH を一時ディレクトリに設定する。
"""
import os
from pathlib import Path

import pytest


@pytest.fixture
def phase2_client(monkeypatch, tmp_path: Path):
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
