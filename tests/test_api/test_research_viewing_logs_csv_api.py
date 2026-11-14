# 仕様: docs/spec/research-lad-csv-download.md#受入基準 (PBI-1: A1 A2 A3 A4 A5 A6 A7 A8)
# 仕様: docs/spec/research-lad-csv-download.md#受入基準 (PBI-C #56: A3・A4 の改訂、C4 の回帰)
# 仕様: docs/spec/research-lad-csv-download.md#何本目の列round_number共有if2つの-csv-に共通pbi-c
# 仕様: docs/spec/research-lad-csv-download.md#csv-の書式共有if4つに共通pbi-1-で定める
# A9(ブラウザで取得できる)は PO確認。ここでは検証しない。
"""研究用の視聴ログ CSV(GET /research/.../viewing-logs.csv)を、Flask のテストクライアントで通して確認する。

一時ディレクトリの tutor.db・learning.db と偽の LLM を使う。記録は既存の API
(POST /api/viewing-log)で作る。API で作れない状態(A6・A7 の特殊な参加者ID・講義ID、
A8 の固有の参加者ID)だけ DB に直接置く。期待値は仕様の AC と DB の値から導き、
実装の内部クラスには依存しない。

PBI-C(#56)で、見出しの2列目に `round_number` が加わり、lecture_id 以降が1列ずつ後ろへずれた。
列は位置の数字ではなく、見出しの名前(COL)で読む。A3・A4 の回の準備は、選択の確定と回の終了の
HTTP の操作で作る(tests/multi_video_helpers.py)。C1〜C4 は test_research_csv_round_number.py。
"""
from __future__ import annotations

import base64
import csv
import io
import logging
import sqlite3
import uuid
from pathlib import Path

import pytest

from tests.login_helpers import login_as
from tests.multi_video_helpers import confirm_round, finish_round, next_second
from tests.selection_helpers import login_unselected
from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway

USER_ENV = "RESEARCHER_BASIC_AUTH_USER"
PASSWORD_ENV = "RESEARCHER_BASIC_AUTH_PASSWORD"
RESEARCHER = ("researcher", "s3cret-pass")
ALL_URL = "/research/viewing-logs.csv"
BOM = b"\xef\xbb\xbf"
HEADER = [
    "participant_id",
    "round_number",
    "lecture_id",
    "learning_session_id",
    "viewing_log_id",
    "time_stamp",
    "current_time",
    "action",
    "duration",
]
HEADER_LINE = ",".join(HEADER)
COL = {name: index for index, name in enumerate(HEADER)}
PID, ROUND, LECTURE, LS, VID, TS, POS, ACTION, DURATION = (COL[name] for name in HEADER)


def participant_url(pid: str) -> str:
    return f"/research/participants/{pid}/viewing-logs.csv"


def basic(user: str, password: str) -> dict[str, str]:
    raw = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {raw}"}


AUTH = basic(*RESEARCHER)


class Env:
    def __init__(self, monkeypatch, tmp_path: Path) -> None:
        self.monkeypatch = monkeypatch
        self.tmp_path = tmp_path
        self.llm = FakeLlmGateway(response="スタブ応答")
        monkeypatch.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
        monkeypatch.setenv("LEARNING_DB_PATH", str(tmp_path / "learning.db"))
        monkeypatch.setattr(
            "framework_drivers.platform.wiring.build_llm_gateway", lambda: self.llm
        )
        from tests.test_interfaces.fakes.fake_video_duration_resolver import (
            FakeVideoDurationResolver,
        )

        monkeypatch.setattr(
            "framework_drivers.platform.wiring.build_video_duration_resolver",
            lambda: FakeVideoDurationResolver(duration_sec=600),
        )

    def start(self, user: str | None = RESEARCHER[0], password: str | None = RESEARCHER[1]):
        for name, value in ((USER_ENV, user), (PASSWORD_ENV, password)):
            if value is None:
                self.monkeypatch.delenv(name, raising=False)
            else:
                self.monkeypatch.setenv(name, value)
        from framework_drivers.platform.main import create_app

        app = create_app()
        app.config["TESTING"] = True
        app.config["PROPAGATE_EXCEPTIONS"] = False
        client = app.test_client()
        login_as(client, "1")  # 参加者としてログイン済み(研究者の Basic 認証とは別系統)
        return client

    def tutor(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.tmp_path / "tutor.db"))
        conn.row_factory = sqlite3.Row
        return conn

    def learning(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.tmp_path / "learning.db"))
        conn.row_factory = sqlite3.Row
        return conn

    def dump_all(self) -> dict[str, dict[str, list[tuple]]]:
        result: dict[str, dict[str, list[tuple]]] = {}
        for label, conn in (("tutor", self.tutor()), ("learning", self.learning())):
            try:
                tables = [
                    r[0]
                    for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                    )
                ]
                result[label] = {
                    t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2")]
                    for t in tables
                }
            finally:
                conn.close()
        return result

    def db_logs(self) -> list[sqlite3.Row]:
        """DB の視聴ログ全行(参加者ID・講義ID付き)。記録した順(id 昇順)。"""
        conn = self.learning()
        try:
            return conn.execute(
                "SELECT s.learner_id, s.lecture_id, s.id AS ls_id, v.id AS v_id, v.time_stamp, "
                'v."current_time" AS pos, v.action, v.duration '
                "FROM viewing_logs v JOIN learning_sessions s ON s.id = v.learning_session_id "
                "ORDER BY v.id"
            ).fetchall()
        finally:
            conn.close()


@pytest.fixture
def env(monkeypatch, tmp_path: Path) -> Env:
    return Env(monkeypatch, tmp_path)


@pytest.fixture
def client(env: Env):
    return env.start()


# ---------------------------------------------------------------- 記録と読み取りの補助


def record(
    client,
    pid: str,
    *,
    position: int = 10,
    action: str = "play",
    duration: float = 0,
    time_stamp: str = "2026-10-29T01:00:00+00:00",
) -> None:
    """既存の API で視聴ログを1件記録する(参加者としてログインし直して送る)。"""
    if getattr(client, "_login_id", None) != pid:
        login_as(client, pid)
    response = client.post(
        "/api/viewing-log",
        json={
            "participant_id": pid,
            "time_stamp": time_stamp,
            "current_time": position,
            "action": action,
            "duration": duration,
        },
    )
    assert response.status_code == 201, response.get_data(as_text=True)


def record_two_rounds_5_then_2(client, env: Env, pid: str) -> None:
    """pid が1本目として lecture-5 を選んで視聴ログを記録して回を終え、2本目として lecture-2 を選んで記録する。

    仕様の A4 の準備(「n本目として講義 L を選ぶ」= 選択の確定、「回を終える」= 終了ボタンの保存)。
    2本目の確定は、1本目の確定と別の秒に行う(next_second)。視聴ログは API で記録する。
    1本目は2件(viewing_log_id の順を確かめるため)、2本目は1件。
    """
    login_unselected(client, pid)
    confirm_round(client, "lecture-5")
    record(client, pid, position=51, time_stamp="2026-10-29T03:00:00+00:00")
    record(client, pid, position=52, action="pause", time_stamp="2026-10-29T02:00:00+00:00")
    finish_round(client)
    next_second()
    confirm_round(client, "lecture-2")
    record(client, pid, position=21, time_stamp="2026-10-29T01:00:00+00:00")
    lectures = [r["lecture_id"] for r in env.db_logs() if r["learner_id"] == pid]
    assert lectures == ["lecture-5", "lecture-5", "lecture-2"], "テストの準備: 2回の記録を作れていない"


def insert_directly(
    env: Env,
    learner_id: str,
    lecture_id: str,
    *,
    position: int = 5,
    action: str = "play",
    duration: float = 1.0,
    time_stamp: str = "2026-10-29T01:00:00+00:00",
) -> str:
    """API で作れない参加者ID・講義IDの学習セッションと視聴ログ1行を、DB に直接置く。学習セッションIDを返す。"""
    ls_id = str(uuid.uuid4())
    conn = env.learning()
    try:
        conn.execute(
            "INSERT INTO learning_sessions (id, learner_id, lecture_id, started_at) VALUES (?,?,?,?)",
            (ls_id, learner_id, lecture_id, "2026-10-29T00:00:00+00:00"),
        )
        conn.execute(
            'INSERT INTO viewing_logs (learning_session_id, time_stamp, "current_time", action, duration) '
            "VALUES (?,?,?,?,?)",
            (ls_id, time_stamp, position, action, duration),
        )
        conn.commit()
    finally:
        conn.close()
    return ls_id


def text_of(response) -> str:
    """BOM を除いた本文(BOM があることは A2 で確かめる)。"""
    raw = response.data
    assert raw.startswith(BOM), "本文が BOM で始まっていない"
    return raw[len(BOM):].decode("utf-8")


def parse(text: str) -> list[list[str]]:
    """RFC 4180 の規則で行と値に分ける(囲みの中の CR・LF を保つ)。"""
    return list(csv.reader(io.StringIO(text, newline="")))


def fetch_rows(client, url: str) -> list[list[str]]:
    response = client.get(url, headers=AUTH)
    assert response.status_code == 200, response.get_data(as_text=True)
    return parse(text_of(response))


def body_rows(client, url: str) -> list[list[str]]:
    rows = fetch_rows(client, url)
    assert rows[0] == HEADER
    return rows[1:]


# ---------------------------------------------------------------- A1


class TestA1RejectWithoutValidCredentials:
    @pytest.fixture
    def seeded(self, env: Env, client):
        record(client, "P02", position=7, action="play")
        return client

    @pytest.mark.parametrize(
        "headers",
        [
            None,
            basic("researcher", "wrong-pass"),
            basic("wrong-user", RESEARCHER[1]),
            basic("", ""),
        ],
        ids=["none", "wrong-password", "wrong-user", "empty"],
    )
    @pytest.mark.parametrize("url", [ALL_URL, participant_url("P02")], ids=["all", "participant"])
    def test_a1_rejected_with_challenge_and_no_content(self, env, seeded, url, headers) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 A1
        # seeded のクライアントは参加者としてログイン済み(参加者としてログインしただけ、の場合を含む)
        ls_id = env.db_logs()[0]["ls_id"]

        response = seeded.get(url, headers=headers or {})

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"].lower().startswith("basic")
        body = response.get_data(as_text=True)
        assert "P02" not in body
        assert ls_id not in body

    @pytest.mark.parametrize("url", [ALL_URL, participant_url("P02")], ids=["all", "participant"])
    def test_a1_participant_logged_in_without_basic_is_rejected(self, seeded, url) -> None:
        # 参加者のログインセッション(Cookie)だけでは取得できない
        response = seeded.get(url)

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert "P02" not in response.get_data(as_text=True)

    @pytest.mark.parametrize(
        "user,password",
        [
            (None, None),
            ("researcher", None),
            (None, "s3cret-pass"),
            ("", ""),
            ("researcher", ""),
            ("", "s3cret-pass"),
        ],
        ids=["both-unset", "password-unset", "user-unset", "both-empty", "password-empty", "user-empty"],
    )
    @pytest.mark.parametrize("url", [ALL_URL, participant_url("P02")], ids=["all", "participant"])
    def test_a1_unset_credentials_always_reject(self, env: Env, user, password, url) -> None:
        client = env.start(user, password)
        record(client, "P02", position=7)
        ls_id = env.db_logs()[0]["ls_id"]
        candidates = [RESEARCHER, ("", ""), ("researcher", ""), ("", "s3cret-pass"), (user or "", password or "")]

        for candidate in candidates:
            response = client.get(url, headers=basic(*candidate))
            assert response.status_code == 401, candidate
            assert "WWW-Authenticate" in response.headers
            body = response.get_data(as_text=True)
            assert "P02" not in body and ls_id not in body
        assert client.get(url).status_code == 401

    @pytest.mark.parametrize("url", [ALL_URL, participant_url("P02")], ids=["all", "participant"])
    def test_a1_valid_credentials_pass_the_same_requests(self, seeded, url) -> None:
        assert seeded.get(url, headers=AUTH).status_code == 200


# ---------------------------------------------------------------- A2


class TestA2ResponseShape:
    @pytest.fixture
    def seeded(self, client):
        record(client, "P01", position=3)
        record(client, "P01", position=9, action="pause")
        return client

    @pytest.mark.parametrize(
        "url,filename",
        [
            (participant_url("P01"), "viewing-logs_P01.csv"),
            (ALL_URL, "viewing-logs_all.csv"),
            (participant_url("%201"), "viewing-logs_participant.csv"),
        ],
        ids=["participant", "all", "unsafe-id"],
    )
    def test_a2_status_headers_and_filename(self, seeded, url, filename) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 A2
        response = seeded.get(url, headers=AUTH)

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
        disposition = response.headers["Content-Disposition"]
        assert disposition.startswith("attachment")
        assert f'filename="{filename}"' in disposition

    @pytest.mark.parametrize("url", [participant_url("P01"), ALL_URL], ids=["participant", "all"])
    def test_a2_bom_once_and_crlf_everywhere(self, seeded, url) -> None:
        response = seeded.get(url, headers=AUTH)

        raw = response.data
        assert raw.startswith(BOM)
        assert raw.count(BOM) == 1
        text = raw[len(BOM):].decode("utf-8")
        assert text.endswith("\r\n")
        assert text.startswith(HEADER_LINE + "\r\n")
        # CRLF を除くと、CR も LF も残らない(単独の LF や CR で終わる行がない)
        assert "\r" not in text.replace("\r\n", "")
        assert "\n" not in text.replace("\r\n", "")
        assert text.count("\r\n") == 3  # 見出し + 2行


# ---------------------------------------------------------------- A3


class TestA3Contents:
    def test_a3_three_events_of_participant_p02(self, env: Env, client) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 A3(PBI-C で改訂: 見出しと round_number)
        login_unselected(client, "P02")
        confirm_round(client, "lecture-1")  # 1本目として lecture-1 を選ぶ(選択の確定)
        record(client, "P02", position=0, action="play", duration=0,
               time_stamp="2026-10-29T01:00:00+00:00")
        record(client, "P02", position=30, action="forward_skip", duration=10,
               time_stamp="2026-10-29T01:00:05+00:00")
        record(client, "P02", position=20, action="backward_seek", duration=-12.7,
               time_stamp="2026-10-29T01:00:09+00:00")

        response = client.get(participant_url("P02"), headers=AUTH)

        assert response.status_code == 200
        text = text_of(response)
        assert text.split("\r\n")[0] == (
            "participant_id,round_number,lecture_id,learning_session_id,viewing_log_id,"
            "time_stamp,current_time,action,duration"
        )
        rows = parse(text)
        assert rows[0] == HEADER
        assert len(rows) == 4
        db = env.db_logs()
        assert len(db) == 3
        for row, d in zip(rows[1:], db):
            assert len(row) == len(HEADER)
            assert row[PID] == "P02"
            assert row[ROUND] == "1"
            assert row[LECTURE] == "lecture-1"
            assert row[LS] == d["ls_id"]
            assert row[VID] == str(d["v_id"])
            assert row[TS] == d["time_stamp"]
        assert [r[VID] for r in rows[1:]] == sorted((r[VID] for r in rows[1:]), key=int)
        assert [r[POS] for r in rows[1:]] == ["0", "30", "20"]
        assert [r[ACTION] for r in rows[1:]] == ["play", "forward_skip", "backward_seek"]
        assert [r[DURATION] for r in rows[1:]] == ["0.0", "10.0", "-12.0"]

    def test_a3_other_participants_rows_are_not_in_participant_csv(self, client) -> None:
        record(client, "P02", position=1)
        record(client, "P01", position=2)

        rows = body_rows(client, participant_url("P02"))

        assert [r[PID] for r in rows] == ["P02"]


# ---------------------------------------------------------------- A4


class TestA4AllParticipantsAndOrder:
    PIDS = ("P01", "P02", "P10", "10", "2")
    SORTED = ["10", "2", "P01", "P02", "P10"]
    OTHERS = ("P01", "P10", "10", "2")

    @pytest.fixture
    def populated(self, env: Env, client):
        for pid in self.OTHERS:
            record(client, pid, position=11, time_stamp="2026-10-29T05:00:00+00:00")
            # 後に記録した行の time_stamp が先の行より早い
            record(client, pid, position=12, action="pause", time_stamp="2026-10-29T04:00:00+00:00")
            # 同じ秒
            record(client, pid, position=13, time_stamp="2026-10-29T04:00:00+00:00")
        record_two_rounds_5_then_2(client, env, "P02")
        return client

    def test_a4_bulk_is_exactly_the_union_of_per_participant_csvs_in_order(self, populated) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 A4(PBI-C で改訂: 同じ参加者の中は回の順)
        bulk = body_rows(populated, ALL_URL)

        per_participant: list[list[str]] = []
        for pid in self.SORTED:
            part = body_rows(populated, participant_url(pid))
            assert part, pid
            assert all(r[PID] == pid for r in part)
            per_participant += part
        assert bulk == per_participant
        assert len(bulk) == 4 * 3 + 3

    def test_a4_p01_is_included(self, populated) -> None:
        assert "P01" in {r[PID] for r in body_rows(populated, ALL_URL)}

    def test_a4_participant_ids_sort_as_strings(self, populated) -> None:
        bulk = body_rows(populated, ALL_URL)

        ordered: list[str] = []
        for r in bulk:
            if not ordered or ordered[-1] != r[PID]:
                ordered.append(r[PID])
        assert ordered == self.SORTED

    def test_a4_within_participant_sorted_by_round_then_record_order(self, populated) -> None:
        bulk = body_rows(populated, ALL_URL)

        p02 = [r for r in bulk if r[PID] == "P02"]
        # 1本目の lecture-5 の行(round_number = 1)が、2本目の lecture-2 の行(2)より前。講義IDの昇順ではない
        assert [(r[ROUND], r[LECTURE]) for r in p02] == [
            ("1", "lecture-5"), ("1", "lecture-5"), ("2", "lecture-2"),
        ]
        # 同じ回の中は viewing_log_id の昇順(1本目の2行目は、1行目より早い time_stamp)
        assert [r[POS] for r in p02] == ["51", "52", "21"]
        first_round_ids = [int(r[VID]) for r in p02[:2]]
        assert first_round_ids == sorted(first_round_ids)
        for pid in self.OTHERS:
            rows = [r for r in bulk if r[PID] == pid]
            ids = [int(r[VID]) for r in rows]
            assert ids == sorted(ids)
            assert [r[POS] for r in rows] == ["11", "12", "13"]

    def test_a4_round_number_is_counted_per_participant(self, populated) -> None:
        # P02 以外の参加者の行の round_number は 1(参加者ごとに数える)
        bulk = body_rows(populated, ALL_URL)

        for pid in self.OTHERS:
            rounds = [r[ROUND] for r in bulk if r[PID] == pid]
            assert rounds == ["1", "1", "1"], pid

    def test_a4_record_order_wins_over_time_stamp_order(self, populated) -> None:
        rows = [r for r in body_rows(populated, ALL_URL) if r[PID] == "P01"]

        # 2行目は1行目より早い時刻、3行目は2行目と同じ秒。それでも記録順に並ぶ
        assert [r[TS] for r in rows] == [
            "2026-10-29T05:00:00+00:00",
            "2026-10-29T04:00:00+00:00",
            "2026-10-29T04:00:00+00:00",
        ]
        assert [r[ACTION] for r in rows] == ["play", "pause", "play"]

    def test_a4_repeated_download_is_identical(self, populated) -> None:
        first = populated.get(ALL_URL, headers=AUTH)
        second = populated.get(ALL_URL, headers=AUTH)

        assert first.status_code == 200
        assert len(first.data) > len(BOM) + len(HEADER_LINE)
        assert first.data == second.data


# ---------------------------------------------------------------- A5


class TestA5EmptyIsHeaderOnly:
    EMPTY = BOM + (HEADER_LINE + "\r\n").encode("utf-8")

    def test_a5_unknown_participant(self, client) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 A5
        record(client, "P02", position=1)

        response = client.get(participant_url("nobody"), headers=AUTH)

        assert response.status_code == 200
        assert response.data == self.EMPTY

    def test_a5_participant_with_session_but_no_logs(self, env: Env, client) -> None:
        login_as(client, "P03")  # 学習セッションだけを作る(視聴ログは記録しない)
        conn = env.learning()
        try:
            sessions = conn.execute(
                "SELECT COUNT(*) AS n FROM learning_sessions WHERE learner_id='P03'"
            ).fetchone()["n"]
        finally:
            conn.close()
        assert sessions == 1  # テストの準備の確認

        response = client.get(participant_url("P03"), headers=AUTH)

        assert response.status_code == 200
        assert response.data == self.EMPTY

    def test_a5_bulk_with_no_viewing_logs(self, client) -> None:
        response = client.get(ALL_URL, headers=AUTH)

        assert response.status_code == 200
        assert response.data == self.EMPTY

    @pytest.mark.parametrize("encoded", ["%201", "1%20"], ids=["leading-space", "trailing-space"])
    def test_a5_participant_id_is_matched_as_is(self, client, encoded) -> None:
        record(client, "1", position=44)

        padded = client.get(participant_url(encoded), headers=AUTH)

        assert padded.status_code == 200
        assert padded.data == self.EMPTY
        exact = body_rows(client, participant_url("1"))
        assert [r[POS] for r in exact] == ["44"]


# ---------------------------------------------------------------- A6


class TestA6QuotingOfSpecialCharacters:
    SPECIAL_PID = 'a,b"c\nd'

    def test_a6_participant_id_with_comma_quote_and_lf_is_quoted(self, env: Env, client) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 A6
        insert_directly(env, self.SPECIAL_PID, "lecture-1", position=77, action="pause", duration=2.0)

        response = client.get(ALL_URL, headers=AUTH)

        assert response.status_code == 200
        text = text_of(response)
        assert '"a,b""c\nd"' in text  # 値全体を囲み、中の二重引用符を重ねる(LF はそのまま)
        rows = parse(text)
        row = [r for r in rows[1:] if r[POS] == "77"]
        assert len(row) == 1
        assert row[0][PID] == self.SPECIAL_PID
        assert len(row[0]) == len(HEADER)
        assert rows[0] == HEADER

    def test_a6_plain_values_are_not_quoted(self, env: Env, client) -> None:
        insert_directly(env, self.SPECIAL_PID, "lecture-1")
        record(client, "P01", position=3)

        text = text_of(client.get(ALL_URL, headers=AUTH))

        p01_line = next(line for line in text.split("\r\n") if line.startswith("P01,"))
        assert '"' not in p01_line


# ---------------------------------------------------------------- A7


class TestA7FormulaGuard:
    LECTURES = ["=1+1", "+1", "-1", "@SUM(A1)", "\tx", "\rx"]

    def test_a7_lecture_id_starting_with_formula_characters_gets_apostrophe(self, env: Env, client) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 A7
        ids = {
            lecture: insert_directly(env, "formula-user", lecture, position=100 + i)
            for i, lecture in enumerate(self.LECTURES)
        }
        record(client, "P02", position=20, action="backward_seek", duration=-12.7)

        response = client.get(ALL_URL, headers=AUTH)

        assert response.status_code == 200
        text = text_of(response)
        rows = parse(text)
        assert rows[0] == HEADER
        by_session = {r[LS]: r for r in rows[1:]}
        for lecture, ls_id in ids.items():
            assert by_session[ls_id][LECTURE] == "'" + lecture, repr(lecture)
            assert len(by_session[ls_id]) == len(HEADER)
        # 囲みの規則は ' を付けた後の値に掛かる(CR を含むので囲まれ、' は囲みの内側の先頭)
        assert '"\'\rx"' in text
        # 数値の列には ' を付けない
        backward = [r for r in rows[1:] if r[PID] == "P02"]
        assert len(backward) == 1
        assert backward[0][DURATION] == "-12.0"
        assert backward[0][POS] == "20"
        assert backward[0][VID].isdigit()
        assert backward[0][ROUND] == "1"  # 数値の列(round_number)にも ' を付けない(C4)

    def test_a7_apostrophe_is_not_added_to_ordinary_values(self, env: Env, client) -> None:
        record(client, "P02", position=1)
        insert_directly(env, "formula-user", "=1+1")

        rows = body_rows(client, ALL_URL)

        p02 = [r for r in rows if r[PID] == "P02"]
        assert [p02[0][PID], p02[0][LECTURE]] == ["P02", "lecture-1"]
        assert p02[0][ACTION] == "play"
        assert not any(v.startswith("'") for v in p02[0])


# ---------------------------------------------------------------- A8


class TestA8NoStoreNoLogNoWriteNoRegression:
    @pytest.mark.parametrize("url", [ALL_URL, participant_url("P01"), participant_url("nobody")])
    def test_a8_success_has_no_store(self, client, url) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 A8
        record(client, "P01", position=1)

        response = client.get(url, headers=AUTH)

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"

    @pytest.mark.parametrize("url", [ALL_URL, participant_url("P01")], ids=["all", "participant"])
    @pytest.mark.parametrize("headers", [{}, basic("researcher", "bad")], ids=["none", "wrong"])
    def test_a8_rejection_has_no_store(self, client, url, headers) -> None:
        response = client.get(url, headers=headers)

        assert response.status_code == 401
        assert response.headers["Cache-Control"] == "no-store"

    def test_a8_unset_credentials_rejection_has_no_store(self, env: Env) -> None:
        client = env.start(None, None)

        response = client.get(ALL_URL, headers=AUTH)

        assert response.status_code == 401
        assert response.headers["Cache-Control"] == "no-store"

    def test_a8_ids_are_not_logged_and_databases_are_unchanged(self, env: Env, client, caplog) -> None:
        marker = "UNIQUE-MARKER-7f3a9c-固有の参加者"
        marker_session = insert_directly(env, marker, "lecture-1", position=909)
        record(client, "P01", position=1)
        before = env.dump_all()

        with caplog.at_level(logging.DEBUG):
            caplog.clear()
            all_response = client.get(ALL_URL, headers=AUTH)
            one_response = client.get(participant_url(marker), headers=AUTH)
            rejected = client.get(ALL_URL)

        assert all_response.status_code == 200 and one_response.status_code == 200
        assert rejected.status_code == 401
        assert marker in text_of(all_response)  # 取得できている(ログに出ないことの検査が空振りでない)
        assert marker_session in text_of(one_response)
        assert marker not in caplog.text
        assert marker_session not in caplog.text
        assert env.dump_all() == before

    def test_a8_databases_are_unchanged_for_empty_and_unknown_requests(self, env: Env, client) -> None:
        record(client, "P01", position=1)
        before = env.dump_all()

        responses = [
            client.get(participant_url("nobody"), headers=AUTH),
            client.get(participant_url("%201"), headers=AUTH),
            client.get(ALL_URL, headers=AUTH),
        ]

        assert [r.status_code for r in responses] == [200, 200, 200]
        assert env.dump_all() == before
        assert [r["learner_id"] for r in env.db_logs()] == ["P01"]

    def test_a8_participant_apis_still_work_without_credentials(self, client) -> None:
        # 既存を壊さない: 参加者の記録 API は Basic 認証なしのまま
        record(client, "P01", position=1)  # 201 を内部で確認する
