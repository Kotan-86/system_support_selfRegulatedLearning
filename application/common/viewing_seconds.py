# 仕様: docs/spec/domain-model.md#ViewingEvent（視聴イベント）
"""視聴ログの秒数フィールドを整数秒へ正規化する ingress 用パーサ。"""
from __future__ import annotations

import math
from typing import Any

from application.common.errors import ValidationError
from application.common.result import Result, err, ok


def _truncate_toward_zero(value: float) -> int:
    """有限の実数を 0 方向へ切り捨てて整数秒にする。"""
    return int(value)


def parse_seconds_value(value: Any, *, field_name: str) -> Result[int, ValidationError]:
    """JSON 等の生値を整数秒に正規化する。小数は 0 方向へ切り捨てる。"""
    if isinstance(value, bool):
        return err(ValidationError(f"{field_name} must be a number, not bool"))
    if isinstance(value, int):
        return ok(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return err(ValidationError(f"{field_name} must be a finite number"))
        return ok(_truncate_toward_zero(value))
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return err(ValidationError(f"{field_name} must be a number"))
        try:
            numeric = float(stripped)
        except ValueError:
            return err(ValidationError(f"{field_name} must be a number"))
        if not math.isfinite(numeric):
            return err(ValidationError(f"{field_name} must be a finite number"))
        return ok(_truncate_toward_zero(numeric))
    return err(ValidationError(f"{field_name} must be a number"))


def parse_video_position(value: Any) -> Result[int, ValidationError]:
    """current_time / video_position を整数秒に正規化する。"""
    return parse_seconds_value(value, field_name="current_time")


def parse_position_delta(value: Any) -> Result[int, ValidationError]:
    """duration / position_delta を整数秒に正規化する。"""
    return parse_seconds_value(value, field_name="duration")
