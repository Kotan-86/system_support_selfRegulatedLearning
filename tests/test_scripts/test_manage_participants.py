# 仕様: docs/spec/participant-login.md#受入基準
# AC17(平文を保存しない)、AC18(パスワードの表示)、AC19(上限と再発行の対象)、
# AC26(ID の払い出し)、AC29(停止の指示)
"""ID/パスワードの作成スクリプト `scripts.manage_participants`(30-T4)。

CLI: `[--file PATH] add [--note TEXT] | reissue <ID> | suspend <ID>`。
`main(argv, *, today)` は 0=成功、1=失敗。生成したパスワードは標準出力に1回だけ、失敗の理由は標準エラー。
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest
from werkzeug.security import check_password_hash

from framework_drivers.platform.participant_credentials import ENTRY_KEYS
from scripts.manage_participants import main
from tests.login_helpers import (
    CREDENTIALS_ENV,
    build_app,
    make_entry,
    post_login,
    select_lecture_directly,
    viewing_payload,
    write_credentials_file,
)

TODAY = date(2026, 10, 27)
LATER = date(2026, 11, 3)


class Cli:
    def __init__(self, path: Path, capsys) -> None:
        self.path = path
        self.capsys = capsys

    def run(self, *args: str, today: date = TODAY) -> tuple[int, str, str]:
        self.capsys.readouterr()
        code = main(["--file", str(self.path), *args], today=lambda: today)
        captured = self.capsys.readouterr()
        return code, captured.out, captured.err

    def entries(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8"))["participants"]

    def entry(self, participant_id: str) -> dict:
        (found,) = [e for e in self.entries() if e["id"] == participant_id]
        return found

    def raw(self) -> bytes:
        return self.path.read_bytes()


@pytest.fixture
def cli(tmp_path, capsys) -> Cli:
    return Cli(tmp_path / "creds" / "participants.json", capsys)


def password_in(output: str, password_hash: str) -> str:
    """標準出力の中から、ハッシュで照合できる(= 生成されたパスワードの)語を1つ取り出す。"""
    tokens = {t for t in re.split(r"[\s:=：「」\"'`,、]+", output) if t}
    found = [t for t in tokens if len(t) >= 16 and check_password_hash(password_hash, t)]
    assert len(found) == 1, f"標準出力から生成されたパスワードを特定できない: {output!r}"
    return found[0]


def add(cli: Cli, *extra: str, today: date = TODAY) -> tuple[str, str]:
    code, out, err = cli.run("add", *extra, today=today)
    assert code == 0, err
    entry = cli.entries()[-1]
    return entry["id"], password_in(out, entry["password_hash"])


def seed_active(cli: Cli, count: int) -> None:
    write_credentials_file(
        cli.path,
        [make_entry(f"P{n:02d}", f"pw-{n:02d}-0123456789abcdef") for n in range(1, count + 1)],
    )


# ---------------------------------------------------------------- AC26


class TestAc26IdAllocation:
    def test_ac26_three_adds_on_an_empty_registry_allocate_p01_p02_p03_in_order(self, cli) -> None:
        write_credentials_file(cli.path, [])

        ids = [add(cli)[0] for _ in range(3)]

        assert ids == ["P01", "P02", "P03"]
        assert [e["id"] for e in cli.entries()] == ["P01", "P02", "P03"]

    def test_ac26_add_creates_the_file_when_it_does_not_exist(self, cli) -> None:
        assert not cli.path.exists()

        assert add(cli)[0] == "P01"

        assert cli.path.exists()

    def test_ac26_suspended_numbers_are_not_reused(self, cli) -> None:
        for _ in range(3):
            add(cli)
        assert cli.run("suspend", "P02")[0] == 0
        assert add(cli)[0] == "P04"

        assert cli.run("suspend", "P04")[0] == 0
        assert add(cli)[0] == "P05"  # 最大番号(停止中)の次。P04 を再利用しない
        assert [e["id"] for e in cli.entries()] == ["P01", "P02", "P03", "P04", "P05"]


# ---------------------------------------------------------------- AC18


class TestAc18PasswordDisplay:
    def test_ac18_password_is_printed_once_to_stdout_and_is_16_chars_or_more(self, cli) -> None:
        code, out, err = cli.run("add")

        assert code == 0, err
        entry = cli.entries()[0]
        password = password_in(out, entry["password_hash"])
        assert len(password) >= 16
        assert out.count(password) == 1
        assert password not in err
        assert entry["id"] in out  # 配布のため ID も分かる

    def test_ac18_passwords_differ_every_time(self, cli) -> None:
        passwords = [add(cli)[1] for _ in range(5)]
        code, out, _ = cli.run("reissue", "P01")
        assert code == 0
        passwords.append(password_in(out, cli.entry("P01")["password_hash"]))

        assert len(set(passwords)) == len(passwords)
        assert all(len(p) >= 16 for p in passwords)

    def test_ac18_reissue_prints_the_new_password_once(self, cli) -> None:
        add(cli)

        code, out, err = cli.run("reissue", "P01")

        assert code == 0, err
        password = password_in(out, cli.entry("P01")["password_hash"])
        assert out.count(password) == 1


# ---------------------------------------------------------------- AC17


class TestAc17NoPlaintextStored:
    def test_ac17_file_and_dbs_never_contain_the_password_and_the_hash_verifies(
        self, cli, monkeypatch, tmp_path
    ) -> None:
        pid, password = add(cli, "--note", "テスト用メモ")

        text = cli.path.read_text(encoding="utf-8")
        assert password not in text
        entry = cli.entry(pid)
        assert check_password_hash(entry["password_hash"], password)
        assert not check_password_hash(entry["password_hash"], password + "x")
        assert not check_password_hash(entry["password_hash"], "another-string-0123456789")
        # 2つの DB にも含まれない(アプリでそのパスワードを使ってから、DB のバイト列を調べる)
        monkeypatch.setenv(CREDENTIALS_ENV, str(cli.path))
        app, _ = build_app(monkeypatch, tmp_path)
        client = app.test_client()
        assert post_login(client, pid, password).status_code == 302
        select_lecture_directly(pid, "lecture-1")  # 選択前は 409(講義の選択 AC)なので、選択済みにする
        assert client.post("/api/viewing-log", json=viewing_payload(pid)).status_code == 201
        for db in ("tutor.db", "learning.db"):
            assert password.encode("utf-8") not in (tmp_path / db).read_bytes()

    def test_ac17_entry_keys_are_exactly_the_documented_ones(self, cli) -> None:
        add(cli, "--note", "メモ")

        (entry,) = cli.entries()

        assert set(entry) == set(ENTRY_KEYS)
        assert entry["status"] == "active"
        assert entry["issued_on"] == TODAY.isoformat()
        assert entry["note"] == "メモ"

    def test_ac17_note_defaults_to_empty_string(self, cli) -> None:
        add(cli)

        assert cli.entries()[0]["note"] == ""

    def test_ac17_file_has_no_plaintext_after_reissue(self, cli) -> None:
        _, first = add(cli)
        code, out, _ = cli.run("reissue", "P01", today=LATER)
        assert code == 0
        second = password_in(out, cli.entry("P01")["password_hash"])

        text = cli.path.read_text(encoding="utf-8")
        assert first not in text
        assert second not in text

    def test_ac17_default_file_comes_from_the_environment_variable(
        self, tmp_path, monkeypatch
    ) -> None:
        path = tmp_path / "from-env" / "participants.json"
        monkeypatch.setenv(CREDENTIALS_ENV, str(path))

        code = main(["add"], today=lambda: TODAY)

        assert code == 0
        written = json.loads(path.read_text(encoding="utf-8"))["participants"]
        assert [e["id"] for e in written] == ["P01"]


# ---------------------------------------------------------------- AC19


class TestAc19LimitAndReissueTargets:
    def test_ac19_the_31st_add_succeeds_and_allocates_p31(self, cli) -> None:
        seed_active(cli, 30)

        code, out, err = cli.run("add")

        assert code == 0, err
        assert len(cli.entries()) == 31
        assert cli.entries()[-1]["id"] == "P31"
        assert password_in(out, cli.entry("P31")["password_hash"])

    def test_ac19_the_32nd_add_fails_and_the_file_is_unchanged(self, cli) -> None:
        seed_active(cli, 31)
        before = cli.raw()

        code, out, err = cli.run("add")

        assert code != 0
        assert err.strip() != ""
        assert cli.raw() == before
        assert len(cli.entries()) == 31
        assert "P32" not in [e["id"] for e in cli.entries()]
        assert "P32" not in out

    def test_ac19_suspended_ids_still_count_toward_the_limit(self, cli) -> None:
        seed_active(cli, 31)
        assert cli.run("suspend", "P05")[0] == 0
        before = cli.raw()

        code, out, _ = cli.run("add")

        assert code != 0
        assert cli.raw() == before
        assert len(cli.entries()) == 31
        assert "P32" not in out

    def test_ac19_reissue_of_an_unregistered_id_fails_and_the_file_is_unchanged(self, cli) -> None:
        seed_active(cli, 3)
        before = cli.raw()

        code, _, err = cli.run("reissue", "P09")

        assert code != 0
        assert err.strip() != ""
        assert cli.raw() == before

    def test_ac19_reissue_of_a_suspended_id_fails_and_the_file_is_unchanged(self, cli) -> None:
        seed_active(cli, 3)
        assert cli.run("suspend", "P02")[0] == 0
        before = cli.raw()
        old_hash = cli.entry("P02")["password_hash"]

        code, out, err = cli.run("reissue", "P02")

        assert code != 0
        assert err.strip() != ""
        assert cli.raw() == before
        assert cli.entry("P02")["status"] == "suspended"
        assert cli.entry("P02")["password_hash"] == old_hash
        assert out.strip() == ""  # パスワードを表示しない

    def test_ac19_reissue_changes_only_the_target_entry(self, cli) -> None:
        seed_active(cli, 3)
        before = {e["id"]: e for e in cli.entries()}

        code, out, _ = cli.run("reissue", "P02", today=LATER)

        assert code == 0
        after = {e["id"]: e for e in cli.entries()}
        assert after["P01"] == before["P01"]
        assert after["P03"] == before["P03"]
        assert after["P02"]["password_hash"] != before["P02"]["password_hash"]
        assert after["P02"]["issued_on"] == LATER.isoformat()  # 再発行したら更新日
        assert after["P02"]["status"] == "active"
        new_password = password_in(out, after["P02"]["password_hash"])
        assert not check_password_hash(after["P02"]["password_hash"], "pw-02-0123456789abcdef")
        assert check_password_hash(after["P02"]["password_hash"], new_password)

    @pytest.mark.parametrize("command", [("reissue", "P01"), ("suspend", "P01")])
    def test_ac19_reissue_and_suspend_fail_when_the_file_does_not_exist(self, cli, command) -> None:
        code, _, err = cli.run(*command)

        assert code != 0
        assert err.strip() != ""
        assert not cli.path.exists()


# ---------------------------------------------------------------- AC29


class TestAc29Suspend:
    def _three(self, cli) -> dict[str, str]:
        return dict(add(cli) for _ in range(3))

    def test_ac29_suspend_sets_status_and_date_and_changes_nothing_else(self, cli) -> None:
        self._three(cli)
        before = {e["id"]: e for e in cli.entries()}

        code, _, err = cli.run("suspend", "P02", today=LATER)

        assert code == 0, err
        after = {e["id"]: e for e in cli.entries()}
        assert after["P02"]["status"] == "suspended"
        assert after["P02"]["issued_on"] == LATER.isoformat()
        assert after["P02"]["password_hash"] == before["P02"]["password_hash"]
        assert after["P02"]["note"] == before["P02"]["note"]
        assert after["P01"] == before["P01"]
        assert after["P03"] == before["P03"]

    def test_ac29_the_app_started_with_that_file_rejects_p02_and_accepts_p01_p03(
        self, cli, monkeypatch, tmp_path
    ) -> None:
        passwords = self._three(cli)
        assert cli.run("suspend", "P02")[0] == 0
        monkeypatch.setenv(CREDENTIALS_ENV, str(cli.path))
        app, _ = build_app(monkeypatch, tmp_path)

        assert post_login(app.test_client(), "P02", passwords["P02"]).status_code == 401
        assert post_login(app.test_client(), "P01", passwords["P01"]).status_code == 302
        assert post_login(app.test_client(), "P03", passwords["P03"]).status_code == 302

    def test_ac29_suspending_an_unregistered_id_fails_and_the_file_is_unchanged(self, cli) -> None:
        self._three(cli)
        before = cli.raw()

        code, _, err = cli.run("suspend", "P04")

        assert code != 0
        assert err.strip() != ""
        assert cli.raw() == before

    def test_ac29_reissuing_the_suspended_id_fails_and_it_still_cannot_log_in(
        self, cli, monkeypatch, tmp_path
    ) -> None:
        passwords = self._three(cli)
        assert cli.run("suspend", "P02")[0] == 0
        before = cli.raw()

        code, _, _ = cli.run("reissue", "P02")

        assert code != 0
        assert cli.raw() == before
        monkeypatch.setenv(CREDENTIALS_ENV, str(cli.path))
        app, _ = build_app(monkeypatch, tmp_path)
        assert post_login(app.test_client(), "P02", passwords["P02"]).status_code == 401

    @pytest.mark.parametrize("command", ["activate", "resume", "unsuspend", "enable", "restore"])
    def test_ac29_there_is_no_command_to_reactivate(self, cli, command) -> None:
        self._three(cli)
        assert cli.run("suspend", "P02")[0] == 0
        before = cli.raw()

        try:
            code, _, _ = cli.run(command, "P02")
        except SystemExit as exit_:  # argparse の未知のコマンドは SystemExit(2)
            code = exit_.code

        assert code not in (0, None)
        assert cli.raw() == before
        assert cli.entry("P02")["status"] == "suspended"
