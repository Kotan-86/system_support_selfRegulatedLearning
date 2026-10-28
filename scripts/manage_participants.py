# 仕様: docs/spec/participant-login.md#5-idパスワードの登録研究者
"""参加者の ID/パスワードの作成スクリプト(研究者が使う)。

使い方: ``python scripts/manage_participants.py [--file PATH] add [--note TEXT] | bulk-add --count N | reissue <ID> | suspend <ID>``
設定ファイルの場所は ``--file`` > 環境変数 PARTICIPANT_CREDENTIALS_FILE > プロジェクトルートの
``secrets/participants.json`` の順。パスワードは標準出力に1回だけ表示し、ファイルには
ハッシュだけを保存する。失敗の理由は標準エラーに出し、ファイルは変更しない。
``bulk-add`` は N 件を一度に登録し、パスワードは端末に出さず、設定ファイルと同じ
ディレクトリの ``participants-distribution.csv``(配布用。配布後に削除する)に書く。
"""
from __future__ import annotations

import argparse
import os
import re
import secrets
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:  # `python scripts/manage_participants.py` で直接実行するとき用
    sys.path.insert(0, str(_PROJECT_ROOT))

from framework_drivers.platform.participant_credentials import (  # noqa: E402
    PARTICIPANT_CREDENTIALS_FILE_ENV,
    STATUS_ACTIVE,
    STATUS_SUSPENDED,
    CredentialsFileError,
    ParticipantCredential,
    dump_credentials,
    hash_password,
    load_credentials_file,
)

MAX_PARTICIPANTS = 31  # 研究協力者30 + 研究者の確認用1(P01〜P31)
DISTRIBUTION_CSV_NAME = "participants-distribution.csv"
_ID_PATTERN = re.compile(r"^P(\d+)$")
DEFAULT_FILE = _PROJECT_ROOT / "secrets" / "participants.json"


class _CommandError(Exception):
    pass


def _resolve_path(file_arg: str | None) -> Path:
    if file_arg:
        return Path(file_arg)
    env = os.environ.get(PARTICIPANT_CREDENTIALS_FILE_ENV)
    if env:
        return Path(env)
    return DEFAULT_FILE


def _write_atomically(path: Path, text: str) -> None:
    """一時ファイルに書いてから置換する(途中で失敗しても元のファイルを壊さない)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _next_id(entries: dict[str, ParticipantCredential]) -> str:
    numbers = [int(m.group(1)) for pid in entries if (m := _ID_PATTERN.match(pid))]
    return f"P{(max(numbers) if numbers else 0) + 1:02d}"


def _new_password() -> str:
    return secrets.token_urlsafe(16)  # 約22文字


def _add(path: Path, entries: dict, note: str, today: date) -> str:
    if len(entries) >= MAX_PARTICIPANTS:
        raise _CommandError(f"参加者は最大 {MAX_PARTICIPANTS} 名までです(停止中の ID も数えます)")
    participant_id = _next_id(entries)
    password = _new_password()
    entries[participant_id] = ParticipantCredential(
        participant_id=participant_id,
        issued_on=today.isoformat(),
        status=STATUS_ACTIVE,
        note=note,
        password_hash=hash_password(password),
    )
    _write_atomically(path, dump_credentials(entries.values()))
    return f"ID: {participant_id}\nパスワード: {password}\n"


def _write_distribution_csv(csv_path: Path, rows: list[tuple[str, str]]) -> None:
    """配布用 CSV を新規作成する(同名があれば失敗。途中で失敗したら残さない)。"""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(csv_path, "x", encoding="utf-8", newline="") as handle:
            handle.write("id,password\n")
            for participant_id, password in rows:
                handle.write(f"{participant_id},{password}\n")  # パスワードは , と " を含まない
    except FileExistsError:
        raise
    except BaseException:
        csv_path.unlink(missing_ok=True)
        raise


def _bulk_add(path: Path, entries: dict, count: int, today: date) -> str:
    if count < 1:
        raise _CommandError("--count は 1 以上の整数で指定してください")
    if len(entries) + count > MAX_PARTICIPANTS:
        raise _CommandError(
            f"参加者は最大 {MAX_PARTICIPANTS} 名までです(停止中の ID も数えます。"
            f"登録済み {len(entries)} 件に {count} 件は追加できません)"
        )
    csv_path = path.parent / DISTRIBUTION_CSV_NAME
    if csv_path.exists():
        raise _CommandError(
            f"配布用 CSV がすでにあります: {csv_path}(配布が済んでいれば削除してから実行してください)"
        )
    new_entries = dict(entries)
    rows: list[tuple[str, str]] = []
    for _ in range(count):
        participant_id = _next_id(new_entries)
        password = _new_password()
        new_entries[participant_id] = ParticipantCredential(
            participant_id=participant_id,
            issued_on=today.isoformat(),
            status=STATUS_ACTIVE,
            note="",
            password_hash=hash_password(password),
        )
        rows.append((participant_id, password))
    _write_distribution_csv(csv_path, rows)
    try:
        _write_atomically(path, dump_credentials(new_entries.values()))
    except BaseException:
        csv_path.unlink(missing_ok=True)
        raise
    return f"{count} 件を登録しました。配布用 CSV: {csv_path}\n配布が済んだら CSV を削除してください\n"


def _reissue(path: Path, entries: dict, participant_id: str, today: date) -> str:
    current = entries.get(participant_id)
    if current is None:
        raise _CommandError(f"{participant_id} は登録されていません")
    if current.status != STATUS_ACTIVE:
        raise _CommandError(f"{participant_id} は停止中のため再発行できません")
    password = _new_password()
    entries[participant_id] = replace(
        current, issued_on=today.isoformat(), password_hash=hash_password(password)
    )
    _write_atomically(path, dump_credentials(entries.values()))
    return f"ID: {participant_id}\nパスワード: {password}\n"


def _suspend(path: Path, entries: dict, participant_id: str, today: date) -> str:
    current = entries.get(participant_id)
    if current is None:
        raise _CommandError(f"{participant_id} は登録されていません")
    entries[participant_id] = replace(
        current, status=STATUS_SUSPENDED, issued_on=today.isoformat()
    )
    _write_atomically(path, dump_credentials(entries.values()))
    return f"ID: {participant_id} を停止しました\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="参加者の ID/パスワードを作成・再発行・停止する")
    parser.add_argument("--file", help="設定ファイルの場所(省略時は環境変数、なければ secrets/participants.json)")
    sub = parser.add_subparsers(dest="command", required=True)
    add_parser = sub.add_parser("add", help="新しい ID とパスワードを作る")
    add_parser.add_argument("--note", default="", help="メモ(任意)")
    bulk_parser = sub.add_parser("bulk-add", help="N 件の ID とパスワードを一度に作り、配布用 CSV に書く")
    bulk_parser.add_argument("--count", type=int, required=True, help="登録する件数")
    sub.add_parser("reissue", help="パスワードを再発行する").add_argument("participant_id")
    sub.add_parser("suspend", help="ID を停止する(解除の手段はない)").add_argument("participant_id")
    return parser


def main(
    argv: Sequence[str] | None = None, *, today: Callable[[], date] = date.today
) -> int:
    args = _build_parser().parse_args(argv)
    path = _resolve_path(args.file)
    try:
        if path.exists():
            entries = dict(load_credentials_file(path))
        elif args.command in ("add", "bulk-add"):
            entries = {}
        else:
            raise _CommandError(f"設定ファイルがありません: {path}")
        if args.command == "add":
            message = _add(path, entries, args.note, today())
        elif args.command == "bulk-add":
            message = _bulk_add(path, entries, args.count, today())
        elif args.command == "reissue":
            message = _reissue(path, entries, args.participant_id, today())
        else:
            message = _suspend(path, entries, args.participant_id, today())
    except (_CommandError, CredentialsFileError, OSError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
