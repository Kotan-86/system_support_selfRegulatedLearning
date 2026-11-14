# 仕様: docs/spec/research-lad-csv-download.md#受入基準 (PBI-2: B1 B2 B3 B4 B5 B6 B7 B8 B9)
# 仕様: docs/spec/research-lad-csv-download.md#受入基準 (PBI-C #56: B3・B5 の改訂、C4 の回帰)
# 仕様: docs/spec/research-lad-csv-download.md#何本目の列round_number共有if2つの-csv-に共通pbi-c
# 仕様: docs/spec/research-lad-csv-download.md#小テストの-csv-の列この順pbi-2
# B10(ブラウザで取得できる)は PO確認。ここでは検証しない。
"""研究用の小テスト CSV(GET /research/.../quiz-answers.csv)を、Flask のテストクライアントで通して確認する。

一時ディレクトリの tutor.db・learning.db と偽の LLM を使う。記録は既存の API
(POST /api/quiz-attempts)で作る。API で作れない状態(B4 の回答のない受験、
B9 の固有の参加者ID)だけ DB に直接置く。期待値は仕様の AC と DB の値から導き、
実装の内部クラスには依存しない。書式の共通部分(BOM・CRLF・囲み)は PBI-1 のテストで検証済みで、
ここでは小テストの URL でも同じに働くことを確認する。

PBI-C(#56)で、見出しの2列目に `round_number` が加わり、lecture_id 以降が1列ずつ後ろへずれた。
列は位置の数字ではなく、見出しの名前(COL)で読む。B3・B5 の回の準備は、選択の確定と回の終了の
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
ALL_URL = "/research/quiz-answers.csv"
BOM = b"\xef\xbb\xbf"
HEADER = [
    "participant_id",
    "round_number",
    "lecture_id",
    "learning_session_id",
    "attempt_id",
    "attempted_at",
    "score_numerator",
    "score_denominator",
    "question_index",
    "selected_answer",
    "is_correct",
]
HEADER_LINE = ",".join(HEADER)
COL = {name: index for index, name in enumerate(HEADER)}
PID, ROUND, LECTURE, LS, ATTEMPT, AT, NUM, DEN, QI, ANS, OK = (COL[name] for name in HEADER)
URLS = [ALL_URL, "/research/participants/P02/quiz-answers.csv"]
URL_IDS = ["all", "participant"]


def participant_url(pid: str) -> str:
    return f"/research/participants/{pid}/quiz-answers.csv"


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

    def db_rows(self) -> list[sqlite3.Row]:
        """DB の小テスト全行(受験ごと、回答は LEFT JOIN)。受験ID・回答ID の昇順。"""
        conn = self.learning()
        try:
            return conn.execute(
                "SELECT s.learner_id, s.lecture_id, s.id AS ls_id, a.id AS attempt_id, "
                "a.created_at, a.score_numerator AS num, a.score_denominator AS den, "
                "w.question_index AS qi, w.selected_answer AS ans, w.is_correct AS ok "
                "FROM quiz_attempts a JOIN learning_sessions s ON s.id = a.learning_session_id "
                "LEFT JOIN quiz_attempt_answers w ON w.attempt_id = a.id "
                "ORDER BY a.id, w.id"
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


def answers_of(*triples) -> list[dict]:
    return [
        {"question_index": q, "selected_answer": a, "is_correct": c} for q, a, c in triples
    ]


def record(
    client,
    pid: str,
    answers: list[dict] | None = None,
    *,
    score: tuple[int, int] = (1, 3),
    timestamp: str = "2026-10-29T01:00:00+00:00",
) -> int:
    """既存の API で小テストの受験を1回記録する(参加者としてログインし直して送る)。attempt_id を返す。"""
    if getattr(client, "_login_id", None) != pid:
        login_as(client, pid)
    if answers is None:
        answers = answers_of((1, "側面", 1), (2, "B", 0), (3, "C", 0))
    response = client.post(
        "/api/quiz-attempts",
        json={
            "participant_id": pid,
            "timestamp": timestamp,
            "score_numerator": score[0],
            "score_denominator": score[1],
            "answers": answers,
        },
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()["attempt_id"]


def record_two_rounds_5_then_2(client, env: Env, pid: str) -> None:
    """pid が1本目として lecture-5 を選んで受験して回を終え、2本目として lecture-2 を選んで受験する。

    仕様の B5 の準備(「n本目として講義 L を選ぶ」= 選択の確定、「回を終える」= 終了ボタンの保存)。
    2本目の確定は、1本目の確定と別の秒に行う(next_second)。受験は API で記録する。
    1本目は2回(attempt_id の順を確かめるため。2回目の時刻は1回目より早い)、2本目は1回。
    """
    login_unselected(client, pid)
    confirm_round(client, "lecture-5")
    record(client, pid, answers_of((2, "L5a-q2", 0), (1, "L5a-q1", 1)), score=(1, 2),
           timestamp="2026-10-29T03:00:00+00:00")
    record(client, pid, answers_of((1, "L5b", 1)), score=(1, 1), timestamp="2026-10-29T02:00:00+00:00")
    finish_round(client)
    next_second()
    confirm_round(client, "lecture-2")
    record(client, pid, answers_of((1, "L2", 0)), score=(0, 1), timestamp="2026-10-29T01:00:00+00:00")
    lectures = [r["lecture_id"] for r in env.db_rows() if r["learner_id"] == pid]
    assert lectures == ["lecture-5"] * 3 + ["lecture-2"], "テストの準備: 2回の受験を作れていない"


def insert_attempt_directly(
    env: Env,
    learner_id: str,
    lecture_id: str = "lecture-1",
    *,
    answers: list[tuple[int, str, int]] = (),
    score: tuple[int, int] = (2, 5),
    created_at: str = "2026-10-29T01:00:00+00:00",
) -> tuple[str, int]:
    """API で作れない状態(回答のない受験、固有の参加者ID)を DB に直接置く。(学習セッションID, 受験ID)。"""
    ls_id = str(uuid.uuid4())
    conn = env.learning()
    try:
        conn.execute(
            "INSERT INTO learning_sessions (id, learner_id, lecture_id, started_at) VALUES (?,?,?,?)",
            (ls_id, learner_id, lecture_id, "2026-10-29T00:00:00+00:00"),
        )
        cur = conn.execute(
            "INSERT INTO quiz_attempts (learning_session_id, created_at, score_numerator, score_denominator) "
            "VALUES (?,?,?,?)",
            (ls_id, created_at, score[0], score[1]),
        )
        attempt_id = cur.lastrowid
        for q, a, c in answers:
            conn.execute(
                "INSERT INTO quiz_attempt_answers (attempt_id, question_index, selected_answer, is_correct) "
                "VALUES (?,?,?,?)",
                (attempt_id, q, a, c),
            )
        conn.commit()
    finally:
        conn.close()
    return ls_id, attempt_id


def text_of(response) -> str:
    """BOM を除いた本文(BOM があることは B2 で確かめる)。"""
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


# ---------------------------------------------------------------- B1


class TestB1RejectWithoutValidCredentials:
    SECRET = "SECRET-ANSWER-b1-9d2e"

    @pytest.fixture
    def seeded(self, env: Env, client):
        record(client, "P02", answers_of((1, self.SECRET, 1)), score=(1, 1))
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
    @pytest.mark.parametrize("url", URLS, ids=URL_IDS)
    def test_b1_rejected_with_challenge_and_no_content(self, env, seeded, url, headers) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 B1
        # seeded のクライアントは参加者としてログイン済み(参加者としてログインしただけ、の場合を含む)
        ls_id = env.db_rows()[0]["ls_id"]

        response = seeded.get(url, headers=headers or {})

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"].lower().startswith("basic")
        body = response.get_data(as_text=True)
        assert "P02" not in body
        assert ls_id not in body
        assert self.SECRET not in body

    @pytest.mark.parametrize("url", URLS, ids=URL_IDS)
    def test_b1_participant_logged_in_without_basic_is_rejected(self, seeded, url) -> None:
        response = seeded.get(url)

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        body = response.get_data(as_text=True)
        assert "P02" not in body and self.SECRET not in body

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
    @pytest.mark.parametrize("url", URLS, ids=URL_IDS)
    def test_b1_unset_credentials_always_reject(self, env: Env, user, password, url) -> None:
        client = env.start(user, password)
        record(client, "P02", answers_of((1, self.SECRET, 1)), score=(1, 1))
        ls_id = env.db_rows()[0]["ls_id"]
        candidates = [RESEARCHER, ("", ""), ("researcher", ""), ("", "s3cret-pass"), (user or "", password or "")]

        for candidate in candidates:
            response = client.get(url, headers=basic(*candidate))
            assert response.status_code == 401, candidate
            assert "WWW-Authenticate" in response.headers
            body = response.get_data(as_text=True)
            assert "P02" not in body and ls_id not in body and self.SECRET not in body
        assert client.get(url).status_code == 401

    @pytest.mark.parametrize("url", URLS, ids=URL_IDS)
    def test_b1_valid_credentials_pass_the_same_requests(self, seeded, url) -> None:
        # 対照: 実装があれば、正しい資格情報で 200 になる(拒否系が空振りでないことの裏付け)
        response = seeded.get(url, headers=AUTH)

        assert response.status_code == 200
        assert self.SECRET in text_of(response)


# ---------------------------------------------------------------- B2


class TestB2ResponseShape:
    @pytest.fixture
    def seeded(self, client):
        record(client, "P01", answers_of((1, "A", 1), (2, "B", 0)), score=(1, 2))
        return client

    @pytest.mark.parametrize(
        "url,filename",
        [
            (participant_url("P01"), "quiz-answers_P01.csv"),
            (ALL_URL, "quiz-answers_all.csv"),
            (participant_url("%201"), "quiz-answers_participant.csv"),
        ],
        ids=["participant", "all", "unsafe-id"],
    )
    def test_b2_status_headers_and_filename(self, seeded, url, filename) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 B2
        response = seeded.get(url, headers=AUTH)

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
        disposition = response.headers["Content-Disposition"]
        assert disposition.startswith("attachment")
        assert f'filename="{filename}"' in disposition

    @pytest.mark.parametrize("url", [participant_url("P01"), ALL_URL], ids=["participant", "all"])
    def test_b2_bom_once_and_crlf_everywhere(self, seeded, url) -> None:
        response = seeded.get(url, headers=AUTH)

        assert response.status_code == 200
        raw = response.data
        assert raw.startswith(BOM)
        assert raw.count(BOM) == 1
        text = raw[len(BOM):].decode("utf-8")
        assert text.endswith("\r\n")
        assert text.startswith(HEADER_LINE + "\r\n")
        assert "\r" not in text.replace("\r\n", "")
        assert "\n" not in text.replace("\r\n", "")
        assert text.count("\r\n") == 3  # 見出し + 2回答


# ---------------------------------------------------------------- B3


class TestB3Contents:
    def test_b3_two_attempts_all_answers_in_order(self, env: Env, client) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 B3(PBI-C で改訂: 見出しと round_number)
        login_unselected(client, "P02")
        confirm_round(client, "lecture-1")  # 1本目として lecture-1 を選ぶ(選択の確定)
        a1 = record(
            client, "P02",
            answers_of((1, "側面", 1), (2, "B", 0), (3, "C", 1)),
            score=(2, 3), timestamp="2026-10-29T01:00:00+00:00",
        )
        a2 = record(
            client, "P02",
            answers_of((1, "D", 0), (2, "E", 1)),
            score=(1, 2), timestamp="2026-10-29T01:05:00+00:00",
        )
        assert a1 != a2

        response = client.get(participant_url("P02"), headers=AUTH)

        assert response.status_code == 200
        text = text_of(response)
        # 設問の文・正解の列はない
        assert text.split("\r\n")[0] == (
            "participant_id,round_number,lecture_id,learning_session_id,attempt_id,attempted_at,"
            "score_numerator,score_denominator,question_index,selected_answer,is_correct"
        )
        rows = parse(text)
        assert rows[0] == HEADER
        assert len(rows) == 6  # 見出し + 3 + 2(最新1回だけに絞られていない)
        db = env.db_rows()
        assert len(db) == 5
        for row, d in zip(rows[1:], db):
            assert len(row) == len(HEADER)
            assert row[PID] == "P02"
            assert row[ROUND] == "1"
            assert row[LECTURE] == "lecture-1"
            assert row[LS] == d["ls_id"]
            assert row[ATTEMPT] == str(d["attempt_id"])
            assert row[AT] == d["created_at"]
            assert row[NUM] == str(d["num"])
            assert row[DEN] == str(d["den"])
            assert row[QI] == str(d["qi"])
            assert row[ANS] == d["ans"]
            assert row[OK] in ("1", "0")
            assert row[OK] == str(d["ok"])
        body = rows[1:]
        assert [r[ROUND] for r in body] == ["1"] * 5
        assert [r[QI] for r in body] == ["1", "2", "3", "1", "2"]
        assert [r[OK] for r in body] == ["1", "0", "1", "0", "1"]
        assert [r[ANS] for r in body] == ["側面", "B", "C", "D", "E"]
        assert [(r[NUM], r[DEN]) for r in body] == [("2", "3")] * 3 + [("1", "2")] * 2
        assert len({r[ATTEMPT] for r in body[:3]}) == 1
        assert len({r[ATTEMPT] for r in body[3:]}) == 1
        assert body[0][ATTEMPT] != body[3][ATTEMPT]
        assert body[0][ATTEMPT] == str(a1) and body[3][ATTEMPT] == str(a2)

    def test_b3_other_participants_rows_are_not_in_participant_csv(self, client) -> None:
        record(client, "P02")
        record(client, "P01")

        rows = body_rows(client, participant_url("P02"))

        assert len(rows) == 3
        assert {r[PID] for r in rows} == {"P02"}


# ---------------------------------------------------------------- B4


class TestB4AttemptWithoutAnswers:
    def test_b4_attempt_without_answers_is_one_row_with_empty_answer_columns(self, env: Env, client) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 B4
        ls_id, attempt_id = insert_attempt_directly(
            env, "P03", "lecture-1", answers=[], score=(0, 5), created_at="2026-10-29T06:00:00+00:00"
        )
        record(client, "P02", answers_of((1, "A", 1)), score=(1, 1))

        for url in (participant_url("P03"), ALL_URL):
            rows = [r for r in body_rows(client, url) if r[PID] == "P03"]
            assert len(rows) == 1, url
            row = rows[0]
            assert len(row) == len(HEADER)
            # P03 の学習セッションは1つなので round_number は 1
            assert row[:QI] == [
                "P03", "1", "lecture-1", ls_id, str(attempt_id), "2026-10-29T06:00:00+00:00", "0", "5",
            ]
            assert row[QI:] == ["", "", ""]

    def test_b4_attempt_without_answers_does_not_hide_attempts_with_answers(self, env: Env, client) -> None:
        ls_id, empty_id = insert_attempt_directly(env, "P03", "lecture-1", answers=[], score=(0, 5))
        conn = env.learning()
        try:
            cur = conn.execute(
                "INSERT INTO quiz_attempts (learning_session_id, created_at, score_numerator, score_denominator) "
                "VALUES (?,?,?,?)",
                (ls_id, "2026-10-29T07:00:00+00:00", 1, 2),
            )
            second = cur.lastrowid
            conn.execute(
                "INSERT INTO quiz_attempt_answers (attempt_id, question_index, selected_answer, is_correct) "
                "VALUES (?,?,?,?)",
                (second, 1, "X", 1),
            )
            conn.commit()
        finally:
            conn.close()

        rows = body_rows(client, participant_url("P03"))

        assert [(r[ATTEMPT], r[QI], r[ANS], r[OK]) for r in rows] == [
            (str(empty_id), "", "", ""),
            (str(second), "1", "X", "1"),
        ]


# ---------------------------------------------------------------- B5


class TestB5AllParticipantsAndOrder:
    SORTED = ["10", "2", "P01", "P02", "P10"]
    OTHERS = ("P01", "P10", "10", "2")

    @pytest.fixture
    def populated(self, env: Env, client):
        for pid in self.OTHERS:
            # 設問番号は、送った順(5, 2, 1)と昇順(1, 2, 5)が異なるようにする
            # (API は 1〜5 の設問番号しか受け付けない。10 と 2 の数値順は別のテストで DB に直接置いて確かめる)
            record(
                client, pid,
                answers_of((5, "five", 1), (2, "two", 0), (1, "one", 1)),
                score=(2, 3), timestamp="2026-10-29T05:00:00+00:00",
            )
            # 後の受験の時刻が先より早い
            record(client, pid, answers_of((1, "x", 0)), score=(0, 1), timestamp="2026-10-29T04:00:00+00:00")
            # 同じ秒
            record(client, pid, answers_of((1, "y", 1)), score=(1, 1), timestamp="2026-10-29T04:00:00+00:00")
        record_two_rounds_5_then_2(client, env, "P02")
        return client

    def test_b5_bulk_is_exactly_the_union_of_per_participant_csvs_in_order(self, populated) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 B5(PBI-C で改訂: 同じ参加者の中は回の順)
        bulk = body_rows(populated, ALL_URL)

        per_participant: list[list[str]] = []
        for pid in self.SORTED:
            part = body_rows(populated, participant_url(pid))
            assert part, pid
            assert all(r[PID] == pid for r in part)
            per_participant += part
        assert bulk == per_participant
        assert len(bulk) == 4 * 5 + 4

    def test_b5_p01_is_included(self, populated) -> None:
        assert "P01" in {r[PID] for r in body_rows(populated, ALL_URL)}

    def test_b5_participant_ids_sort_as_strings(self, populated) -> None:
        bulk = body_rows(populated, ALL_URL)

        ordered: list[str] = []
        for r in bulk:
            if not ordered or ordered[-1] != r[PID]:
                ordered.append(r[PID])
        assert ordered == self.SORTED

    def test_b5_within_participant_round_then_attempt_then_question_index(self, populated) -> None:
        bulk = body_rows(populated, ALL_URL)

        p02 = [r for r in bulk if r[PID] == "P02"]
        # 1本目の lecture-5 の行(round_number = 1)が、2本目の lecture-2 の行(2)より前。講義IDの昇順ではない
        assert [(r[ROUND], r[LECTURE]) for r in p02] == [("1", "lecture-5")] * 3 + [("2", "lecture-2")]
        # 同じ回の中は attempt_id の昇順(1本目の2回目は、1回目より早い attempted_at)、
        # 同じ受験の中は question_index の昇順(送った順 2, 1 ではない)
        assert [(r[QI], r[ANS]) for r in p02] == [
            ("1", "L5a-q1"), ("2", "L5a-q2"), ("1", "L5b"), ("1", "L2"),
        ]
        first_round_attempts = [int(r[ATTEMPT]) for r in p02[:3]]
        assert first_round_attempts == sorted(first_round_attempts)
        assert first_round_attempts[0] != first_round_attempts[2]
        for pid in self.OTHERS:
            rows = [r for r in bulk if r[PID] == pid]
            attempts = [int(r[ATTEMPT]) for r in rows]
            assert attempts == sorted(attempts)
            # 1回目の中は question_index の昇順(送った順ではない)
            assert [r[QI] for r in rows[:3]] == ["1", "2", "5"]
            assert [r[ANS] for r in rows[:3]] == ["one", "two", "five"]

    def test_b5_round_number_is_counted_per_participant(self, populated) -> None:
        # P02 以外の参加者の行の round_number は 1(参加者ごとに数える)
        bulk = body_rows(populated, ALL_URL)

        for pid in self.OTHERS:
            rounds = [r[ROUND] for r in bulk if r[PID] == pid]
            assert rounds == ["1"] * 5, pid

    def test_b5_attempt_order_wins_over_attempted_at_order(self, populated) -> None:
        rows = [r for r in body_rows(populated, ALL_URL) if r[PID] == "P01"]

        # 2回目は1回目より早い時刻、3回目は2回目と同じ秒。それでも受験した順に並ぶ
        assert [r[AT] for r in rows] == [
            "2026-10-29T05:00:00+00:00",
            "2026-10-29T05:00:00+00:00",
            "2026-10-29T05:00:00+00:00",
            "2026-10-29T04:00:00+00:00",
            "2026-10-29T04:00:00+00:00",
        ]
        assert [r[ANS] for r in rows] == ["one", "two", "five", "x", "y"]

    def test_b5_question_index_is_ordered_numerically(self, env: Env, client) -> None:
        # 文字列順なら 1, 10, 2 になる。API は 1〜5 しか受け付けないので DB に直接置く
        insert_attempt_directly(
            env, "P03", "lecture-1",
            answers=[(10, "ten", 1), (2, "two", 0), (1, "one", 1)],
            score=(2, 3),
        )

        rows = body_rows(client, ALL_URL)

        assert [r[QI] for r in rows] == ["1", "2", "10"]
        assert [r[ANS] for r in rows] == ["one", "two", "ten"]

    def test_b5_repeated_download_is_identical(self, populated) -> None:
        first = populated.get(ALL_URL, headers=AUTH)
        second = populated.get(ALL_URL, headers=AUTH)

        assert first.status_code == 200
        assert len(first.data) > len(BOM) + len(HEADER_LINE)
        assert first.data == second.data


# ---------------------------------------------------------------- B6


class TestB6EmptyIsHeaderOnly:
    EMPTY = BOM + (HEADER_LINE + "\r\n").encode("utf-8")

    def test_b6_unknown_participant(self, client) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 B6
        record(client, "P02")

        response = client.get(participant_url("nobody"), headers=AUTH)

        assert response.status_code == 200
        assert response.data == self.EMPTY

    def test_b6_participant_with_session_but_no_attempts(self, env: Env, client) -> None:
        login_as(client, "P03")  # 学習セッションだけを作る(受験は記録しない)
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

    def test_b6_bulk_with_no_attempts(self, client) -> None:
        response = client.get(ALL_URL, headers=AUTH)

        assert response.status_code == 200
        assert response.data == self.EMPTY

    @pytest.mark.parametrize("encoded", ["%201", "1%20"], ids=["leading-space", "trailing-space"])
    def test_b6_participant_id_is_matched_as_is(self, client, encoded) -> None:
        record(client, "1", answers_of((1, "only-one", 1)), score=(1, 1))

        padded = client.get(participant_url(encoded), headers=AUTH)

        assert padded.status_code == 200
        assert padded.data == self.EMPTY
        exact = body_rows(client, participant_url("1"))
        assert [r[ANS] for r in exact] == ["only-one"]


# ---------------------------------------------------------------- B7


class TestB7QuotingAndJapanese:
    SPECIAL = 'a,b"c\nd'

    def test_b7_special_characters_are_quoted_and_roundtrip(self, env: Env, client) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 B7
        record(client, "P02", answers_of((1, self.SPECIAL, 0), (2, "側面", 1)), score=(1, 2))
        assert self.SPECIAL in [r["ans"] for r in env.db_rows()]  # 準備: API は検査せず保存する

        for url in (participant_url("P02"), ALL_URL):
            response = client.get(url, headers=AUTH)
            assert response.status_code == 200, url
            text = text_of(response)
            assert '"a,b""c\nd"' in text, url  # 値全体を囲み、中の二重引用符を重ねる(LF はそのまま)
            rows = parse(text)
            assert rows[0] == HEADER
            special = [r for r in rows[1:] if r[QI] == "1"]
            assert len(special) == 1
            assert special[0][ANS] == self.SPECIAL
            assert len(special[0]) == len(HEADER)
            # 日本語は UTF-8 のままで書かれる
            assert "側面".encode("utf-8") in response.data
            assert [r[ANS] for r in rows[1:] if r[QI] == "2"] == ["側面"]

    def test_b7_plain_values_are_not_quoted(self, client) -> None:
        record(client, "P02", answers_of((1, 'a,b"c\nd', 0)), score=(0, 1))
        record(client, "P01", answers_of((1, "plain", 1)), score=(1, 1))

        text = text_of(client.get(ALL_URL, headers=AUTH))

        p01_line = next(line for line in text.split("\r\n") if line.startswith("P01,"))
        assert '"' not in p01_line


# ---------------------------------------------------------------- B8


class TestB8FormulaGuard:
    VALUES = ["=1+1", "+1", "-1", "@SUM(A1)"]

    def test_b8_selected_answer_starting_with_formula_characters_gets_apostrophe(self, env: Env, client) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 B8
        record(
            client, "P02",
            answers_of(*[(i + 1, v, i % 2) for i, v in enumerate(self.VALUES)]),
            score=(2, 4),
        )
        assert [r["ans"] for r in env.db_rows()] == self.VALUES  # 準備: API は検査せず保存する

        for url in (participant_url("P02"), ALL_URL):
            response = client.get(url, headers=AUTH)
            assert response.status_code == 200, url
            rows = parse(text_of(response))
            assert rows[0] == HEADER
            body = [r for r in rows[1:] if r[PID] == "P02"]
            assert [r[ANS] for r in body] == ["'" + v for v in self.VALUES]
            # 数値の列には ' を付けない
            for r in body:
                assert len(r) == len(HEADER)
                for col in (ROUND, ATTEMPT, NUM, DEN, QI, OK):
                    assert not r[col].startswith("'"), (HEADER[col], r[col])
                    assert r[col].isdigit(), (HEADER[col], r[col])
            assert [r[NUM] for r in body] == ["2"] * 4
            assert [r[DEN] for r in body] == ["4"] * 4
            assert [r[QI] for r in body] == ["1", "2", "3", "4"]
            assert [r[OK] for r in body] == ["0", "1", "0", "1"]

    def test_b8_apostrophe_is_not_added_to_ordinary_values(self, client) -> None:
        record(client, "P02", answers_of((1, "側面", 1), (2, "B", 0)), score=(1, 2))

        rows = body_rows(client, ALL_URL)

        assert [r[ANS] for r in rows] == ["側面", "B"]
        assert not any(v.startswith("'") for r in rows for v in r)


# ---------------------------------------------------------------- B9


class TestB9NoStoreNoLogNoWriteNoRegression:
    @pytest.mark.parametrize("url", [ALL_URL, participant_url("P01"), participant_url("nobody")])
    def test_b9_success_has_no_store(self, client, url) -> None:
        # 仕様: docs/spec/research-lad-csv-download.md#受入基準 B9
        record(client, "P01")

        response = client.get(url, headers=AUTH)

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"

    @pytest.mark.parametrize("url", [ALL_URL, participant_url("P01")], ids=["all", "participant"])
    @pytest.mark.parametrize("headers", [{}, basic("researcher", "bad")], ids=["none", "wrong"])
    def test_b9_rejection_has_no_store(self, client, url, headers) -> None:
        response = client.get(url, headers=headers)

        assert response.status_code == 401
        assert response.headers["Cache-Control"] == "no-store"

    def test_b9_unset_credentials_rejection_has_no_store(self, env: Env) -> None:
        client = env.start(None, None)

        response = client.get(ALL_URL, headers=AUTH)

        assert response.status_code == 401
        assert response.headers["Cache-Control"] == "no-store"

    def test_b9_answers_are_not_logged_and_databases_are_unchanged(self, env: Env, client, caplog) -> None:
        marker_answer = "UNIQUE-ANSWER-7f3a9c-固有の回答"
        marker_pid = "UNIQUE-PID-5b1d-固有の参加者"
        marker_session, _ = insert_attempt_directly(
            env, marker_pid, "lecture-1", answers=[(1, "z", 1)], score=(1, 1)
        )
        record(client, "P01", answers_of((1, marker_answer, 1)), score=(1, 1))
        before = env.dump_all()

        with caplog.at_level(logging.DEBUG):
            caplog.clear()
            all_response = client.get(ALL_URL, headers=AUTH)
            one_response = client.get(participant_url("P01"), headers=AUTH)
            marker_response = client.get(participant_url(marker_pid), headers=AUTH)
            rejected = client.get(ALL_URL)

        assert all_response.status_code == 200 and one_response.status_code == 200
        assert marker_response.status_code == 200
        assert rejected.status_code == 401
        assert marker_answer in text_of(all_response)  # 取得できている(ログに出ないことの検査が空振りでない)
        assert marker_answer in text_of(one_response)
        assert marker_session in text_of(marker_response)
        assert marker_answer not in caplog.text
        assert marker_pid not in caplog.text
        assert marker_session not in caplog.text
        assert env.dump_all() == before

    def test_b9_databases_are_unchanged_for_empty_and_unknown_requests(self, env: Env, client) -> None:
        record(client, "P01")
        before = env.dump_all()

        responses = [
            client.get(participant_url("nobody"), headers=AUTH),
            client.get(participant_url("%201"), headers=AUTH),
            client.get(ALL_URL, headers=AUTH),
        ]

        assert [r.status_code for r in responses] == [200, 200, 200]
        assert env.dump_all() == before
        assert {r["learner_id"] for r in env.db_rows()} == {"P01"}

    def test_b9_participant_apis_still_work_without_credentials(self, client) -> None:
        # 既存を壊さない: 参加者の記録 API は Basic 認証なしのまま
        record(client, "P01")  # 201 を内部で確認する
