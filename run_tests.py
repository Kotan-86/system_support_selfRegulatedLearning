#!/usr/bin/env python3
"""
テスト実行スクリプト。uv を用いて pytest を実行する。
プロジェクトルートで:
  uv run python run_tests.py
  uv run python run_tests.py -v
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    rc = subprocess.call(
        ["uv", "run", "pytest", "tests/", "-v", "--tb=short"] + sys.argv[1:],
        cwd=project_root,
    )
    sys.exit(rc)
