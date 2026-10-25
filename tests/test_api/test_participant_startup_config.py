# 仕様: docs/spec/participant-login.md#受入基準
# AC20(SECRET_KEY)、AC28(設定ファイル)
"""起動時の設定の検査(30-T1)。`create_app()` の呼び出し形で検証する(main.py の読み込み時にも実行されるため)。"""
from __future__ import annotations

import json

import pytest

from framework_drivers.platform.participant_auth import StartupConfigError
from framework_drivers.platform.participant_credentials import CredentialsFileError
from tests.login_helpers import (
    CREDENTIALS_ENV,
    TEST_PASSWORD,
    build_app,
    make_entry,
    post_login,
    write_credentials_file,
)

GOOD_ENTRY = make_entry("A", "good-password-0123456789")


@pytest.fixture
def good_file(monkeypatch, tmp_path):
    path = write_credentials_file(tmp_path / "creds" / "participants.json", [GOOD_ENTRY])
    monkeypatch.setenv(CREDENTIALS_ENV, str(path))
    return path


def _create(monkeypatch, tmp_path):
    return build_app(monkeypatch, tmp_path)[0]


# ---------------------------------------------------------------- AC20


class TestAc20SecretKey:
    @pytest.mark.parametrize("value", [None, "", "tutor_secret_key"], ids=["unset", "empty", "legacy-default"])
    def test_ac20_missing_empty_or_legacy_secret_key_fails_with_its_name(
        self, monkeypatch, tmp_path, good_file, value
    ) -> None:
        if value is None:
            monkeypatch.delenv("SECRET_KEY", raising=False)
        else:
            monkeypatch.setenv("SECRET_KEY", value)

        with pytest.raises(StartupConfigError) as excinfo:
            _create(monkeypatch, tmp_path)

        assert "SECRET_KEY" in str(excinfo.value)

    def test_ac20_a_set_secret_key_starts_the_app(self, monkeypatch, tmp_path, good_file) -> None:
        monkeypatch.setenv("SECRET_KEY", "another-secret-for-test-0123456789")

        app = _create(monkeypatch, tmp_path)

        assert app is not None
        assert app.config["SECRET_KEY"] == "another-secret-for-test-0123456789"


# ---------------------------------------------------------------- AC28


def _write_text(tmp_path, text: str):
    path = tmp_path / "creds" / "participants.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _without(entry: dict, key: str) -> dict:
    return {k: v for k, v in entry.items() if k != key}


BROKEN_FILES = {
    "not-json": "this is not json {",
    "top-level-not-object": json.dumps([GOOD_ENTRY]),
    "participants-not-array": json.dumps({"participants": {"id": "A"}}),
    "entry-not-object": json.dumps({"participants": ["A"]}),
    "missing-id": json.dumps({"participants": [_without(GOOD_ENTRY, "id")]}),
    "missing-status": json.dumps({"participants": [_without(GOOD_ENTRY, "status")]}),
    "missing-password-hash": json.dumps({"participants": [_without(GOOD_ENTRY, "password_hash")]}),
    "empty-id": json.dumps({"participants": [{**GOOD_ENTRY, "id": ""}]}),
    "unknown-status": json.dumps({"participants": [{**GOOD_ENTRY, "status": "enabled"}]}),
    "duplicate-id": json.dumps({"participants": [GOOD_ENTRY, GOOD_ENTRY]}),
}


class TestAc28CredentialsFile:
    def _assert_fails_naming_the_env(self, monkeypatch, tmp_path) -> None:
        with pytest.raises(CredentialsFileError) as excinfo:
            _create(monkeypatch, tmp_path)
        assert CREDENTIALS_ENV in str(excinfo.value)

    def test_ac28_env_var_unset(self, monkeypatch, tmp_path) -> None:
        monkeypatch.delenv(CREDENTIALS_ENV, raising=False)
        self._assert_fails_naming_the_env(monkeypatch, tmp_path)

    def test_ac28_file_does_not_exist(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv(CREDENTIALS_ENV, str(tmp_path / "creds" / "missing.json"))
        self._assert_fails_naming_the_env(monkeypatch, tmp_path)

    def test_ac28_location_is_a_directory(self, monkeypatch, tmp_path) -> None:
        directory = tmp_path / "creds-dir"
        directory.mkdir()
        monkeypatch.setenv(CREDENTIALS_ENV, str(directory))
        self._assert_fails_naming_the_env(monkeypatch, tmp_path)

    @pytest.mark.parametrize("name", sorted(BROKEN_FILES))
    def test_ac28_broken_content_fails_naming_the_env(self, monkeypatch, tmp_path, name) -> None:
        path = _write_text(tmp_path, BROKEN_FILES[name])
        monkeypatch.setenv(CREDENTIALS_ENV, str(path))
        self._assert_fails_naming_the_env(monkeypatch, tmp_path)

    def test_ac28_well_formed_file_starts_and_allows_login(self, monkeypatch, tmp_path, good_file) -> None:
        client = _create(monkeypatch, tmp_path).test_client()

        assert post_login(client, "A", "good-password-0123456789").status_code == 302

    def test_ac28_zero_entries_starts_and_nobody_can_log_in(self, monkeypatch, tmp_path) -> None:
        path = write_credentials_file(tmp_path / "creds" / "participants.json", [])
        monkeypatch.setenv(CREDENTIALS_ENV, str(path))

        client = _create(monkeypatch, tmp_path).test_client()

        assert post_login(client, "A", TEST_PASSWORD).status_code == 401

    def test_ac28_all_suspended_starts_and_nobody_can_log_in(self, monkeypatch, tmp_path) -> None:
        path = write_credentials_file(
            tmp_path / "creds" / "participants.json",
            [
                make_entry("A", "pw-a-0123456789abcdef", status="suspended"),
                make_entry("B", "pw-b-0123456789abcdef", status="suspended"),
            ],
        )
        monkeypatch.setenv(CREDENTIALS_ENV, str(path))

        client = _create(monkeypatch, tmp_path).test_client()

        assert post_login(client, "A", "pw-a-0123456789abcdef").status_code == 401
        assert post_login(client, "B", "pw-b-0123456789abcdef").status_code == 401

    def test_ac28_optional_fields_may_be_omitted(self, monkeypatch, tmp_path) -> None:
        entry = _without(_without(GOOD_ENTRY, "issued_on"), "note")
        path = write_credentials_file(tmp_path / "creds" / "participants.json", [entry])
        monkeypatch.setenv(CREDENTIALS_ENV, str(path))

        client = _create(monkeypatch, tmp_path).test_client()

        assert post_login(client, "A", "good-password-0123456789").status_code == 302

    def test_ac28_id_format_is_not_checked_by_the_app(self, monkeypatch, tmp_path) -> None:
        path = write_credentials_file(
            tmp_path / "creds" / "participants.json",
            [make_entry("not-P01-format", "pw-x-0123456789abcdef")],
        )
        monkeypatch.setenv(CREDENTIALS_ENV, str(path))

        client = _create(monkeypatch, tmp_path).test_client()

        assert post_login(client, "not-P01-format", "pw-x-0123456789abcdef").status_code == 302
