# 仕様: docs/spec/application-usecase.md#RunTutoringPipeline
"""PR-0 回帰ガード: 既存 Tutoring テストが GREEN のままであることを担保する。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

EXISTING_TUTORING_TEST_PATHS: list[str] = [
    "tests/test_application/test_tutoring/test_send_chat_message.py",
    "tests/test_application/test_tutoring/test_start_or_get_tutor_session.py",
    "tests/test_application/test_tutoring/test_tutoring_ports.py",
    "tests/test_application/test_tutoring/test_fakes.py",
    "tests/test_interfaces/test_tutoring/test_chat_prompt_builder.py",
    "tests/test_interfaces/test_tutoring/test_send_chat_message_controller.py",
    "tests/test_framework_drivers/db/tutoring/test_send_chat_message_sqlite.py",
]


@pytest.mark.parametrize("test_path", EXISTING_TUTORING_TEST_PATHS)
def test_existing_tutoring_tests_remain_green(test_path: str) -> None:
    """既存 Tutoring 関連テストを subprocess で実行し、回帰がないことを確認する。"""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-q"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Regression in {test_path}:\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
