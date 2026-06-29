"""
チャット・LAD 統合テスト用フィクスチャ。
対話用・学習用 DB を tmp_path に設定したクライアントと、repository 用の初期化 DB を提供する。
"""
from pathlib import Path

import pytest

from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway


@pytest.fixture
def fake_llm_gateway() -> FakeLlmGateway:
    """テスト用 Fake LlmGateway（プロンプト捕捉用）。"""
    return FakeLlmGateway(response="スタブ応答")


@pytest.fixture
def chat_lad_client(monkeypatch, tmp_path: Path, fake_llm_gateway: FakeLlmGateway):
    """
    Flask テストクライアント。TUTOR_DB_PATH と LEARNING_DB_PATH を tmp_path に設定。
    LLM は FakeLlmGateway に差し替える。
    """
    monkeypatch.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
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


@pytest.fixture
def initialized_tutor_db(monkeypatch, tmp_path: Path):
    """対話用 DB のみ tmp_path に初期化する。repository の単体テスト用。"""
    monkeypatch.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
    monkeypatch.setenv("LEARNING_DB_PATH", str(tmp_path / "learning.db"))
    from framework_drivers.platform.wiring import init_databases

    init_databases()
    return tmp_path / "tutor.db"
