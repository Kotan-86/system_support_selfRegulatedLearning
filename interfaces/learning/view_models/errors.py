# 仕様: docs/spec/interfaces-layer.md#ErrorViewModel
"""クライアント向けエラー ViewModel。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class StatusKind(StrEnum):
    """HTTP ステータス相当の区分。Flask 接続層がこれを実ステータスへ変換する。"""

    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    VALIDATION = "validation"
    GATEWAY = "gateway"


@dataclass(frozen=True)
class ErrorViewModel:
    """AppError をシリアライズ可能なクライアント契約へ変換した型。"""

    error_code: str
    message: str
    status_kind: StatusKind
