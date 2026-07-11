# 仕様: docs/spec/domain-model.md#Value Object（Tutoring）
# 仕様: docs/spec/domain-implementation-plan.md Phase 4
"""Tutoring コンテキストの Value Object テスト。"""
from __future__ import annotations

import pytest

from domain.tutoring.dialogue_move_decision import ResponseBudget, ScaffoldingLevel
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


class TestResponseBudget:
    """ResponseBudget のデフォルトと不変条件。"""

    def test_defaults_scaffolding_and_composite_fields(self) -> None:
        budget = ResponseBudget(max_sentences=4, max_questions=1)

        assert budget.scaffolding_level is ScaffoldingLevel.HIGH
        assert budget.allow_composite_turn is False
        assert budget.composite_pattern is None

    def test_rejects_non_positive_max_sentences(self) -> None:
        with pytest.raises(ValueError, match="max_sentences"):
            ResponseBudget(max_sentences=0, max_questions=1)

    def test_allows_zero_max_questions(self) -> None:
        budget = ResponseBudget(max_sentences=3, max_questions=0)

        assert budget.max_questions == 0
