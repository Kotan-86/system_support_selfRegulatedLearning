# 仕様: docs/spec/research-lad-csv-download.md#csv-の書式共有if4つに共通pbi-1-で定める
# 仕様: docs/spec/research-lad-csv-download.md#数式とみなされる値の扱いpbi-1-で定める決定-q2
"""研究用 CSV の書き出し(UTF-8 + BOM、CRLF、RFC 4180 の囲み、数式の無効化)。"""
from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence

BOM = "﻿"
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def guard_formula(value: str) -> str:
    """数式として実行されうる文字列の先頭に ' を付ける(文字列の列だけに使う)。"""
    return "'" + value if value.startswith(_FORMULA_PREFIXES) else value


def encode_csv(header: Sequence[str], rows: Iterable[Sequence[object]]) -> bytes:
    """見出し + 行を CSV の bytes にする。値は文字列か数値(空は '')。"""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return (BOM + buffer.getvalue()).encode("utf-8")
