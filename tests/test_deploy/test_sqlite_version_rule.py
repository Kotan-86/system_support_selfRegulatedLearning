# 仕様: docs/spec/db-persistence.md#受入基準 (AC20)
"""AC20: イメージ内の SQLite の版が WAL-reset の不具合の修正済みの版でなければ、ビルドを失敗させる。

ビルド時の確認そのもの(docker build)は Docker のある環境(Cloud Build など)でしか動かない。
この機でできるのは、版の判定の規則(下限、3.52.0 の除外)の単体テストと、Dockerfile が
そのチェックをビルド中に呼んでいることの静的な確認まで。

公開IF(test-writer が決めた。tests.md に記録):
  ファイル: deploy/sqlite_version_check.py
    is_fixed_version(version: str) -> bool   # 修正済みなら True
    main(argv: list[str] | None = None) -> int
        # argv[0] があればその版、なければ sqlite3.sqlite_version を判定。修正済みなら 0、そうでなければ 0 以外
  `python deploy/sqlite_version_check.py [VERSION]` で同じ判定が動く(Dockerfile の RUN から呼ぶ)。
"""
from __future__ import annotations

import importlib.util
import re
import sqlite3
import subprocess
import sys

import pytest

from tests.test_deploy._harness import DEPLOY_ROOT, DOCKERFILE

MODULE_PATH = DEPLOY_ROOT / "deploy" / "sqlite_version_check.py"

FIXED = [
    "3.51.3",
    "3.51.4",
    "3.51.10",
    "3.53.0",
    "3.53.1",
    "3.60.0",
    "3.100.0",
    "4.0.0",
    "3.44.6",
    "3.44.7",
    "3.44.10",
    "3.50.7",
    "3.50.8",
    "3.50.10",
]
NOT_FIXED = [
    "3.50.4",  # 開発機の版(影響範囲の内)
    "3.51.2",  # 修正の1つ前
    "3.51.0",
    "3.51.1",
    "3.52.0",  # 撤回された版
    "3.44.5",
    "3.44.0",
    "3.50.6",
    "3.50.0",
    "3.45.0",
    "3.46.1",
    "3.49.2",
    "3.40.1",
    "3.9.0",  # 文字列比較の罠
    "3.7.17",
]


def _load():
    assert MODULE_PATH.exists(), f"版の判定規則がない: {MODULE_PATH}"
    spec = importlib.util.spec_from_file_location("sqlite_version_check_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("version", FIXED)
def test_ac20_fixed_versions_are_accepted(version):
    assert _load().is_fixed_version(version) is True


@pytest.mark.parametrize("version", NOT_FIXED)
def test_ac20_unfixed_versions_are_rejected(version):
    assert _load().is_fixed_version(version) is False


def test_ac20_main_returns_nonzero_for_unfixed_and_zero_for_fixed():
    module = _load()
    assert module.main(["3.52.0"]) != 0
    assert module.main(["3.50.4"]) != 0
    assert module.main(["3.53.0"]) == 0
    assert module.main(["3.50.7"]) == 0


def test_ac20_main_without_argument_judges_the_python_sqlite_version():
    module = _load()
    expected_ok = module.is_fixed_version(sqlite3.sqlite_version)
    assert (module.main([]) == 0) is expected_ok


@pytest.mark.parametrize("version,ok", [("3.52.0", False), ("3.53.0", True)])
def test_ac20_script_exit_code_is_what_a_docker_run_step_needs(version, ok):
    assert MODULE_PATH.exists(), f"版の判定規則がない: {MODULE_PATH}"
    proc = subprocess.run(
        [sys.executable, str(MODULE_PATH), version], capture_output=True, text=True
    )
    assert (proc.returncode == 0) is ok, (proc.returncode, proc.stdout, proc.stderr)


def test_ac20_dockerfile_runs_the_version_check_during_build():
    assert DOCKERFILE.exists()
    text = re.sub(r"\\\r?\n\s*", " ", DOCKERFILE.read_text(encoding="utf-8"))
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    run_idx = next(
        (
            i
            for i, l in enumerate(lines)
            if re.match(r"^RUN\b", l) and "sqlite_version_check.py" in l
        ),
        None,
    )
    assert run_idx is not None, "Dockerfile にビルド中の版の確認(RUN ... sqlite_version_check.py)がない"
    copy_idx = next(
        (
            i
            for i, l in enumerate(lines)
            if re.match(r"^COPY\b", l) and re.search(r"\bdeploy\b", l)
        ),
        None,
    )
    assert copy_idx is not None and copy_idx < run_idx, (
        "版の確認の前に deploy/ が COPY されていない"
    )
