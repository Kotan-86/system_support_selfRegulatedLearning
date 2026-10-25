# 仕様: docs/spec/participant-login.md#受入基準
"""参加者ログインのテスト補助。

アプリ側(participant_credentials)に依存しないよう、設定ファイルは仕様の形式
(UTF-8 の JSON)で直接書く。ハッシュは werkzeug で作る(照合側は方式を問わない)。
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from werkzeug.security import generate_password_hash

SECRET_KEY_FOR_TESTS = "test-secret-key-not-for-production"
CREDENTIALS_ENV = "PARTICIPANT_CREDENTIALS_FILE"
SECURE_DISABLED_ENV = "SESSION_COOKIE_SECURE_DISABLED"
TEST_PASSWORD = "test-password-0123456789"

# 既存テスト・新規テストが使う参加者 ID(アプリは ID の形式を確かめない)
TEST_PARTICIPANT_IDS = (
    "1", "2", "3", "10", "foo", "truncate-test", "learner-42",
    "A", "B", "P01", "P02", "P03", "P30", "P31",
)


def fast_hash(password: str) -> str:
    """テスト用の軽いハッシュ(pbkdf2、低コスト)。照合は werkzeug の check_password_hash。"""
    return generate_password_hash(password, method="pbkdf2:sha256:1000")


def make_entry(
    participant_id: str,
    password: str = TEST_PASSWORD,
    *,
    status: str = "active",
    note: str = "",
    issued_on: str = "2026-10-26",
) -> dict[str, str]:
    return {
        "id": participant_id,
        "issued_on": issued_on,
        "status": status,
        "note": note,
        "password_hash": fast_hash(password),
    }


def write_credentials_file(path: Path, entries: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"participants": entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


_SHARED_CREDENTIALS_PATH: Path | None = None


def shared_credentials_path() -> Path:
    """全テスト共通の設定ファイル(TEST_PARTICIPANT_IDS を「有効」で含む)。"""
    global _SHARED_CREDENTIALS_PATH
    if _SHARED_CREDENTIALS_PATH is None or not _SHARED_CREDENTIALS_PATH.exists():
        directory = Path(tempfile.mkdtemp(prefix="participants-test-"))
        _SHARED_CREDENTIALS_PATH = write_credentials_file(
            directory / "participants.json",
            [make_entry(pid) for pid in TEST_PARTICIPANT_IDS],
        )
    return _SHARED_CREDENTIALS_PATH


def apply_default_env() -> None:
    """main.py の読み込み時の create_app() が通るよう、環境に既定値を与える。"""
    os.environ[CREDENTIALS_ENV] = str(shared_credentials_path())
    os.environ["SECRET_KEY"] = SECRET_KEY_FOR_TESTS
    os.environ[SECURE_DISABLED_ENV] = "1"


def post_login(client, participant_id: str, password: str = TEST_PASSWORD, *, next_path=None):
    data = {"participant_id": participant_id, "password": password}
    if next_path is not None:
        data["next"] = next_path
    return client.post("/login", data=data)


def login_as(client, participant_id: str, password: str = TEST_PASSWORD, *, next_path=None):
    """ログインを送り、成功(302)を確かめる。クライアントに現在の ID を記録する。"""
    response = post_login(client, participant_id, password, next_path=next_path)
    assert response.status_code == 302, (
        f"login_as({participant_id!r}) が成功しない: {response.status_code}"
    )
    client._login_id = participant_id  # noqa: SLF001 - テスト補助
    return response


def ensure_login(client, participant_id: str) -> None:
    """現在のログイン ID が違うときだけログインし直す(複数の参加者を1つのクライアントで使うテスト用)。"""
    if getattr(client, "_login_id", None) != participant_id:
        login_as(client, participant_id)


def build_app(monkeypatch, tmp_path: Path, *, clock=None, llm=None, propagate=True):
    """DB を tmp_path に、LLM を偽物にして create_app を呼ぶ。戻り値は (app, llm)。"""
    from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway
    from tests.test_interfaces.fakes.fake_video_duration_resolver import (
        FakeVideoDurationResolver,
    )

    llm = llm or FakeLlmGateway(response="スタブ応答")
    monkeypatch.setenv("TUTOR_DB_PATH", str(tmp_path / "tutor.db"))
    monkeypatch.setenv("LEARNING_DB_PATH", str(tmp_path / "learning.db"))
    monkeypatch.setattr("framework_drivers.platform.wiring.build_llm_gateway", lambda: llm)
    monkeypatch.setattr(
        "framework_drivers.platform.wiring.build_video_duration_resolver",
        lambda: FakeVideoDurationResolver(duration_sec=600),
    )
    from framework_drivers.platform.main import create_app

    app = create_app() if clock is None else create_app(clock=clock)
    app.config["TESTING"] = True
    app.config["PROPAGATE_EXCEPTIONS"] = propagate
    return app, llm


def dump_databases(tmp_path: Path) -> dict[str, dict[str, list[tuple]]]:
    """2つの DB の全表の全行(行数と内容の比較用)。"""
    import sqlite3

    result: dict[str, dict[str, list[tuple]]] = {}
    for label, name in (("tutor", "tutor.db"), ("learning", "learning.db")):
        conn = sqlite3.connect(str(tmp_path / name))
        try:
            tables = [
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
            result[label] = {
                t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY 1")]
                for t in tables
            }
        finally:
            conn.close()
    return result


def row_counts(tmp_path: Path) -> dict[str, dict[str, int]]:
    return {
        label: {t: len(rows) for t, rows in tables.items()}
        for label, tables in dump_databases(tmp_path).items()
    }


def displayed_participant_id(html: str) -> str | None:
    """画面の「参加者 ID: <strong>…</strong>」に表示されている ID。"""
    import re

    match = re.search(r"参加者 ID:\s*<strong>([^<]*)</strong>", html)
    return match.group(1).strip() if match else None


def viewing_payload(participant_id=..., current_time: int = 10, action: str = "play") -> dict:
    """POST /api/viewing-log の本文。participant_id=... なら項目を含めない。"""
    body = {
        "time_stamp": "2026-02-23T11:18:42",
        "current_time": current_time,
        "action": action,
        "duration": 0,
    }
    if participant_id is not ...:
        body["participant_id"] = participant_id
    return body


def quiz_payload(participant_id=...) -> dict:
    body = {
        "timestamp": "2026-02-23T12:00:00",
        "score_numerator": 4,
        "score_denominator": 5,
        "answers": [
            {"question_index": 1, "selected_answer": "A", "is_correct": 1},
            {"question_index": 2, "selected_answer": "B", "is_correct": 0},
        ],
    }
    if participant_id is not ...:
        body["participant_id"] = participant_id
    return body


def learners_of(tmp_path: Path, table: str) -> list[str]:
    """viewing_logs / quiz_attempts の各行の学習者 ID(learning_sessions 経由)。"""
    import sqlite3

    conn = sqlite3.connect(str(tmp_path / "learning.db"))
    try:
        return sorted(
            r[0]
            for r in conn.execute(
                f"SELECT s.learner_id FROM {table} t "
                "JOIN learning_sessions s ON s.id = t.learning_session_id"
            )
        )
    finally:
        conn.close()


def location_path(response) -> str:
    from urllib.parse import urlsplit

    return urlsplit(response.headers.get("Location", "")).path


def location_host(response) -> str:
    from urllib.parse import urlsplit

    return urlsplit(response.headers.get("Location", "")).netloc
