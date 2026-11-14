# 仕様: docs/spec/multi-video-learning.md#受入基準 (PBI #56 PBI-D 選び直し) AC14(選び直しの同時の要求)
"""選び直しの確定と、別の確定・最初の記録が同時に届いたときの結果を確かめる(What 8節「同時の要求」)。

既存の tests/test_api/test_lecture_selection_race.py と同じく、同じ協力者の別々のクライアントから、
threading.Barrier で同時に送り出し、試行ごとに新しい DB で繰り返す。どちらが先に成立するかは問わず、
どの順でも成り立つ条件だけを判定する。

範囲: learning.db の中の要求(確定どうし、確定と視聴ログ)。`/chat`・対話ログの保存(tutor.db)と
選び直しの同時は、仕様の既知の制限(制約「選び直しの排他」)のため検査しない。

【test-writer が置いた前提】各試行の最初に、選び直しができる状態であること(選択の画面が 200)を
準備として確かめる(選び直しが最初から無い実装では、同時の要求の検査にならないため)。
"""
from __future__ import annotations

import sqlite3
import threading

import pytest

from tests.login_helpers import build_app
from tests.multi_video_helpers import W, X, Y, Z, build_progress, sessions_of
from tests.selection_helpers import CONFIRM_PATH, SELECT_PATH, login_unselected, viewing_body

PID = "P02"
TRIALS = 15


def _clients(app, count: int, first_progress) -> list:
    """同じ協力者でログインした count 個のクライアント。最初のクライアントで first_progress を作る。"""
    first = app.test_client()
    first_progress(first)
    clients = [first]
    for _ in range(count - 1):
        client = app.test_client()
        login_unselected(client, PID)
        clients.append(client)
    return clients


def _run_concurrently(requests: list) -> list[int]:
    """requests(引数なしの関数)を同時に送り出し、状態コードを返す(順は不定)。"""
    barrier = threading.Barrier(len(requests))
    statuses: list[int] = []
    errors: list[BaseException] = []

    def go(send) -> None:
        barrier.wait()
        try:
            statuses.append(send().status_code)
        except BaseException as exc:  # noqa: BLE001 - スレッドの例外をテストの失敗にする
            errors.append(exc)

    threads = [threading.Thread(target=go, args=(send,)) for send in requests]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"同時の要求の処理で例外: {errors!r}"
    return statuses


def _assert_reselectable(client) -> None:
    screen = client.get(SELECT_PATH)
    assert screen.status_code == 200, (
        f"準備: 選び直しができる状態でない(選択の画面が {screen.status_code} "
        f"{screen.headers.get('Location')})"
    )


def _orphan_viewing_logs(tmp_path) -> list[tuple]:
    conn = sqlite3.connect(str(tmp_path / "learning.db"))
    try:
        return conn.execute(
            "SELECT v.id, v.learning_session_id FROM viewing_logs v "
            "LEFT JOIN learning_sessions s ON s.id = v.learning_session_id WHERE s.id IS NULL"
        ).fetchall()
    finally:
        conn.close()


def _viewing_counts(tmp_path) -> dict[str, int]:
    """講義ごとの視聴ログの数(PID の学習セッション)。"""
    conn = sqlite3.connect(str(tmp_path / "learning.db"))
    try:
        return {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT s.lecture_id, COUNT(*) FROM viewing_logs v "
                "JOIN learning_sessions s ON s.id = v.learning_session_id "
                "WHERE s.learner_id=? GROUP BY s.lecture_id",
                (PID,),
            )
        }
    finally:
        conn.close()


@pytest.mark.parametrize("trial", range(TRIALS))
def test_ac14a_two_reselect_confirms_at_once_leave_one_session(monkeypatch, tmp_path, trial) -> None:
    # 仕様: docs/spec/multi-video-learning.md#受入基準 AC14 (a)、What 8節「同時の要求」
    app, _ = build_app(monkeypatch, tmp_path)
    one, two = _clients(app, 2, lambda c: build_progress(c, PID, [], X))
    _assert_reselectable(one)

    statuses = _run_concurrently(
        [
            lambda: one.post(CONFIRM_PATH, data={"lecture_id": Y}),
            lambda: two.post(CONFIRM_PATH, data={"lecture_id": W}),
        ]
    )

    lectures = [lec for _sid, lec in sessions_of(tmp_path, PID)]
    assert len(lectures) == 1, f"学習セッションが {len(lectures)} 個: {lectures}(状態コード {statuses})"
    assert lectures[0] in {Y, W}, f"講義が Y・W のいずれでもない: {lectures}(状態コード {statuses})"


@pytest.mark.parametrize("trial", range(TRIALS))
def test_ac14b_reselect_and_first_viewing_log_at_once_leave_no_orphan(
    monkeypatch, tmp_path, trial
) -> None:
    # 仕様: docs/spec/multi-video-learning.md#受入基準 AC14 (b)、What 8節「同時の要求」
    #   (記録が X に入り X のまま / 選び直しが成立し、記録は Y に入るか拒否される)
    app, _ = build_app(monkeypatch, tmp_path)
    one, two = _clients(app, 2, lambda c: build_progress(c, PID, [], X))
    _assert_reselectable(one)

    statuses = _run_concurrently(
        [
            lambda: one.post(CONFIRM_PATH, data={"lecture_id": Y}),
            lambda: two.post("/api/viewing-log", json=viewing_body(action="play")),
        ]
    )

    assert _orphan_viewing_logs(tmp_path) == [], f"存在しない学習セッションを指す視聴ログ(状態コード {statuses})"
    lectures = [lec for _sid, lec in sessions_of(tmp_path, PID)]
    assert len(lectures) == 1, f"学習セッションが {len(lectures)} 個: {lectures}(状態コード {statuses})"
    counts = _viewing_counts(tmp_path)
    if lectures == [X]:
        assert counts == {X: 1}, f"選び直しが成立しないとき、記録は X に入る: {counts}(状態コード {statuses})"
    else:
        assert lectures == [Y], lectures
        assert counts in ({}, {Y: 1}), f"選び直しが成立したとき、記録は Y に入るか拒否される: {counts}"


@pytest.mark.parametrize("trial", range(5))
def test_ac14_two_reselect_confirms_in_round2_keep_two_sessions(monkeypatch, tmp_path, trial) -> None:
    # 仕様: docs/spec/multi-video-learning.md#What 8節「同時の要求」(選び直しの確定が同時に複数届いても、
    #       学習セッションは n のまま。AC14 (a) を n = 2 で。終えた回 X は変わらない)
    app, _ = build_app(monkeypatch, tmp_path)
    one, two = _clients(app, 2, lambda c: build_progress(c, PID, [X], Y))
    _assert_reselectable(one)
    x_row = [row for row in sessions_of(tmp_path, PID) if row[1] == X]

    statuses = _run_concurrently(
        [
            lambda: one.post(CONFIRM_PATH, data={"lecture_id": Z}),
            lambda: two.post(CONFIRM_PATH, data={"lecture_id": W}),
        ]
    )

    sessions = sessions_of(tmp_path, PID)
    assert len(sessions) == 2, f"学習セッションが {len(sessions)} 個: {sessions}(状態コード {statuses})"
    assert [row for row in sessions if row[1] == X] == x_row, "終えた回 X の学習セッションが変わった"
    # 今の回は1つ(8節はどちらが成立するかを定めないため、Y・Z・W のいずれでもよい)
    current = [lec for _sid, lec in sessions if lec != X]
    assert len(current) == 1 and current[0] in {Y, Z, W}, sessions
