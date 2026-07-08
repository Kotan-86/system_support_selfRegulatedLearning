# 仕様: docs/spec/domain-model.md#Tutoring-VO（InterpretationStateCard）
"""InterpretationStateCard の不変条件テスト。"""
from __future__ import annotations

from domain.tutoring.interpretation_state import (
    InterpretationField,
    InterpretationFieldStatus,
    InterpretationStateCard,
)


class TestInterpretationStateCardEmpty:
    """InterpretationStateCard.empty() の受入基準。"""

    def test_interpretation_state_card_empty(self) -> None:
        card = InterpretationStateCard.empty()

        assert len(card.field_names) == 8
        for field_name in card.field_names:
            field = getattr(card, field_name)
            assert isinstance(field, InterpretationField)
            assert field.status is InterpretationFieldStatus.UNKNOWN
            assert field.note == ""


class TestInterpretationField:
    """InterpretationField の不変条件。"""

    def test_unknown_factory_defaults_to_unknown_status(self) -> None:
        field = InterpretationField.unknown(note="未確認")

        assert field.status is InterpretationFieldStatus.UNKNOWN
        assert field.note == "未確認"

    def test_all_status_values_are_defined(self) -> None:
        assert {s.value for s in InterpretationFieldStatus} == {
            "confirmed",
            "hypothesized",
            "unknown",
        }


class TestInterpretationStateCardFields:
    """8 軸フィールド名が prompts.py と一致する。"""

    def test_state_card_has_eight_named_axes(self) -> None:
        expected = {
            "task_understanding",
            "answer_rationale",
            "felt_dissonance",
            "domain_connection",
            "process_memory",
            "lad_connection",
            "ai_hypotheses",
            "learner_load",
        }
        assert InterpretationStateCard.empty().field_names == expected
