# 仕様: docs/spec/domain-model.md#Value Object（Tutoring）
# 仕様: docs/spec/domain-implementation-plan.md Phase 4
"""Tutoring コンテキストの Value Object テスト。"""
from __future__ import annotations

import pytest

from domain.tutoring.message import MessageRole


class TestMessageRole:
    """MessageRole の不変条件を検証する。"""

    def test_has_user_and_assistant_only(self) -> None:
        """MessageRole は user / assistant の 2 値のみ。"""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert len(MessageRole) == 2

    def test_rejects_invalid_role_string(self) -> None:
        """定義外の role 文字列は拒否される。"""
        with pytest.raises(ValueError):
            MessageRole.from_value("system")
