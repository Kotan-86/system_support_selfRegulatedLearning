# 仕様: docs/spec/research-lad-csv-download.md#受入基準 (PBI-C #56: C1 C2 C3 C4)
# 仕様: docs/spec/research-lad-csv-download.md#何本目の列round_number共有if2つの-csv-に共通pbi-c
# 仕様: docs/spec/research-lad-csv-download.md#対象と並び順決定-q3multi-video-learningmd-の-q7
# C5(ブラウザと Excel で確認できる)は PO確認。ここでは検証しない。
# A3・A4・B3・B5 の改訂と、C4 のうち A1・A2・A5〜A8、B1・B2・B4・B6〜B9 の回帰は、
# test_research_viewing_logs_csv_api.py と test_research_quiz_answers_csv_api.py にある。
"""研究用の2つの CSV の「何本目」の列(round_number)を、4つの URL で確かめる。

一時ディレクトリの DB と偽の LLM でアプリを起動し、Flask のテストクライアントで操作する。
回の準備は HTTP の操作(ログイン、選択の確定、視聴ログ・小テストの記録、終了ボタンの保存)で作る
(tests/multi_video_helpers.py)。C3 の状態は API では作れないため、DB に直接置く(仕様の共通の前提の例外)。
期待値は仕様の AC から導き、実装の内部クラスには依存しない。列は見出しの名前で読む。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.login_helpers import TEST_PARTICIPANT_IDS, make_entry, write_credentials_file
from tests.multi_video_helpers import (
    confirm_round,
    finish_round,
    next_second,
    record_quiz,
    record_viewing,
    schema_of,
)
from tests.selection_helpers import login_unselected
from tests.test_api import test_research_quiz_answers_csv_api as qa
from tests.test_api import test_research_viewing_logs_csv_api as vl

AUTH = vl.AUTH

# 2つの CSV(視聴ログ、小テスト)× 2つの範囲(参加者別、一括)= 4つの URL
KINDS = {
    "viewing": (vl.HEADER, vl.ALL_URL, vl.participant_url),
    "quiz": (qa.HEADER, qa.ALL_URL, qa.participant_url),
}
FOUR = [
    ("viewing", "participant"),
    ("viewing", "all"),
    ("quiz", "participant"),
    ("quiz", "all"),
]
FOUR_IDS = [f"{kind}-{scope}" for kind, scope in FOUR]


def url_of(kind: str, scope: str, pid: str) -> str:
    _header, all_url, participant_url = KINDS[kind]
    return all_url if scope == "all" else participant_url(pid)


def fetch(client, kind: str, url: str) -> tuple[bytes, list[dict[str, str]]]:
    """状態 200 を確かめ、(本文のバイト列, 見出しの名前で引ける行の一覧)を返す。"""
    header = KINDS[kind][0]
    response = client.get(url, headers=AUTH)
    assert response.status_code == 200, (url, response.status_code, response.get_data(as_text=True)[:300])
    rows = vl.parse(vl.text_of(response))
    assert rows[0] == header, (url, rows[0])
    for row in rows[1:]:
        assert len(row) == len(header), (url, row)
    return response.data, [dict(zip(header, row)) for row in rows[1:]]


def rows_of(client, kind: str, scope: str, pid: str) -> list[dict[str, str]]:
    _raw, rows = fetch(client, kind, url_of(kind, scope, pid))
    return [r for r in rows if r["participant_id"] == pid]


def lecture_sequence(rows: list[dict[str, str]]) -> list[str]:
    """行の講義IDの並び(続く同じ値は1つにまとめる)。"""
    sequence: list[str] = []
    for r in rows:
        if not sequence or sequence[-1] != r["lecture_id"]:
            sequence.append(r["lecture_id"])
    return sequence


@pytest.fixture
def env(monkeypatch, tmp_path: Path) -> vl.Env:
    # C2 の参加者 P04 は、共通のテスト用の設定ファイルにないので、P04 を加えた設定ファイルを使う
    path = write_credentials_file(
        tmp_path / "creds" / "participants.json",
        [make_entry(pid) for pid in (*TEST_PARTICIPANT_IDS, "P04")],
    )
    monkeypatch.setenv("PARTICIPANT_CREDENTIALS_FILE", str(path))
    return vl.Env(monkeypatch, tmp_path)


@pytest.fixture
def client(env: vl.Env):
    return env.start()


# ---------------------------------------------------------------- C1


C1_ROUNDS = ["lecture-5", "lecture-2", "lecture-3"]  # 1本目、2本目、3本目(講義IDの昇順ではない)
C1_EXPECTED = {"lecture-5": "1", "lecture-2": "2", "lecture-3": "3"}


@pytest.fixture
def three_rounds(client):
    """P03 が lecture-5 → lecture-2 → lecture-3 の順に選び、各回で視聴ログ2件と小テスト1回を記録して回を終える。

    一括で参加者ごとに数えることを見るため、P10 が1本目として lecture-1 を選んで記録する(終えない)。
    """
    login_unselected(client, "P03")
    for index, lecture_id in enumerate(C1_ROUNDS):
        if index > 0:
            next_second()  # 2本目以降の確定は、前の確定と別の秒に行う(仕様の共通の前提)
        confirm_round(client, lecture_id)
        assert record_viewing(client, "play", current_time=10 + index).status_code == 201
        assert record_viewing(client, "pause", current_time=20 + index).status_code == 201
        assert record_quiz(client, lecture_id).status_code == 201
        finish_round(client)
    login_unselected(client, "P10")
    confirm_round(client, "lecture-1")
    assert record_viewing(client, "play").status_code == 201
    assert record_quiz(client, "lecture-1").status_code == 201
    return client


class TestC1ThreeRoundsValuesAndOrder:
    @pytest.mark.parametrize("kind,scope", FOUR, ids=FOUR_IDS)
    def test_c1_round_number_and_order_follow_the_selection_order(self, three_rounds, kind, scope) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 C1
        rows = rows_of(three_rounds, kind, scope, "P03")

        assert rows, "P03 の行がない"
        assert {r["lecture_id"] for r in rows} == set(C1_ROUNDS)
        for r in rows:
            assert r["round_number"] == C1_EXPECTED[r["lecture_id"]], r
        # 行は lecture-5 → lecture-2 → lecture-3 の順(講義IDの昇順ではない)
        assert lecture_sequence(rows) == C1_ROUNDS
        assert [r["round_number"] for r in rows] == sorted((r["round_number"] for r in rows), key=int)

    @pytest.mark.parametrize("kind,scope", FOUR, ids=FOUR_IDS)
    def test_c1_round_number_is_written_as_a_plain_integer(self, three_rounds, kind, scope) -> None:
        # round_number は ' も二重引用符も付かない 1・2・3(本文の行を、CSV として読む前の形で見る)
        raw, _rows = fetch(three_rounds, kind, url_of(kind, scope, "P03"))
        lines = [line for line in raw[len(vl.BOM):].decode("utf-8").split("\r\n") if line.startswith("P03,")]

        assert lines, "P03 の行がない"
        assert {line.split(",", 2)[1] for line in lines} == {"1", "2", "3"}

    def test_c1_bulk_counts_per_participant(self, three_rounds) -> None:
        # 一括でも、ほかの参加者(P10)の学習セッションは数えない(P10 は 1 から)
        for kind in KINDS:
            p10 = rows_of(three_rounds, kind, "all", "P10")
            assert p10, kind
            assert {r["round_number"] for r in p10} == {"1"}, kind


# ---------------------------------------------------------------- C2


@pytest.fixture
def round_without_viewing(client):
    """P04 が、1本目 lecture-5 で小テストだけを記録して回を終え、2本目 lecture-2 で視聴ログと小テストを記録する(終えない)。"""
    login_unselected(client, "P04")
    confirm_round(client, "lecture-5")
    assert record_quiz(client, "lecture-5").status_code == 201
    finish_round(client)
    next_second()
    confirm_round(client, "lecture-2")
    assert record_viewing(client, "play").status_code == 201
    assert record_quiz(client, "lecture-2").status_code == 201
    return client


class TestC2RoundWithoutRecordsIsStillCounted:
    @pytest.mark.parametrize("scope", ["participant", "all"])
    def test_c2_viewing_csv_has_only_round_2(self, round_without_viewing, scope) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 C2
        rows = rows_of(round_without_viewing, "viewing", scope, "P04")

        assert rows, "P04 の視聴ログの行がない"
        assert {r["lecture_id"] for r in rows} == {"lecture-2"}
        # 1本目(記録なし)も数えるので 2。番号は詰まらない(1 の行はない)
        assert {r["round_number"] for r in rows} == {"2"}

    @pytest.mark.parametrize("scope", ["participant", "all"])
    def test_c2_quiz_csv_has_round_1_and_2(self, round_without_viewing, scope) -> None:
        rows = rows_of(round_without_viewing, "quiz", scope, "P04")

        assert lecture_sequence(rows) == ["lecture-5", "lecture-2"]
        for r in rows:
            assert r["round_number"] == {"lecture-5": "1", "lecture-2": "2"}[r["lecture_id"]], r

    @pytest.mark.parametrize("kind", list(KINDS))
    def test_c2_participant_and_bulk_agree(self, round_without_viewing, kind) -> None:
        # 参加者別と一括で、同じ行の round_number は同じ(行がそのまま一致する)
        participant = rows_of(round_without_viewing, kind, "participant", "P04")
        bulk = rows_of(round_without_viewing, kind, "all", "P04")

        assert participant
        assert participant == bulk

    def test_c2_same_learning_session_has_same_round_in_both_csvs(self, round_without_viewing) -> None:
        viewing = rows_of(round_without_viewing, "viewing", "all", "P04")
        quiz = rows_of(round_without_viewing, "quiz", "all", "P04")

        viewing_rounds = {(r["learning_session_id"], r["round_number"]) for r in viewing}
        quiz_rounds = {(r["learning_session_id"], r["round_number"]) for r in quiz}
        assert len(viewing_rounds) == 1
        assert viewing_rounds <= quiz_rounds


# ---------------------------------------------------------------- C3

# 各ケース: (参加者ID, [(学習セッションID, 講義ID, 開始時刻)] を置く順, 期待する {学習セッションID: round_number})
# 置く順(行の ID の順)、学習セッションID の順、講義IDの順が、期待する順と食い違うように選んだ。
C3_CASES = {
    # (a) 開始時刻が同じ2つ: 学習セッションID の文字列の昇順で先が 1
    "a-same-start": (
        "C3-same",
        [
            ("c3a-session-2", "lecture-1", "2026-11-14T07:00:00+00:00"),
            ("c3a-session-1", "lecture-6", "2026-11-14T07:00:00+00:00"),
        ],
        {"c3a-session-1": "1", "c3a-session-2": "2"},
    ),
    # (b) 開始時刻が互いに異なる4つ: 開始時刻の昇順に 1〜4(上限を設けない)
    "b-four-sessions": (
        "C3-four",
        [
            ("c3b-w", "lecture-6", "2026-11-14T03:00:00+00:00"),
            ("c3b-y", "lecture-2", "2026-11-14T04:00:00+00:00"),
            ("c3b-x", "lecture-1", "2026-11-14T02:00:00+00:00"),
            ("c3b-z", "lecture-3", "2026-11-14T01:00:00+00:00"),
        ],
        {"c3b-z": "1", "c3b-x": "2", "c3b-w": "3", "c3b-y": "4"},
    ),
    # (c) 開始時刻の形が違う3つ: 保存された文字列の昇順に 1〜3(時刻の順なら +09:00 の行が先になる)
    "c-mixed-offsets": (
        "C3-mixed",
        [
            ("c3c-a", "lecture-1", "2026-11-14T07:00:00+00:00"),
            ("c3c-b", "lecture-2", "2026-01-01T09:00:00+09:00"),
            ("c3c-c", "lecture-3", "2026-01-01T00:30:00"),
        ],
        {"c3c-c": "1", "c3c-b": "2", "c3c-a": "3"},
    ),
}


def place_sessions(env: vl.Env, learner: str, sessions: list[tuple[str, str, str]]) -> None:
    """学習セッションと、その視聴ログ1行・小テストの受験1回(回答1問)を、DB に直接置く。"""
    conn = env.learning()
    try:
        for index, (ls_id, lecture_id, started_at) in enumerate(sessions):
            conn.execute(
                "INSERT INTO learning_sessions (id, learner_id, lecture_id, started_at) VALUES (?,?,?,?)",
                (ls_id, learner, lecture_id, started_at),
            )
            conn.execute(
                'INSERT INTO viewing_logs (learning_session_id, time_stamp, "current_time", action, duration) '
                "VALUES (?,?,?,?,?)",
                (ls_id, "2026-11-14T08:00:00+00:00", 100 + index, "play", 0.0),
            )
            attempt_id = conn.execute(
                "INSERT INTO quiz_attempts (learning_session_id, created_at, score_numerator, score_denominator) "
                "VALUES (?,?,?,?)",
                (ls_id, "2026-11-14T08:00:00+00:00", 1, 1),
            ).lastrowid
            conn.execute(
                "INSERT INTO quiz_attempt_answers (attempt_id, question_index, selected_answer, is_correct) "
                "VALUES (?,?,?,?)",
                (attempt_id, 1, f"answer-{ls_id}", 1),
            )
        conn.commit()
    finally:
        conn.close()


class TestC3SameStartAndUnexpectedData:
    @pytest.mark.parametrize("case", list(C3_CASES))
    @pytest.mark.parametrize("kind,scope", FOUR, ids=FOUR_IDS)
    def test_c3_round_number_of_directly_placed_sessions(self, env: vl.Env, client, case, kind, scope) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 C3
        learner, sessions, expected = C3_CASES[case]
        place_sessions(env, learner, sessions)
        url = url_of(kind, scope, learner)

        first_raw, rows = fetch(client, kind, url)  # 状態 200(fetch が確かめる)
        second_raw, _ = fetch(client, kind, url)

        mine = [r for r in rows if r["participant_id"] == learner]
        # 置いた記録の行がすべて出る(学習セッションごとに1行)
        assert sorted(r["learning_session_id"] for r in mine) == sorted(expected)
        assert {r["learning_session_id"]: r["round_number"] for r in mine} == expected
        # 行は round_number の昇順
        assert [r["round_number"] for r in mine] == sorted(expected.values(), key=int)
        # 同じ取得を2回行うと本文が一致する
        assert first_raw == second_raw


# ---------------------------------------------------------------- C4


class TestC4NoSideEffects:
    def test_c4_databases_and_schema_unchanged_by_c1_downloads(self, env: vl.Env, three_rounds) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 C4
        before = env.dump_all()
        schema_before = (schema_of(env.tmp_path / "learning.db"), schema_of(env.tmp_path / "tutor.db"))

        for kind, scope in FOUR:
            _raw, rows = fetch(three_rounds, kind, url_of(kind, scope, "P03"))
            assert any(r["participant_id"] == "P03" for r in rows)  # 取得できている(空振りでない)

        assert env.dump_all() == before
        assert (schema_of(env.tmp_path / "learning.db"), schema_of(env.tmp_path / "tutor.db")) == schema_before
