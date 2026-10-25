# 仕様: docs/spec/db-persistence.md#受入基準 (AC2, AC3, AC4, AC5)
"""起動手順(deploy/entrypoint.sh)を、偽の litestream / gunicorn で動かして検証する。

偽の道具の約束は _harness.py の冒頭を参照。
"""
from __future__ import annotations

import sqlite3

import pytest

from tests.test_deploy._harness import db_paths, requires_bash, run_entrypoint

pytestmark = requires_bash


def _restore_ends(run):
    return run.evs("restore-end")


# --- AC2: 起動の順序 ---------------------------------------------------------


def test_ac2_both_restores_finish_before_gunicorn_starts(tmp_path):
    run = run_entrypoint(tmp_path, restore_mode="exists")

    assert run.returncode == 0, run.output
    ends = _restore_ends(run)
    assert sorted(e["which"] for e in ends) == ["learning", "tutor"], run.events
    gunicorn_at = run.index_of("gunicorn-start")
    assert gunicorn_at is not None, f"gunicorn が起動していない: {run.events}"
    last_restore_end = run.index_of("restore-end", last=True)
    assert last_restore_end < gunicorn_at, f"復元の完了前に gunicorn が起動: {run.events}"


def test_ac2_restore_happens_before_replicate_and_not_after_app_start(tmp_path):
    run = run_entrypoint(tmp_path, restore_mode="exists")

    assert run.returncode == 0, run.output
    gunicorn_at = run.index_of("gunicorn-start")
    assert gunicorn_at is not None
    # 復元が gunicorn より後に走ってはならない(restore-begin も含めて全部前)
    for i, e in enumerate(run.events):
        if str(e.get("ev", "")).startswith("restore"):
            assert i < gunicorn_at, f"gunicorn の後に復元: {run.events}"
    replicate_at = run.index_of("replicate-start")
    assert replicate_at is not None, f"複製(replicate)が始まっていない: {run.events}"
    assert run.index_of("restore-end", last=True) < replicate_at


# --- AC3: 復元の失敗時に空で起動しない ---------------------------------------


@pytest.mark.parametrize("failing", ["learning", "tutor"])
@pytest.mark.parametrize("restore_mode", ["exists", "none"])
def test_ac3_restore_failure_of_either_db_exits_nonzero_and_does_not_start_app(
    tmp_path, failing, restore_mode
):
    run = run_entrypoint(tmp_path, restore_mode=restore_mode, fail_for=failing)

    attempted = [e for e in _restore_ends(run) if e["which"] == failing]
    assert attempted, f"失敗させる復元が呼ばれていない(起動手順が復元を試みていない): {run.events}"
    assert run.returncode != 0, run.output
    assert run.evs("gunicorn-start") == [], f"復元失敗なのにアプリが起動: {run.events}"
    assert run.evs("replicate-start") == [], f"復元失敗なのに複製が開始: {run.events}"


# --- AC4: 複製がない初回 -----------------------------------------------------


def test_ac4_no_replica_first_boot_starts_app_and_both_dbs_have_schema(tmp_path):
    run = run_entrypoint(tmp_path, restore_mode="none", init_app=True)

    assert run.returncode == 0, run.output
    assert sorted(e["which"] for e in _restore_ends(run)) == ["learning", "tutor"], run.events
    assert run.evs("gunicorn-start"), run.events
    assert run.evs("gunicorn-app-initialized"), run.events

    paths = db_paths(tmp_path)
    assert paths["learning"].exists() and paths["tutor"].exists()
    expected = {
        "learning": {"learning_sessions", "viewing_logs", "quiz_attempts"},
        "tutor": {"sessions", "messages", "dialog_logs"},
    }
    for name, tables in expected.items():
        conn = sqlite3.connect(str(paths[name]))
        try:
            found = {
                r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        finally:
            conn.close()
        assert tables <= found, f"{name}.db にスキーマがない: {found}"


# --- AC5: 複製先の設定がないときは起動しない ---------------------------------


@pytest.mark.parametrize("bucket", [None, ""], ids=["unset", "empty"])
def test_ac5_missing_replica_target_fails_with_message_and_does_not_start_app(
    tmp_path, bucket
):
    run = run_entrypoint(tmp_path, bucket=bucket, disabled=None)

    assert run.returncode != 0, run.output
    assert run.evs("gunicorn-start") == [], f"設定なしでアプリが起動: {run.events}"
    assert "DB_REPLICA_BUCKET" in run.output or "複製先" in run.output, (
        f"複製先の設定がないことが出力に示されていない: {run.output!r}"
    )


@pytest.mark.parametrize("disabled", ["0", "true", "yes", ""])
def test_ac5_disabled_value_other_than_1_is_not_an_opt_out(tmp_path, disabled):
    run = run_entrypoint(tmp_path, bucket=None, disabled=disabled)

    assert run.returncode != 0, run.output
    assert run.evs("gunicorn-start") == [], run.events


@pytest.mark.parametrize("bucket", [None, "test-bucket"], ids=["no-bucket", "with-bucket"])
def test_ac5_disabled_1_starts_app_without_restore_or_replicate(tmp_path, bucket):
    run = run_entrypoint(tmp_path, bucket=bucket, disabled="1")

    assert run.returncode == 0, run.output
    assert run.litestream_events == [], f"複製しない指定なのに litestream が呼ばれた: {run.events}"
    assert run.evs("gunicorn-start"), f"アプリが起動していない: {run.events}"
    assert "DB_REPLICA_DISABLED" in run.output or "複製しない" in run.output, (
        f"複製しないことがログに残っていない: {run.output!r}"
    )


def test_ac5_disabled_other_than_1_with_bucket_still_replicates(tmp_path):
    run = run_entrypoint(tmp_path, restore_mode="exists", bucket="test-bucket", disabled="true")

    assert run.returncode == 0, run.output
    assert sorted(e["which"] for e in _restore_ends(run)) == ["learning", "tutor"], run.events
    assert run.evs("replicate-start"), run.events
