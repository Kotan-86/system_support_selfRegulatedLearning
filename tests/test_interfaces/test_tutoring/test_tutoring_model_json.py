# 仕様: docs/spec/domain-model.md#Tutoring-VO
"""tutoring_model_json のパース検証。"""
from __future__ import annotations

import pytest

from application.common.errors import LlmGatewayError
from domain.tutoring.dialogue_move_decision import ScaffoldingLevel
from interfaces.tutoring.tutoring_model_json import (
    parse_pedagogical_model_output,
    parse_student_model_output,
)


def _minimal_interpretation_state() -> dict[str, dict[str, str]]:
    return {
        field: {"status": "unknown", "note": ""}
        for field in (
            "task_understanding",
            "answer_rationale",
            "felt_dissonance",
            "domain_connection",
            "process_memory",
            "lad_connection",
            "ai_hypotheses",
            "learner_load",
        )
    }


def test_parse_pedagogical_model_output_accepts_empty_evidence_list() -> None:
    decision = parse_pedagogical_model_output(
        {
            "dialogue_move": "REPAIR_OVERLOAD",
            "response_budget": {"max_sentences": 3, "max_questions": 0},
            "interface_instructions": "負荷を下げて短く返す",
            "evidence_to_surface": [],
        }
    )
    assert decision.evidence_to_surface == ()


def test_parse_pedagogical_model_output_defaults_scaffolding_fields() -> None:
    """省略時は scaffolding_level=high、allow_composite_turn=false。"""
    decision = parse_pedagogical_model_output(
        {
            "dialogue_move": "ELICIT_REASON",
            "response_budget": {"max_sentences": 4, "max_questions": 1},
            "interface_instructions": "理由を聞く",
        }
    )

    budget = decision.response_budget
    assert budget.scaffolding_level is ScaffoldingLevel.HIGH
    assert budget.allow_composite_turn is False
    assert budget.composite_pattern is None


def test_parse_pedagogical_model_output_parses_extended_response_budget() -> None:
    decision = parse_pedagogical_model_output(
        {
            "dialogue_move": "REVOICE_LEARNER_INTERPRETATION",
            "response_budget": {
                "max_sentences": 6,
                "max_questions": 1,
                "scaffolding_level": "medium",
                "allow_composite_turn": True,
                "composite_pattern": "CONFIRM_AND_ADVANCE",
            },
            "interface_instructions": "確認して次へ進む",
        }
    )

    budget = decision.response_budget
    assert budget.max_sentences == 6
    assert budget.max_questions == 1
    assert budget.scaffolding_level is ScaffoldingLevel.MEDIUM
    assert budget.allow_composite_turn is True
    assert budget.composite_pattern == "CONFIRM_AND_ADVANCE"


def test_parse_pedagogical_model_output_rejects_invalid_scaffolding_level() -> None:
    with pytest.raises(LlmGatewayError, match="invalid scaffolding_level"):
        parse_pedagogical_model_output(
            {
                "dialogue_move": "ELICIT_REASON",
                "response_budget": {
                    "max_sentences": 4,
                    "max_questions": 1,
                    "scaffolding_level": "ultra",
                },
                "interface_instructions": "理由を聞く",
            }
        )


def test_parse_student_model_output_accepts_empty_evidence_list() -> None:
    result = parse_student_model_output(
        {
            "utterance_type": "OVERLOAD_OR_RESISTANCE",
            "interpretation_state": _minimal_interpretation_state(),
            "evidence_references": [],
        }
    )
    assert result.evidence_references == ()
