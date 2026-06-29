"""
Phase 2 / Phase 4 用フィクスチャ。
学習データ用 API のテストで LEARNING_DB_PATH を一時ディレクトリに設定する。
"""
import os
from pathlib import Path

import pytest


@pytest.fixture
def phase2_client(monkeypatch, tmp_path: Path):
    """
    Flask テストクライアント。TUTOR_DB_PATH と LEARNING_DB_PATH を tmp_path に設定。
    """
    monkeypatch.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
    monkeypatch.setenv("LEARNING_DB_PATH", str(tmp_path / "learning.db"))
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
