# 仕様: docs/spec/interfaces-layer.md#VideoDurationResolver
"""動画総尺解決 Port。"""
from __future__ import annotations

from typing import Protocol

from application.common.errors import AppError
from application.common.result import Result
from domain.learning.lecture import Lecture


class VideoDurationResolver(Protocol):
    """Lecture から動画総尺（秒）を解決する。"""

    def resolve(self, lecture: Lecture) -> Result[int, AppError]:
        """成功時は duration_sec > 0。失敗時は ValidationError 等。"""
