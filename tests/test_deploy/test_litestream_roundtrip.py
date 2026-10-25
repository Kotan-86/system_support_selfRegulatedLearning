# 仕様: docs/spec/db-persistence.md#受入基準 (AC8)
"""AC8: ローカルでの複製 → 復元の往復。

一時ディレクトリの2つの DB に学習データと対話データを書き、Litestream(v0.5.17)でファイルの
複製先へ複製した後、元の DB を消して復元すると、2つの DB とも、書いた行がすべて読める。
Litestream が複製している間、2つの DB のジャーナルモードは wal である。

Litestream のバイナリ(v0.5.17)が要る。見つからない・版が違うときは skip するが、
**skip は合格の証跡にならない**(tests.md では「実行不能」に分類する)。
バイナリの場所は PATH、または環境変数 LITESTREAM_BIN で指定する。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from framework_drivers.platform.wiring import init_databases
from tests.test_deploy._dbio import (
    expected_sample_data,
    journal_mode,
    read_sample_data,
    set_wal,
    write_sample_data,
)

EXPECTED_VERSION = "0.5.17"


def _binary() -> str | None:
    return os.environ.get("LITESTREAM_BIN") or shutil.which("litestream")


def _skip_reason() -> str | None:
    exe = _binary()
    if not exe:
        return "実行不能(AC8): litestream のバイナリがない(skip は合格の証跡にならない)"
    try:
        out = subprocess.run(
            [exe, "version"], capture_output=True, text=True, timeout=30
        ).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"実行不能(AC8): litestream version が実行できない: {e}"
    if EXPECTED_VERSION not in out:
        return f"実行不能(AC8): litestream の版が {EXPECTED_VERSION} でない: {out!r}"
    return None


_REASON = _skip_reason()
pytestmark = pytest.mark.skipif(_REASON is not None, reason=_REASON or "")


def _fwd(p: Path) -> str:
    return str(p).replace("\\", "/")


def _wait_for_replica(replica_dir: Path, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if any(p.is_file() for p in replica_dir.rglob("*")):
            return
        time.sleep(0.5)
    raise AssertionError(f"複製が始まらない: {replica_dir}")


def test_ac8_replicate_then_restore_round_trip(tmp_path, monkeypatch):
    exe = _binary()
    learning = tmp_path / "live" / "learning.db"
    tutor = tmp_path / "live" / "tutor.db"
    rep_l = tmp_path / "replica" / "learning"
    rep_t = tmp_path / "replica" / "tutor"
    for d in (learning.parent, rep_l, rep_t):
        d.mkdir(parents=True)
    monkeypatch.setenv("LEARNING_DB_PATH", str(learning))
    monkeypatch.setenv("TUTOR_DB_PATH", str(tutor))

    init_databases()
    set_wal(learning)
    set_wal(tutor)

    config = tmp_path / "litestream.yml"
    config.write_text(
        "dbs:\n"
        f"  - path: {_fwd(learning)}\n"
        "    replica:\n"
        "      type: file\n"
        f"      path: {_fwd(rep_l)}\n"
        f"  - path: {_fwd(tutor)}\n"
        "    replica:\n"
        "      type: file\n"
        f"      path: {_fwd(rep_t)}\n",
        encoding="utf-8",
    )

    proc = subprocess.Popen(
        [exe, "replicate", "-config", str(config)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_for_replica(rep_l)
        _wait_for_replica(rep_t)
        write_sample_data(learning, tutor)
        # 複製している間、2つの DB は wal
        assert journal_mode(learning) == "wal"
        assert journal_mode(tutor) == "wal"
        time.sleep(4)  # sync-interval(既定 1 秒)を十分に超えて待つ
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    # 元の DB を(付随ファイルも)消す
    for base in (learning, tutor):
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(base) + suffix)
            if p.exists():
                p.unlink()
    assert not learning.exists() and not tutor.exists()

    for db in (learning, tutor):
        r = subprocess.run(
            [exe, "restore", "-config", str(config), str(db)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert r.returncode == 0, r.stdout + r.stderr

    assert read_sample_data(learning, tutor) == expected_sample_data()
