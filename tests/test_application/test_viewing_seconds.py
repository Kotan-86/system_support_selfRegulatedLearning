# 仕様: docs/spec/domain-model.md#ViewingEvent（視聴イベント）
"""viewing_seconds パーサのテスト。"""
from __future__ import annotations

import math

import pytest

from application.common.errors import ValidationError
from application.common.result import Err, Ok
from application.common.viewing_seconds import (
    parse_position_delta,
    parse_seconds_value,
    parse_video_position,
)


class TestParseSecondsValue:
    """整数秒への正規化を検証する。"""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (0, 0),
            (120, 120),
            (-5, -5),
            (90.9, 90),
            (10.5, 10),
            (-5.7, -5),
            ("90.5", 90),
            ("-5", -5),
        ],
    )
    def test_truncates_fractional_values_toward_zero(
        self, raw: object, expected: int
    ) -> None:
        result = parse_seconds_value(raw, field_name="seconds")

        assert isinstance(result, Ok)
        assert result.value == expected

    def test_rejects_bool(self) -> None:
        result = parse_seconds_value(True, field_name="seconds")

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)

    def test_rejects_non_numeric_string(self) -> None:
        result = parse_seconds_value("abc", field_name="seconds")

        assert isinstance(result, Err)

    @pytest.mark.parametrize("raw", [math.nan, math.inf, -math.inf])
    def test_rejects_non_finite_float(self, raw: float) -> None:
        result = parse_seconds_value(raw, field_name="seconds")

        assert isinstance(result, Err)


class TestIngressFieldParsers:
    """API フィールド名付きパーサを検証する。"""

    def test_parse_video_position_uses_current_time_field_name(self) -> None:
        result = parse_video_position("not-a-number")

        assert isinstance(result, Err)
        assert "current_time" in result.error.message

    def test_parse_position_delta_uses_duration_field_name(self) -> None:
        result = parse_position_delta("not-a-number")

        assert isinstance(result, Err)
        assert "duration" in result.error.message

    def test_fractional_duration_truncates_to_int(self) -> None:
        result = parse_position_delta(10.5)

        assert isinstance(result, Ok)
        assert result.value == 10
