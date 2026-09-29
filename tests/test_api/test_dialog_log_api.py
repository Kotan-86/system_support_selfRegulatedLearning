# 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-1 A2, A4, A5, A6, A7, A8, A11, A12, A13, A14, A15, A17)
# 仕様: docs/spec/dialog-log-save.md#保存-api
"""POST /api/dialog-log を、Flask のテストクライアント(偽の LLM)で起動から通して確認する。"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from application.common.errors import LlmGatewayError
from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway

TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")
_ORIGINAL_MESSAGE_COLUMNS = (
    "id, session_id, role, content, created_at, "
    "utterance_type, dialogue_move, interpretation_state"
)


def _make_client(monkeypatch, tmp_path: Path, llm: FakeLlmGateway):
    monkeypatch.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
    monkeypatch.setenv("LEARNING_DB_PATH", str(tmp_path / "learning.db"))
    monkeypatch.setattr(
        "framework_drivers.platform.wiring.build_llm_gateway", lambda: llm
    )
    from tests.test_interfaces.fakes.fake_video_duration_resolver import (
        FakeVideoDurationResolver,
    )

    monkeypatch.setattr(
        "framework_drivers.platform.wiring.build_video_duration_resolver",
        lambda: FakeVideoDurationResolver(duration_sec=600),
    )
    from framework_drivers.platform.main import create_app

    app = create_app()
    app.config["TESTING"] = True
    # 未捕捉の例外(DB に書けないとき等)を、テストへの例外ではなく 500 の応答にする
    app.config["PROPAGATE_EXCEPTIONS"] = False
    return app.test_client()


@pytest.fixture
def llm() -> FakeLlmGateway:
    return FakeLlmGateway(response="スタブ応答")


@pytest.fixture
def client(monkeypatch, tmp_path: Path, llm: FakeLlmGateway):
    return _make_client(monkeypatch, tmp_path, llm)


@pytest.fixture
def tutor_db(tmp_path: Path):
    conn = sqlite3.connect(str(tmp_path / "tutor.db"))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def learning_db(tmp_path: Path):
    conn = sqlite3.connect(str(tmp_path / "learning.db"))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def _chat(client, text: str, participant_id: str = "1"):
    return client.post("/chat", json={"message": text, "participant_id": participant_id})


def _save(client, participant_id: str = "1", end_method: str = "end_button"):
    return client.post(
        "/api/dialog-log",
        json={"participant_id": participant_id, "end_method": end_method},
    )


def _log_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM dialog_logs ORDER BY session_id").fetchall()


class TestSaveAfterConversation:
    def test_a2_a4_a8_two_round_trips_are_saved_with_identifiers(
        self, client, tutor_db, learning_db
    ) -> None:
        assert _chat(client, "質問1").status_code == 200
        assert _chat(client, "質問2").status_code == 200

        response = _save(client)

        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert set(body) == {"tutor_session_id", "ended_at", "end_method"}
        assert body["end_method"] == "end_button"
        assert TIME_PATTERN.match(body["ended_at"])
        (row,) = _log_rows(tutor_db)
        assert body["tutor_session_id"] == row["session_id"]
        assert body["ended_at"] == row["ended_at"]
        log = json.loads(row["log_json"])
        assert [m["role"] for m in log["messages"]] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert [m["content"] for m in log["messages"] if m["role"] == "user"] == [
            "質問1",
            "質問2",
        ]
        assistants = [m["content"] for m in log["messages"] if m["role"] == "assistant"]
        stored = [
            r["content"]
            for r in tutor_db.execute(
                "SELECT content FROM messages WHERE role='assistant' ORDER BY id"
            )
        ]
        assert assistants == stored

        # A4: 4つの識別子(JSON と列が一致し、実際のセッションに一致する)
        learning = learning_db.execute(
            "SELECT id, learner_id, lecture_id FROM learning_sessions"
        ).fetchall()
        assert len(learning) == 1
        tutor_session = tutor_db.execute("SELECT id, learning_session_id FROM sessions").fetchall()
        assert len(tutor_session) == 1
        assert row["participant_id"] == "1" == log["participant_id"]
        assert row["lecture_id"] == learning[0]["lecture_id"] == log["lecture_id"] == "lecture-1"
        assert row["learning_session_id"] == learning[0]["id"] == log["learning_session_id"]
        assert row["session_id"] == tutor_session[0]["id"] == log["tutor_session_id"]
        assert tutor_session[0]["learning_session_id"] == learning[0]["id"]
        assert row["end_method"] == log["end_method"] == "end_button"
        assert row["ended_at"] == log["ended_at"]

    def test_a4_lecture_follows_the_participant(self, client, tutor_db) -> None:
        _chat(client, "こんにちは", participant_id="2")

        response = _save(client, participant_id="2")

        assert response.status_code == 200
        (row,) = _log_rows(tutor_db)
        assert row["participant_id"] == "2"
        assert row["lecture_id"] == "lecture-2"

    def test_a5_a6_timestamps_and_pipeline_metadata(self, client, tutor_db) -> None:
        _chat(client, "質問")
        _save(client)

        (row,) = _log_rows(tutor_db)
        user, assistant = json.loads(row["log_json"])["messages"]
        assert set(user) == {"role", "content", "timestamp"}
        assert TIME_PATTERN.match(user["timestamp"])
        assert set(assistant) == {
            "role",
            "content",
            "timestamp",
            "utterance_type",
            "dialogue_move",
            "interpretation_state",
        }
        assert TIME_PATTERN.match(assistant["timestamp"])
        assert assistant["timestamp"] >= user["timestamp"]
        db_row = tutor_db.execute(
            "SELECT utterance_type, dialogue_move, interpretation_state, "
            "created_at, responded_at FROM messages WHERE role='assistant'"
        ).fetchone()
        assert assistant["utterance_type"] == db_row["utterance_type"]
        assert assistant["dialogue_move"] == db_row["dialogue_move"]
        expected_state = (
            json.loads(db_row["interpretation_state"])
            if db_row["interpretation_state"]
            else None
        )
        assert assistant["interpretation_state"] == expected_state
        assert assistant["timestamp"] == db_row["responded_at"]

    def test_a8_page_leave_is_accepted_and_recorded(self, client, tutor_db) -> None:
        _chat(client, "質問")

        response = _save(client, end_method="page_leave")

        assert response.status_code == 200
        assert response.get_json()["end_method"] == "page_leave"
        (row,) = _log_rows(tutor_db)
        assert row["end_method"] == "page_leave"
        assert json.loads(row["log_json"])["end_method"] == "page_leave"

    def test_a11_a12_saving_again_overwrites_and_keeps_one_row(
        self, client, tutor_db
    ) -> None:
        _chat(client, "質問1")
        _save(client)
        _save(client)
        assert len(_log_rows(tutor_db)) == 1
        _chat(client, "質問2")

        response = _save(client, end_method="page_leave")

        assert response.status_code == 200
        (row,) = _log_rows(tutor_db)
        assert row["end_method"] == "page_leave"
        log = json.loads(row["log_json"])
        assert log["end_method"] == "page_leave"
        assert [m["content"] for m in log["messages"] if m["role"] == "user"] == [
            "質問1",
            "質問2",
        ]
        assert len(log["messages"]) == 4

    def test_a7_failed_round_trip_is_not_in_the_log(
        self, client, tutor_db, llm: FakeLlmGateway, monkeypatch
    ) -> None:
        assert _chat(client, "成功する質問").status_code == 200

        def _boom(*_args, **_kwargs):
            raise LlmGatewayError("boom")

        monkeypatch.setattr(llm, "generate_json", _boom)
        failed = _chat(client, "失敗する質問")
        assert failed.status_code != 200

        response = _save(client)

        assert response.status_code == 200
        (row,) = _log_rows(tutor_db)
        contents = [m["content"] for m in json.loads(row["log_json"])["messages"]]
        assert "失敗する質問" not in contents
        assert contents[0] == "成功する質問"
        assert len(contents) == 2


class TestZeroMessages:
    def test_a13_saves_empty_log_and_creates_sessions(
        self, client, tutor_db, learning_db
    ) -> None:
        assert learning_db.execute("SELECT COUNT(*) AS c FROM learning_sessions").fetchone()["c"] == 0
        assert tutor_db.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"] == 0

        response = _save(client)

        assert response.status_code == 200, response.get_data(as_text=True)
        (row,) = _log_rows(tutor_db)
        log = json.loads(row["log_json"])
        assert log["messages"] == []
        learning = learning_db.execute("SELECT id, learner_id, lecture_id FROM learning_sessions").fetchall()
        sessions = tutor_db.execute("SELECT id, learning_session_id FROM sessions").fetchall()
        assert len(learning) == 1 and len(sessions) == 1
        assert row["session_id"] == sessions[0]["id"] == log["tutor_session_id"]
        assert row["learning_session_id"] == learning[0]["id"] == log["learning_session_id"]
        assert sessions[0]["learning_session_id"] == learning[0]["id"]
        assert row["participant_id"] == "1" == log["participant_id"]
        assert row["lecture_id"] == "lecture-1" == log["lecture_id"]

    def test_a13_later_message_is_saved_in_the_same_tutor_session(
        self, client, tutor_db
    ) -> None:
        saved = _save(client).get_json()

        assert _chat(client, "あとからの発言").status_code == 200

        session_ids = {
            r["session_id"] for r in tutor_db.execute("SELECT session_id FROM messages")
        }
        assert session_ids == {saved["tutor_session_id"]}
        assert tutor_db.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"] == 1


class TestRequestErrors:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"json": {"end_method": "end_button"}},
            {"json": {"participant_id": "", "end_method": "end_button"}},
            {"json": {"participant_id": "   ", "end_method": "end_button"}},
            {"json": {"participant_id": "1"}},
            {"json": {"participant_id": "1", "end_method": "leave"}},
            {"json": {"participant_id": "1", "end_method": ""}},
            {"json": ["participant_id", "end_method"]},
            {"json": {}},
            {"data": "not json", "content_type": "application/json"},
            {"data": "participant_id=1&end_method=end_button",
             "content_type": "application/x-www-form-urlencoded"},
        ],
    )
    def test_a17_request_errors_return_400_and_save_nothing(
        self, client, tutor_db, kwargs
    ) -> None:
        _chat(client, "質問")
        good = _save(client)
        assert good.status_code == 200
        before = [dict(r) for r in _log_rows(tutor_db)]
        _chat(client, "追加の質問")

        response = client.post("/api/dialog-log", **kwargs)

        assert response.status_code == 400
        assert [dict(r) for r in _log_rows(tutor_db)] == before

    def test_a17_request_error_creates_no_log_when_none_existed(
        self, client, tutor_db
    ) -> None:
        response = client.post(
            "/api/dialog-log", json={"participant_id": "1", "end_method": "nope"}
        )

        assert response.status_code == 400
        assert _log_rows(tutor_db) == []


class TestSaveFailure:
    def test_a17_db_write_failure_returns_non_2xx_and_keeps_existing_log(
        self, client, tutor_db
    ) -> None:
        _chat(client, "質問1")
        assert _save(client).status_code == 200
        before = [dict(r) for r in _log_rows(tutor_db)]
        _chat(client, "質問2")
        # dialog_logs への書き込みを、DB 側で失敗させる
        tutor_db.executescript(
            """
            CREATE TRIGGER fail_dialog_log_insert BEFORE INSERT ON dialog_logs
            BEGIN SELECT RAISE(ABORT, 'write blocked'); END;
            CREATE TRIGGER fail_dialog_log_update BEFORE UPDATE ON dialog_logs
            BEGIN SELECT RAISE(ABORT, 'write blocked'); END;
            CREATE TRIGGER fail_dialog_log_delete BEFORE DELETE ON dialog_logs
            BEGIN SELECT RAISE(ABORT, 'write blocked'); END;
            """
        )
        tutor_db.commit()

        response = _save(client, end_method="page_leave")

        assert not (200 <= response.status_code < 300)
        assert [dict(r) for r in _log_rows(tutor_db)] == before


class TestExistingBehaviourKept:
    def test_a14_chat_response_and_per_turn_saving_are_unchanged(
        self, client, tutor_db
    ) -> None:
        response = _chat(client, "質問")

        assert response.status_code == 200
        body = response.get_json()
        assert set(body) == {"response", "session_id"}
        assert body["response"] == "スタブ応答"
        rows = tutor_db.execute(
            "SELECT role, content, created_at, responded_at FROM messages ORDER BY id"
        ).fetchall()
        assert [(r["role"], r["content"]) for r in rows] == [
            ("user", "質問"),
            ("assistant", "スタブ応答"),
        ]
        # 並び順に使う created_at は、これまでどおり両方とも受け付けた時刻
        assert rows[0]["created_at"] == rows[1]["created_at"]
        # AI 応答の生成を終えた時刻だけが追加で記録される
        assert rows[0]["responded_at"] is None
        assert TIME_PATTERN.match(rows[1]["responded_at"])
        assert rows[1]["responded_at"] >= rows[1]["created_at"]


class TestLegacyDatabase:
    """A15: 変更前の形の tutor.db(dialog_logs なし、responded_at なし、対話が保存済み)。"""

    _LEGACY_SCHEMA = """
    CREATE TABLE sessions (
        id TEXT PRIMARY KEY,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        participant_id TEXT NOT NULL DEFAULT '',
        learning_session_id TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        utterance_type TEXT,
        dialogue_move TEXT,
        interpretation_state TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );
    """

    def _prepare_legacy(self, tmp_path: Path) -> None:
        from application.learning.dto.start_or_get_learning_session import (
            StartOrGetLearningSessionRequest,
        )
        from application.learning.use_cases.start_or_get_learning_session import (
            StartOrGetLearningSessionUseCase,
        )
        from domain.shared.ids import LearnerId, LectureId
        from framework_drivers.db.learning.id_generators import (
            UuidLearningSessionIdGenerator,
        )
        from framework_drivers.db.learning.sqlite_connection import (
            apply_learning_schema,
            connect_learning_db,
        )
        from framework_drivers.db.learning.sqlite_learning_session_repository import (
            SqliteLearningSessionRepository,
        )

        project_root = Path(__file__).resolve().parent.parent.parent
        learning = connect_learning_db(tmp_path / "learning.db")
        apply_learning_schema(learning, project_root / "db" / "schema_learning.sql")
        result = StartOrGetLearningSessionUseCase(
            repository=SqliteLearningSessionRepository(learning),
            id_generator=UuidLearningSessionIdGenerator(),
        ).execute(
            StartOrGetLearningSessionRequest(
                learner_id=LearnerId("1"),
                lecture_id=LectureId("lecture-1"),
                started_at=datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc),
            )
        )
        assert result.is_ok
        learning_session_id = str(result.value.session_id)
        learning.close()

        legacy = sqlite3.connect(str(tmp_path / "tutor.db"))
        legacy.executescript(self._LEGACY_SCHEMA)
        legacy.execute(
            "INSERT INTO sessions (id, created_at, participant_id, learning_session_id) "
            "VALUES ('ts-old', '2026-06-21T12:00:00+00:00', '', ?)",
            (learning_session_id,),
        )
        legacy.execute(
            "INSERT INTO messages (session_id, role, content, created_at) "
            "VALUES ('ts-old', 'user', '旧の発言', '2026-06-21T12:00:00+00:00')"
        )
        legacy.execute(
            "INSERT INTO messages (session_id, role, content, created_at, "
            "utterance_type, dialogue_move) "
            "VALUES ('ts-old', 'assistant', '旧の応答', '2026-06-21T12:00:00+00:00', "
            "'FACT_REQUEST', 'ELICIT_REASON')"
        )
        legacy.commit()
        legacy.close()

    def test_a15_send_and_save_work_and_old_rows_are_unchanged(
        self, monkeypatch, tmp_path: Path, llm: FakeLlmGateway
    ) -> None:
        self._prepare_legacy(tmp_path)
        peek = sqlite3.connect(str(tmp_path / "tutor.db"))
        peek.row_factory = sqlite3.Row
        old_rows = [
            dict(r)
            for r in peek.execute(
                f"SELECT {_ORIGINAL_MESSAGE_COLUMNS} FROM messages ORDER BY id"
            )
        ]
        peek.close()
        client = _make_client(monkeypatch, tmp_path, llm)

        chat = _chat(client, "新しい発言")
        assert chat.status_code == 200, chat.get_data(as_text=True)
        response = _save(client)

        assert response.status_code == 200, response.get_data(as_text=True)
        conn = sqlite3.connect(str(tmp_path / "tutor.db"))
        conn.row_factory = sqlite3.Row
        try:
            after = [
                dict(r)
                for r in conn.execute(
                    f"SELECT {_ORIGINAL_MESSAGE_COLUMNS} FROM messages ORDER BY id"
                )
            ]
            assert after[: len(old_rows)] == old_rows
            assert len(after) == len(old_rows) + 2
            (row,) = _log_rows(conn)
            assert row["session_id"] == "ts-old"
            messages = json.loads(row["log_json"])["messages"]
        finally:
            conn.close()
        assert [m["content"] for m in messages] == [
            "旧の発言",
            "旧の応答",
            "新しい発言",
            "スタブ応答",
        ]
        # 変更前に保存された AI 応答は null(受け付け時刻で代用しない)
        assert messages[1]["timestamp"] is None
        # 変更後に送った発言の AI 応答には、生成を終えた時刻が入る
        assert TIME_PATTERN.match(messages[3]["timestamp"])
        assert TIME_PATTERN.match(messages[0]["timestamp"])
