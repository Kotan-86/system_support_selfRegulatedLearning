# 仕様: docs/spec/lecture-selection.md#受入基準 AC8(選択の固定)・What 3節(1人1つ。2つのタブでも増えない)
"""同じ協力者が、異なる講義の確定を同時に送っても、学習セッションは1行のままであること。

レース(確認してから挿入するまでの隙間)を安定して再現するため、2つのスレッドを Barrier で同時に
POST /select-lecture/confirm へ送り出し、これを試行ごとに新しい DB で繰り返す。
1回でも2行できたら失敗する(reviewer の実験では 30/30 で再現した)。
"""
from __future__ import annotations

import threading

import pytest

from tests.login_helpers import build_app
from tests.selection_helpers import CONFIRM_PATH, learning_sessions, login_unselected

PID = "P02"
TRIALS = 30


def _post_concurrently(app, lectures: list[str]) -> list[int]:
    """同じ協力者の別々のクライアントから、lectures の確定を同時に送り、状態コードを返す。"""
    clients = []
    for _ in lectures:
        client = app.test_client()
        login_unselected(client, PID)
        clients.append(client)
    barrier = threading.Barrier(len(lectures))
    statuses: list[int] = []

    def go(client, lecture_id: str) -> None:
        barrier.wait()
        statuses.append(client.post(CONFIRM_PATH, data={"lecture_id": lecture_id}).status_code)

    threads = [threading.Thread(target=go, args=(c, lec)) for c, lec in zip(clients, lectures)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return statuses


@pytest.mark.parametrize("trial", range(TRIALS))
def test_ac8_concurrent_confirm_of_different_lectures_keeps_one_session(monkeypatch, tmp_path, trial) -> None:
    """AC8・What 3節: 異なる講義の確定が同時に来ても learning_sessions は1行(1人1つ)。"""
    app, _ = build_app(monkeypatch, tmp_path)

    statuses = _post_concurrently(app, ["lecture-2", "lecture-5"])

    rows = learning_sessions(tmp_path)
    assert len(rows) == 1, f"学習セッションが {len(rows)} 行: {rows} (状態コード {statuses})"
    assert rows[0][0] == PID
    assert rows[0][1] in {"lecture-2", "lecture-5"}
    # 負けた側も、成功した側と同じく 302(講義の画面へ)。500 にならない。
    assert statuses == [302, 302]


@pytest.mark.parametrize("trial", range(10))
def test_ac8_concurrent_confirm_of_same_lecture_keeps_one_session(monkeypatch, tmp_path, trial) -> None:
    """AC8: 同じ講義の確定が同時に来ても1行で、どちらも 302(500 にならない)。"""
    app, _ = build_app(monkeypatch, tmp_path)

    statuses = _post_concurrently(app, ["lecture-3", "lecture-3"])

    assert learning_sessions(tmp_path) == [(PID, "lecture-3")]
    assert statuses == [302, 302]
