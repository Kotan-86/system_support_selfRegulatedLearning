# 仕様: docs/spec/db-persistence.md#受入基準 (AC20)
"""SQLite の WAL-reset の不具合(U8)の修正済みの版かを判定する。

Docker のビルド中に `python deploy/sqlite_version_check.py` で呼ぶ。修正済みでなければ
0 以外で終わり、ビルドが失敗する。

修正済み: 3.51.3 以上(3.52.0 を除く。3.53.0 以降を含む)、3.44 系は 3.44.6 以上、
3.50 系は 3.50.7 以上。それ以外(3.45〜3.49 系を含む)は修正済みに含めない。
標準ライブラリだけで動く(イメージのビルドの早い段階で呼ぶため)。
"""
from __future__ import annotations

import re
import sqlite3
import sys

_WITHDRAWN = (3, 52, 0)


def _parse(version: str) -> tuple[int, int, int] | None:
    if not isinstance(version, str) or not re.fullmatch(r"\d+(\.\d+)*", version.strip()):
        return None
    parts = [int(p) for p in version.strip().split(".")]
    parts += [0] * (3 - len(parts))
    return parts[0], parts[1], parts[2]


def is_fixed_version(version: str) -> bool:
    v = _parse(version)
    if v is None or v == _WITHDRAWN:
        return False
    if v >= (3, 51, 3):
        return True
    if v[:2] == (3, 44):
        return v >= (3, 44, 6)
    if v[:2] == (3, 50):
        return v >= (3, 50, 7)
    return False


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    version = args[0] if args else sqlite3.sqlite_version
    if is_fixed_version(version):
        print(f"SQLite {version}: WAL-reset の不具合の修正済みの版")
        return 0
    print(
        f"SQLite {version}: 修正済みの版ではない"
        "(3.51.3 以上[3.52.0 を除く]、3.44.6 以上の 3.44 系、3.50.7 以上の 3.50 系が必要)",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
