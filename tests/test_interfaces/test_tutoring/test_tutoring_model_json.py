# 仕様: docs/spec/domain-model.md#Tutoring-VO
"""tutoring_model_json のパース検証。"""
from __future__ import annotations

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


def test_parse_student_model_output_accepts_empty_evidence_list() -> None:
    result = parse_student_model_output(
        {
            "utterance_type": "OVERLOAD_OR_RESISTANCE",
            "interpretation_state": _minimal_interpretation_state(),
            "evidence_references": [],
        }
    )
    assert result.evidence_references == ()
