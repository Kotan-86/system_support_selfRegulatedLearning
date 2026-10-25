# 仕様: docs/spec/db-persistence.md#受入基準 (AC6)
"""AC6: あらかじめ WAL モードにした2つの DB で、アプリの起動(スキーマ適用)と
学習データ・対話データの書き込み・読み出しが、既存のテストと同じ結果になり、
その後も2つの DB のジャーナルモードは wal のままである。

注: 稼働中(Litestream が複製している間)の wal は AC8、起動手順による WAL 化は AC21。
"""
from __future__ import annotations

import pytest

from framework_drivers.platform.wiring import init_databases
from tests.test_deploy._dbio import (
    expected_sample_data,
    journal_mode,
    read_sample_data,
    set_wal,
    write_sample_data,
)


@pytest.fixture
def wal_dbs(tmp_path, monkeypatch):
    learning = tmp_path / "learning.db"
    tutor = tmp_path / "tutor.db"
    monkeypatch.setenv("LEARNING_DB_PATH", str(learning))
    monkeypatch.setenv("TUTOR_DB_PATH", str(tutor))
    set_wal(learning)
    set_wal(tutor)
    return learning, tutor


def test_ac6_schema_apply_on_wal_dbs_keeps_wal(wal_dbs):
    learning, tutor = wal_dbs

    init_databases()  # 例外なく完了する

    assert journal_mode(learning) == "wal"
    assert journal_mode(tutor) == "wal"


def test_ac6_write_and_read_on_wal_dbs_gives_same_result_and_stays_wal(wal_dbs):
    learning, tutor = wal_dbs
    init_databases()

    write_sample_data(learning, tutor)
    result = read_sample_data(learning, tutor)

    assert result == expected_sample_data()
    assert journal_mode(learning) == "wal"
    assert journal_mode(tutor) == "wal"


def test_ac6_reinit_on_wal_dbs_keeps_rows_and_wal(wal_dbs):
    """再起動を模す: 書いた後にスキーマ適用をやり直しても、行が残り wal のまま。"""
    learning, tutor = wal_dbs
    init_databases()
    write_sample_data(learning, tutor)

    init_databases()

    assert read_sample_data(learning, tutor) == expected_sample_data()
    assert journal_mode(learning) == "wal"
    assert journal_mode(tutor) == "wal"
