# 仕様: docs/spec/interfaces-layer.md#VideoDurationResolver
"""VideoDurationResolver の Fake 実装（テスト用）。"""
from __future__ import annotations

from application.common.errors import AppError
from application.common.result import Result, err, ok
from domain.learning.lecture import Lecture


class FakeVideoDurationResolver:
    """固定秒数または AppError を返す Fake VideoDurationResolver。"""

    def __init__(
        self,
        *,
        duration_sec: int = 600,
        error: AppError | None = None,
    ) -> None:
        if duration_sec <= 0:
            raise ValueError("duration_sec must be > 0")
        self._duration_sec = duration_sec
        self._error = error
        self.resolve_calls: list[Lecture] = []

    def resolve(self, lecture: Lecture) -> Result[int, AppError]:
        self.resolve_calls.append(lecture)
        if self._error is not None:
            return err(self._error)
        return ok(self._duration_sec)

    def set_duration_sec(self, duration_sec: int) -> None:
        """テスト用: 成功時に返す秒数を変更する。"""
        if duration_sec <= 0:
            raise ValueError("duration_sec must be > 0")
        self._duration_sec = duration_sec
        self._error = None

    def set_error(self, error: AppError) -> None:
        """テスト用: 失敗時に返す AppError を設定する。"""
        self._error = error
