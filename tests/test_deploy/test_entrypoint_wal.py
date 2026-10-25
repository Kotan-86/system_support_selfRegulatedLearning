# 仕様: docs/spec/db-persistence.md#受入基準 (AC21)
"""AC21: 起動の手順による WAL 化。

(a) 復元で WAL でない(delete の)2つの DB が置かれた場合と、(b)「複製なし」の場合の両方で、
アプリの起動が始まる時点で、2つの DB のジャーナルモードが wal である。
模してよいのは litestream とアプリ(gunicorn)の起動だけ。ジャーナルモードは、
偽 gunicorn が標準 sqlite3(実の SQLite)で DB ファイルを開いて記録する。
"""
from __future__ import annotations

import sqlite3

from tests.test_deploy._harness import db_paths, requires_bash, run_entrypoint

pytestmark = requires_bash


def test_ac21a_restored_delete_mode_dbs_are_wal_when_app_starts(tmp_path):
    run = run_entrypoint(tmp_path, restore_mode="exists")

    assert run.returncode == 0, run.output
    # 前提: 復元で置かれたのは WAL でない DB
    for end in run.evs("restore-end"):
        assert end["created_mode"] == "delete", end
    (start,) = run.evs("gunicorn-start")
    assert start["modes"] == {"learning": "wal", "tutor": "wal"}, start

    # 復元された中身(データ)は WAL 化で失われない
    paths = db_paths(tmp_path)
    for name in ("learning", "tutor"):
        conn = sqlite3.connect(str(paths[name]))
        try:
            rows = conn.execute("SELECT v FROM restored_marker").fetchall()
        finally:
            conn.close()
        assert rows == [("restored-" + name,)]


def test_ac21b_no_replica_first_boot_dbs_are_wal_when_app_starts(tmp_path):
    run = run_entrypoint(tmp_path, restore_mode="none")

    assert run.returncode == 0, run.output
    (start,) = run.evs("gunicorn-start")
    assert start["modes"] == {"learning": "wal", "tutor": "wal"}, start


def test_ac21_dbs_stay_wal_after_the_app_applies_schema(tmp_path):
    run = run_entrypoint(tmp_path, restore_mode="none", init_app=True)

    assert run.returncode == 0, run.output
    (initialized,) = run.evs("gunicorn-app-initialized")
    assert initialized["modes"] == {"learning": "wal", "tutor": "wal"}, initialized
