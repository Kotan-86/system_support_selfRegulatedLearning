# 仕様: docs/spec/research-dialog-download.md#受入基準 (R1 R2 R3 R4 R5 R6 R7 R8 R9)
# 仕様: docs/spec/research-dialog-download.md#url-と資格情報共有if固定済み2026-10-19
# R10(ブラウザでの取得)は PO確認。ここでは検証しない。
"""研究用ダウンロード(GET /research/...)を、起動から Flask のテストクライアントで通して確認する。

一時ディレクトリの tutor.db・learning.db と偽の LLM を使う。期待値は仕様の AC と DB の値から導き、
実装の内部には依存しない。
"""
from __future__ import annotations

import base64
import json
import logging
import re
import sqlite3
from pathlib import Path

import pytest

from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway

USER_ENV = "RESEARCHER_BASIC_AUTH_USER"
PASSWORD_ENV = "RESEARCHER_BASIC_AUTH_PASSWORD"
RESEARCHER = ("researcher", "s3cret-pass")
TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")
ALL_URL = "/research/dialog-logs"
TOP_KEYS = [
    "format_version",
    "participant_id",
    "lecture_id",
    "learning_session_id",
    "tutor_session_id",
    "ended_at",
    "end_method",
    "messages",
]
ASSISTANT_KEYS = [
    "role",
    "content",
    "timestamp",
    "utterance_type",
    "dialogue_move",
    "interpretation_state",
]


def participant_url(pid: str) -> str:
    return f"/research/participants/{pid}/dialog-logs"


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
        return app.test_client()

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


@pytest.fixture
def env(monkeypatch, tmp_path: Path) -> Env:
    return Env(monkeypatch, tmp_path)


@pytest.fixture
def client(env: Env):
    return env.start()


def chat(client, text: str, pid: str = "1", **extra):
    body = {"message": text, "participant_id": pid, **extra}
    response = client.post("/chat", json=body)
    assert response.status_code == 200, response.get_data(as_text=True)
    return response


def save(client, pid: str = "1", end_method: str = "end_button"):
    response = client.post(
        "/api/dialog-log", json={"participant_id": pid, "end_method": end_method}
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    return response


def get_json(client, url: str, headers=AUTH):
    response = client.get(url, headers=headers)
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()


def keys_of(items: list[dict]) -> list[tuple[str, str]]:
    return [(i["participant_id"], i["tutor_session_id"]) for i in items]


# ---------------------------------------------------------------- R1


class TestR1RejectWithoutValidCredentials:
    @pytest.fixture
    def seeded(self, env: Env, client):
        chat(client, "SECRETBODY-質問", "1")
        save(client, "1")
        return client

    @pytest.mark.parametrize(
        "headers",
        [
            None,
            basic("researcher", "wrong-pass"),
            basic("wrong-user", RESEARCHER[1]),
            basic("", ""),
            {"Authorization": "Bearer s3cret-pass"},
            {"Authorization": "Basic !!not-base64!!"},
        ],
        ids=["none", "wrong-password", "wrong-user", "empty", "bearer", "garbage"],
    )
    @pytest.mark.parametrize("url", [ALL_URL, participant_url("1")], ids=["all", "participant"])
    def test_r1_rejected_with_challenge_and_no_content(self, env, seeded, url, headers) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R1
        tutor = env.tutor()
        ts_id = tutor.execute("SELECT id FROM sessions").fetchone()["id"]
        ls_id = env.learning().execute("SELECT id FROM learning_sessions").fetchone()["id"]

        response = seeded.get(url, headers=headers or {})

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"].lower().startswith("basic")
        body = response.get_data(as_text=True)
        for leaked in ("SECRETBODY", "スタブ応答", ts_id, ls_id, "participant_id", "tutor_session_id"):
            assert leaked not in body

    def test_r1_valid_credentials_pass_the_same_requests(self, seeded) -> None:
        assert seeded.get(ALL_URL, headers=AUTH).status_code == 200
        assert seeded.get(participant_url("1"), headers=AUTH).status_code == 200

    def test_r1_401_body_does_not_echo_the_requested_participant(self, seeded) -> None:
        response = seeded.get(participant_url("1"))

        assert response.status_code == 401
        assert "participant" not in response.get_data(as_text=True).lower()


# ---------------------------------------------------------------- R2


class TestR2ParticipantCannotFetch:
    @pytest.fixture
    def seeded(self, client):
        chat(client, "SECRETBODY-質問", "1")
        save(client, "1")
        return client

    @pytest.mark.parametrize("url", [ALL_URL, participant_url("1")], ids=["all", "participant"])
    def test_r2_participant_id_in_query_is_not_a_credential(self, seeded, url) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R2
        response = seeded.get(f"{url}?participant_id=1")

        assert response.status_code == 401
        assert "SECRETBODY" not in response.get_data(as_text=True)

    @pytest.mark.parametrize("url", [ALL_URL, participant_url("1")], ids=["all", "participant"])
    def test_r2_participant_id_in_request_body_is_not_a_credential(self, seeded, url) -> None:
        response = seeded.get(url, json={"participant_id": "1"})

        assert response.status_code == 401
        assert "SECRETBODY" not in response.get_data(as_text=True)

    def test_r2_participant_identified_as_basic_user_is_rejected(self, seeded) -> None:
        # 参加者ID を Basic のユーザー名にしても、研究者の資格情報でなければ拒否
        response = seeded.get(participant_url("1"), headers=basic("1", "1"))

        assert response.status_code == 401


# ---------------------------------------------------------------- R3


class TestR3UnsetCredentialsAlwaysReject:
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
    @pytest.mark.parametrize("url", [ALL_URL, participant_url("1")], ids=["all", "participant"])
    def test_r3_every_credential_is_rejected(self, env: Env, user, password, url) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R3
        client = env.start(user, password)
        chat(client, "SECRETBODY-質問", "1")
        candidates = [
            RESEARCHER,
            ("", ""),
            ("researcher", ""),
            ("", "s3cret-pass"),
            (user or "", password or ""),
        ]

        for candidate in candidates:
            response = client.get(url, headers=basic(*candidate))
            assert response.status_code == 401, candidate
            assert "SECRETBODY" not in response.get_data(as_text=True)
        assert client.get(url).status_code == 401

    def test_r3_chat_and_reflect_still_work_when_unset(self, env: Env) -> None:
        client = env.start(None, None)

        assert client.post("/chat", json={"message": "こんにちは", "participant_id": "1"}).status_code == 200
        assert client.get("/reflect?participant_id=1").status_code == 200
        assert client.get("/").status_code in (200, 302)

    def test_r3_chat_and_reflect_work_without_credentials_when_set(self, client) -> None:
        # 参加者の画面と API は、これまでどおり認証なしで使える
        assert client.post("/chat", json={"message": "こんにちは", "participant_id": "1"}).status_code == 200
        assert client.get("/reflect?participant_id=1").status_code == 200


# ---------------------------------------------------------------- R4


class TestR4ParticipantContents:
    def test_r4_two_round_trips_of_participant_1(self, env: Env, client) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R4
        chat(client, "質問その1", "1")
        chat(client, "質問その2", "1")
        chat(client, "参加者2の質問", "2")

        body = get_json(client, participant_url("1"))

        assert isinstance(body, list)
        assert len(body) >= 1
        assert all(item["participant_id"] == "1" for item in body)
        tutor, learning = env.tutor(), env.learning()
        ls = learning.execute(
            "SELECT id, lecture_id FROM learning_sessions WHERE learner_id='1'"
        ).fetchone()
        ts = tutor.execute(
            "SELECT id FROM sessions WHERE learning_session_id=?", (ls["id"],)
        ).fetchone()
        (item,) = body
        assert item["format_version"] == 1
        assert item["tutor_session_id"] == ts["id"]
        assert item["lecture_id"] == ls["lecture_id"]
        assert item["learning_session_id"] == ls["id"]
        messages = item["messages"]
        assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
        assert [m["content"] for m in messages if m["role"] == "user"] == ["質問その1", "質問その2"]
        assert [m["content"] for m in messages if m["role"] == "assistant"] == ["スタブ応答"] * 2
        for m in messages:
            assert TIME_PATTERN.match(m["timestamp"]), m
        assert "参加者2の質問" not in json.dumps(body, ensure_ascii=False)

    def test_r4_internal_judgement_matches_messages_table(self, env: Env, client) -> None:
        chat(client, "質問その1", "1")
        chat(client, "質問その2", "1")

        (item,) = get_json(client, participant_url("1"))

        rows = env.tutor().execute(
            "SELECT role, utterance_type, dialogue_move, interpretation_state, responded_at "
            "FROM messages ORDER BY created_at, id"
        ).fetchall()
        assert len(rows) == 4
        for row, message in zip(rows, item["messages"]):
            assert message["role"] == row["role"]
            if row["role"] == "user":
                assert list(message) == ["role", "content", "timestamp"]
                for key in ("utterance_type", "dialogue_move", "interpretation_state"):
                    assert key not in message
            else:
                assert list(message) == ASSISTANT_KEYS
                assert message["utterance_type"] == row["utterance_type"]
                assert message["dialogue_move"] == row["dialogue_move"]
                expected_state = (
                    json.loads(row["interpretation_state"]) if row["interpretation_state"] else None
                )
                assert message["interpretation_state"] == expected_state
                assert message["timestamp"] == row["responded_at"]

    def test_r4_top_level_key_order_follows_the_spec_example(self, client) -> None:
        # 仕様: docs/spec/research-dialog-download.md#json-の形(論点3 = B: キーは仕様の例の順)
        chat(client, "質問", "1")

        response = client.get(participant_url("1"), headers=AUTH)

        parsed = json.loads(response.get_data(as_text=True), object_pairs_hook=lambda p: p)
        assert [k for k, _ in parsed[0]] == TOP_KEYS

    def test_r4_japanese_is_written_as_utf8_not_escaped(self, client) -> None:
        # 仕様: DR-001 論点3 = B(日本語を \u に変換しない。Content-Type は charset=utf-8)
        chat(client, "日本語の質問です", "1")

        response = client.get(participant_url("1"), headers=AUTH)

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json; charset=utf-8"
        assert "日本語の質問です".encode("utf-8") in response.data
        assert b"\\u" not in response.data

    def test_r4_content_is_not_altered(self, client) -> None:
        text = '  前後の空白と\n改行、"引用符"、<b>タグ</b>、emoji🙂  '
        chat(client, text, "1")

        (item,) = get_json(client, participant_url("1"))

        assert item["messages"][0]["content"] == text.strip() or item["messages"][0]["content"] == text


# ---------------------------------------------------------------- R5


class TestR5SessionsAndEndInfo:
    def test_r5_two_sessions_of_participant_2_with_one_saved(self, env: Env, client) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R5
        chat(client, "lecture-2 の質問", "2")
        chat(client, "lecture-3 の質問", "2", lecture_id="lecture-3")
        saved = save(client, "2").get_json()

        body = get_json(client, participant_url("2"))

        assert len(body) == 2
        by_lecture = {item["lecture_id"]: item for item in body}
        assert set(by_lecture) == {"lecture-2", "lecture-3"}
        row = env.tutor().execute("SELECT * FROM dialog_logs").fetchone()
        assert by_lecture["lecture-2"]["tutor_session_id"] == row["session_id"] == saved["tutor_session_id"]
        assert by_lecture["lecture-2"]["ended_at"] == row["ended_at"]
        assert by_lecture["lecture-2"]["end_method"] == row["end_method"] == "end_button"
        assert by_lecture["lecture-3"]["ended_at"] is None
        assert by_lecture["lecture-3"]["end_method"] is None

    def test_r5_messages_added_after_saving_are_included(self, client) -> None:
        chat(client, "保存前の質問", "2")
        save(client, "2")
        chat(client, "保存後の質問", "2")

        (item,) = get_json(client, participant_url("2"))

        users = [m["content"] for m in item["messages"] if m["role"] == "user"]
        assert users == ["保存前の質問", "保存後の質問"]
        assert len(item["messages"]) == 4
        assert item["end_method"] == "end_button"

    def test_r5_page_leave_method_is_reported(self, client) -> None:
        chat(client, "質問", "2")
        save(client, "2", end_method="page_leave")

        (item,) = get_json(client, participant_url("2"))

        assert item["end_method"] == "page_leave"

    def test_r5_participant_3_saved_without_messages_has_empty_messages(self, client) -> None:
        save(client, "3")

        body = get_json(client, participant_url("3"))

        assert len(body) == 1
        assert body[0]["participant_id"] == "3"
        assert body[0]["messages"] == []
        assert body[0]["end_method"] == "end_button"
        assert TIME_PATTERN.match(body[0]["ended_at"])


# ---------------------------------------------------------------- R6


class TestR6AllParticipants:
    @pytest.fixture
    def populated(self, env: Env, client):
        for pid in ("foo", "2", "10", "1"):
            chat(client, f"{pid}の質問", pid)
        chat(client, "lecture-3 の質問", "2", lecture_id="lecture-3")
        save(client, "1")
        save(client, "2")
        return client

    def test_r6_contains_exactly_the_union_of_per_participant_lists(self, populated) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R6
        everything = get_json(populated, ALL_URL)

        per_participant = []
        for pid in ("1", "10", "2", "foo"):
            per_participant += get_json(populated, participant_url(pid))
        assert everything == per_participant
        assert len(set(keys_of(everything))) == len(everything)

    def test_r6_participant_ids_sort_as_strings(self, populated) -> None:
        everything = get_json(populated, ALL_URL)

        ordered = [item["participant_id"] for item in everything]
        assert ordered == ["1", "10", "2", "2", "foo"]

    def test_r6_unsaved_participants_are_included(self, populated) -> None:
        everything = get_json(populated, ALL_URL)

        foo = [i for i in everything if i["participant_id"] == "foo"]
        assert len(foo) == 1
        assert foo[0]["end_method"] is None

    def test_r6_within_participant_sorted_by_created_at(self, env: Env, populated) -> None:
        tutor = env.tutor()
        # 参加者 2 の2つの対話セッションの作成時刻を、IDの順と逆にする
        body = get_json(populated, participant_url("2"))
        ids = sorted(i["tutor_session_id"] for i in body)
        tutor.execute("UPDATE sessions SET created_at='2026-09-29T05:00:00+00:00' WHERE id=?", (ids[0],))
        tutor.execute("UPDATE sessions SET created_at='2026-09-29T04:00:00+00:00' WHERE id=?", (ids[1],))
        tutor.commit()
        tutor.close()

        again = get_json(populated, ALL_URL)

        two = [i["tutor_session_id"] for i in again if i["participant_id"] == "2"]
        assert two == [ids[1], ids[0]]

    def test_r6_same_second_sessions_are_ordered_by_session_id(self, env: Env, populated) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R6(同じ秒でも並びが決まる)
        tutor = env.tutor()
        tutor.execute("UPDATE sessions SET created_at='2026-09-29T05:00:00+00:00'")
        tutor.commit()
        tutor.close()

        everything = get_json(populated, ALL_URL)

        assert [i["participant_id"] for i in everything] == ["1", "10", "2", "2", "foo"]
        two = [i["tutor_session_id"] for i in everything if i["participant_id"] == "2"]
        assert two == sorted(two)
        assert get_json(populated, ALL_URL) == everything

    def test_r6_naive_and_aware_created_at_do_not_break_the_download(self, env: Env, populated) -> None:
        # 設計 DR-001 M2: CURRENT_TIMESTAMP 形式(タイムゾーン無し)が混ざっても 500 にならない
        tutor = env.tutor()
        row = tutor.execute(
            "SELECT s.id FROM sessions s JOIN messages m ON m.session_id=s.id LIMIT 1"
        ).fetchone()
        tutor.execute("UPDATE sessions SET created_at='2026-09-29 01:00:00' WHERE id=?", (row["id"],))
        tutor.commit()
        tutor.close()

        response = populated.get(ALL_URL, headers=AUTH)

        assert response.status_code == 200


# ---------------------------------------------------------------- R7


class TestR7EmptyList:
    def test_r7_unknown_participant_is_empty_list_with_200(self, client) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R7
        chat(client, "質問", "1")

        response = client.get(participant_url("nobody"), headers=AUTH)

        assert response.status_code == 200
        assert response.get_json() == []

    def test_r7_all_with_no_data_is_empty_list_with_200(self, client) -> None:
        response = client.get(ALL_URL, headers=AUTH)

        assert response.status_code == 200
        assert response.get_json() == []

    @pytest.mark.parametrize("encoded", ["%201", "%20", "1%20", "%E3%80%801"], ids=["leading", "only-space", "trailing", "fullwidth-space"])
    def test_r7_participant_id_is_matched_as_is(self, client, encoded) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R7 (Q6: 変換せずそのまま照合)
        chat(client, "参加者1の質問", "1")

        response = client.get(participant_url(encoded), headers=AUTH)

        assert response.status_code == 200
        assert response.get_json() == []
        assert "参加者1の質問" not in response.get_data(as_text=True)

    def test_r7_exact_id_still_returns_data(self, client) -> None:
        chat(client, "参加者1の質問", "1")

        assert len(get_json(client, participant_url("1"))) == 1


# ---------------------------------------------------------------- R8


class TestR8NoStore:
    @pytest.mark.parametrize("url", [ALL_URL, participant_url("1"), participant_url("nobody")])
    def test_r8_success_has_no_store(self, client, url) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R8
        chat(client, "質問", "1")

        response = client.get(url, headers=AUTH)

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"

    @pytest.mark.parametrize("url", [ALL_URL, participant_url("1")])
    @pytest.mark.parametrize("headers", [{}, basic("researcher", "bad")], ids=["none", "wrong"])
    def test_r8_rejection_has_no_store(self, client, url, headers) -> None:
        response = client.get(url, headers=headers)

        assert response.status_code == 401
        assert response.headers["Cache-Control"] == "no-store"

    def test_r8_unset_credentials_rejection_has_no_store(self, env: Env) -> None:
        client = env.start(None, None)

        response = client.get(ALL_URL, headers=AUTH)

        assert response.status_code == 401
        assert response.headers["Cache-Control"] == "no-store"


# ---------------------------------------------------------------- R9


class TestR9NoLogNoWriteNoRegression:
    def test_r9_content_is_not_logged_and_databases_are_unchanged(
        self, env: Env, client, caplog
    ) -> None:
        # 仕様: docs/spec/research-dialog-download.md#受入基準 R9
        marker = "UNIQUE-MARKER-7f3a9c-固有の文字列"
        chat(client, marker, "1")
        chat(client, marker, "foo")
        save(client, "1")
        before = env.dump_all()

        with caplog.at_level(logging.DEBUG):
            caplog.clear()
            all_response = client.get(ALL_URL, headers=AUTH)
            one_response = client.get(participant_url("1"), headers=AUTH)
            rejected = client.get(ALL_URL)

        assert all_response.status_code == 200 and one_response.status_code == 200
        assert rejected.status_code == 401
        assert marker in all_response.get_data(as_text=True)
        assert marker not in caplog.text
        assert env.dump_all() == before

    def test_r9_databases_are_unchanged_for_empty_and_unknown_requests(self, env: Env, client) -> None:
        chat(client, "質問", "1")
        before = env.dump_all()

        responses = [
            client.get(participant_url("nobody"), headers=AUTH),
            client.get(participant_url("%201"), headers=AUTH),
            client.get(ALL_URL, headers=AUTH),
        ]

        assert [r.status_code for r in responses] == [200, 200, 200]
        assert env.dump_all() == before

    def test_r9_download_does_not_create_sessions_for_unknown_participants(self, env: Env, client) -> None:
        response = client.get(participant_url("brand-new"), headers=AUTH)

        assert response.status_code == 200
        assert response.get_json() == []
        assert env.learning().execute("SELECT COUNT(*) AS n FROM learning_sessions").fetchone()["n"] == 0
        assert env.tutor().execute("SELECT COUNT(*) AS n FROM sessions").fetchone()["n"] == 0

    def test_r9_participant_apis_still_work_without_credentials(self, client) -> None:
        # 既存を壊さない: 参加者の API は認証なしのまま
        chat(client, "質問", "1")

        response = client.post(
            "/api/dialog-log", json={"participant_id": "1", "end_method": "end_button"}
        )

        assert response.status_code == 200
