# 仕様: docs/spec/participant-login.md#5-idパスワードの登録研究者
"""参加者の資格情報(設定ファイル)の読み込み・書き出し・照合。

設定ファイルは UTF-8 の JSON: ``{"participants": [{"id", "issued_on", "status", "note", "password_hash"}]}``。
"""
from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from werkzeug.security import check_password_hash, generate_password_hash

PARTICIPANT_CREDENTIALS_FILE_ENV: Final = "PARTICIPANT_CREDENTIALS_FILE"
STATUS_ACTIVE: Final = "active"
STATUS_SUSPENDED: Final = "suspended"
ENTRY_KEYS: Final = ("id", "issued_on", "status", "note", "password_hash")
REQUIRED_ENTRY_KEYS: Final = ("id", "status", "password_hash")


@dataclass(frozen=True)
class ParticipantCredential:
    participant_id: str
    issued_on: str
    status: str
    note: str
    password_hash: str


class CredentialsFileError(ValueError):
    """設定ファイルの不備。文言に PARTICIPANT_CREDENTIALS_FILE を含む。"""


def _broken(reason: str) -> CredentialsFileError:
    return CredentialsFileError(
        f"参加者の設定ファイル({PARTICIPANT_CREDENTIALS_FILE_ENV} で指定)が不正です: {reason}"
    )


def _text_field(entry: dict, key: str, *, required: bool) -> str:
    if key not in entry:
        if required:
            raise _broken(f"項目に必須の {key} がありません")
        return ""
    value = entry[key]
    if not isinstance(value, str) or (required and not value):
        raise _broken(f"{key} は文字列である必要があります(必須項目は空不可)")
    return value


def parse_credentials(text: str) -> dict[str, ParticipantCredential]:
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise _broken("JSON として解析できません") from exc
    if not isinstance(data, dict):
        raise _broken("最上位がオブジェクトではありません")
    entries = data.get("participants")
    if not isinstance(entries, list):
        raise _broken("participants が配列ではありません")
    result: dict[str, ParticipantCredential] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise _broken("項目がオブジェクトではありません")
        participant_id = _text_field(entry, "id", required=True)
        status = _text_field(entry, "status", required=True)
        if status not in (STATUS_ACTIVE, STATUS_SUSPENDED):
            raise _broken("status は active か suspended である必要があります")
        if participant_id in result:
            raise _broken("同じ ID が2回現れます")
        result[participant_id] = ParticipantCredential(
            participant_id=participant_id,
            issued_on=_text_field(entry, "issued_on", required=False),
            status=status,
            note=_text_field(entry, "note", required=False),
            password_hash=_text_field(entry, "password_hash", required=True),
        )
    return result


def load_credentials_file(
    path: str | os.PathLike[str] | None,
) -> dict[str, ParticipantCredential]:
    if path is None or str(path) == "":
        raise CredentialsFileError(
            "参加者の設定ファイルの場所が指定されていません。"
            f"環境変数 {PARTICIPANT_CREDENTIALS_FILE_ENV} を設定してください"
        )
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise CredentialsFileError(
            f"参加者の設定ファイルを読めません({PARTICIPANT_CREDENTIALS_FILE_ENV} で指定: {path})"
        ) from exc
    return parse_credentials(text)


def dump_credentials(entries: Iterable[ParticipantCredential]) -> str:
    rows = [
        {
            "id": e.participant_id,
            "issued_on": e.issued_on,
            "status": e.status,
            "note": e.note,
            "password_hash": e.password_hash,
        }
        for e in entries
    ]
    return json.dumps({"participants": rows}, ensure_ascii=False, indent=2) + "\n"


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(credential: ParticipantCredential, password: str) -> bool:
    return check_password_hash(credential.password_hash, password)
