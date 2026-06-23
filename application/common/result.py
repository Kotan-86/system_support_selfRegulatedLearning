# 仕様: docs/spec/application-error-handling.md#共通契約
"""UseCase の成功・失敗を型で表す Result 型。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok(Generic[T]):
    """成功結果。value に Response 等を載せる。"""

    value: T

    @property
    def is_ok(self) -> bool:
        return True

    @property
    def is_err(self) -> bool:
        return False


@dataclass(frozen=True)
class Err(Generic[E]):
    """失敗結果。error に AppError 等を載せる。"""

    error: E

    @property
    def is_ok(self) -> bool:
        return False

    @property
    def is_err(self) -> bool:
        return True


Result = Ok[T] | Err[E]


def ok(value: T) -> Ok[T]:
    """成功 Result を生成する。"""
    return Ok(value)


def err(error: E) -> Err[E]:
    """失敗 Result を生成する。"""
    return Err(error)
