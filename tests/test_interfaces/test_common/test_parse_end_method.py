# 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-1 A8, A17)
# 仕様: docs/spec/dialog-log-save.md#保存-api (end_method は end_button / page_leave の2値だけ)
"""ingress.parse_end_method: end_method の2値だけを受け付ける。"""
from __future__ import annotations

import pytest

from application.common.errors import ValidationError
from application.tutoring.dto.save_dialog_log import EndMethod
from interfaces.common import ingress


class TestParseEndMethod:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("end_button", EndMethod.END_BUTTON),
            ("page_leave", EndMethod.PAGE_LEAVE),
        ],
    )
    def test_a8_accepts_the_two_values(self, value: str, expected: EndMethod) -> None:
        result = ingress.parse_end_method(value)

        assert result.is_ok
        assert result.value is expected
        assert result.value.value == value

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "",
            " ",
            "leave",
            "END_BUTTON",
            "end-button",
            " end_button",
            "end_button ",
            "manual",
            0,
            1,
            True,
            ["end_button"],
            {"end_method": "end_button"},
        ],
    )
    def test_a17_rejects_everything_else(self, value: object) -> None:
        result = ingress.parse_end_method(value)

        assert result.is_err
        assert isinstance(result.error, ValidationError)
