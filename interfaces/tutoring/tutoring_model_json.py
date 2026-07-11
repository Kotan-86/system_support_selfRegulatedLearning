# 仕様: docs/spec/domain-model.md#Tutoring-VO
# 仕様: docs/spec/application-error-handling.md#SendChatMessage
"""ITS Student / Pedagogical Model の JSON 入出力。"""
from __future__ import annotations

import json
from typing import Any

from application.common.errors import LlmGatewayError
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.dialogue_move_decision import (
    DialogueMoveDecision,
    ResponseBudget,
    ScaffoldingLevel,
)
from domain.tutoring.interpretation_state import (
    InterpretationField,
    InterpretationFieldStatus,
    InterpretationStateCard,
)
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from domain.tutoring.learner_utterance_type import LearnerUtteranceType

_STATE_CARD_JSON_ALIASES: dict[str, str] = {
    "LAD_connection": "lad_connection",
    "AI_hypotheses": "ai_hypotheses",
}


def format_state_card_json(state_card: InterpretationStateCard) -> str:
    """InterpretationStateCard を JSON 文字列に整形する。"""
    payload = {
        field_name: {
            "status": getattr(state_card, field_name).status.value,
            "note": getattr(state_card, field_name).note,
        }
        for field_name in sorted(state_card.field_names)
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _parse_field(raw: Any, *, field_name: str) -> InterpretationField:
    if not isinstance(raw, dict):
        raise LlmGatewayError(
            f"interpretation_state.{field_name} must be an object"
        )
    status_raw = raw.get("status")
    if status_raw is None:
        raise LlmGatewayError(
            f"interpretation_state.{field_name}.status is required"
        )
    try:
        status = InterpretationFieldStatus(str(status_raw))
    except ValueError as exc:
        raise LlmGatewayError(
            f"invalid status for {field_name}: {status_raw!r}"
        ) from exc
    note = str(raw.get("note") or "")
    return InterpretationField(status=status, note=note)


def _normalize_state_card_payload(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise LlmGatewayError("interpretation_state must be an object")
    normalized: dict[str, Any] = {}
    for key, value in raw.items():
        canonical = _STATE_CARD_JSON_ALIASES.get(key, key)
        normalized[canonical] = value
    return normalized


def serialize_interpretation_state_card(
    state_card: InterpretationStateCard | None,
) -> str | None:
    """InterpretationStateCard を DB 永続化用 JSON 文字列へ変換する。"""
    if state_card is None:
        return None
    return format_state_card_json(state_card)


def deserialize_interpretation_state_card(
    raw: str | None,
) -> InterpretationStateCard | None:
    """DB 永続化 JSON から InterpretationStateCard を復元する。"""
    if raw is None or raw == "":
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid interpretation_state JSON: {raw!r}") from exc
    try:
        return parse_interpretation_state_card(payload)
    except LlmGatewayError as exc:
        raise ValueError(str(exc)) from exc


def parse_interpretation_state_card(raw: Any) -> InterpretationStateCard:
    """Student Model JSON から InterpretationStateCard を復元する。"""
    normalized = _normalize_state_card_payload(raw)
    fields: dict[str, InterpretationField] = {}
    for field_name in InterpretationStateCard.empty().field_names:
        if field_name not in normalized:
            fields[field_name] = InterpretationField.unknown()
            continue
        fields[field_name] = _parse_field(
            normalized[field_name],
            field_name=field_name,
        )
    return InterpretationStateCard(**fields)


def parse_student_model_output(data: dict[str, Any]) -> LearnerInterpretationResult:
    """Student Model の JSON 出力を LearnerInterpretationResult に変換する。"""
    utterance_raw = data.get("utterance_type")
    if utterance_raw is None:
        raise LlmGatewayError("utterance_type is required")
    try:
        utterance_type = LearnerUtteranceType(str(utterance_raw))
    except ValueError as exc:
        raise LlmGatewayError(
            f"invalid utterance_type: {utterance_raw!r}"
        ) from exc

    state_card = parse_interpretation_state_card(data.get("interpretation_state"))
    evidence_raw = data.get("evidence_references")
    if evidence_raw is None:
        evidence_raw = []
    if not isinstance(evidence_raw, list):
        raise LlmGatewayError("evidence_references must be a list")
    evidence_references = tuple(str(item) for item in evidence_raw)
    return LearnerInterpretationResult(
        utterance_type=utterance_type,
        state_card=state_card,
        evidence_references=evidence_references,
    )


def _parse_response_budget(budget_raw: Any) -> ResponseBudget:
    """response_budget オブジェクトを ResponseBudget に変換する。"""
    if not isinstance(budget_raw, dict):
        raise LlmGatewayError("response_budget must be an object")
    try:
        max_sentences = int(budget_raw.get("max_sentences", 5))
        max_questions = int(budget_raw.get("max_questions", 1))
    except (TypeError, ValueError) as exc:
        raise LlmGatewayError("response_budget values must be integers") from exc

    scaffolding_raw = budget_raw.get("scaffolding_level", "high")
    try:
        scaffolding_level = ScaffoldingLevel(str(scaffolding_raw))
    except ValueError as exc:
        raise LlmGatewayError(
            f"invalid scaffolding_level: {scaffolding_raw!r}"
        ) from exc

    allow_composite_raw = budget_raw.get("allow_composite_turn", False)
    if not isinstance(allow_composite_raw, bool):
        raise LlmGatewayError("allow_composite_turn must be a boolean")

    composite_pattern_raw = budget_raw.get("composite_pattern")
    composite_pattern = (
        str(composite_pattern_raw) if composite_pattern_raw is not None else None
    )

    return ResponseBudget(
        max_sentences=max_sentences,
        max_questions=max_questions,
        scaffolding_level=scaffolding_level,
        allow_composite_turn=allow_composite_raw,
        composite_pattern=composite_pattern,
    )


def parse_pedagogical_model_output(data: dict[str, Any]) -> DialogueMoveDecision:
    """Pedagogical Model の JSON 出力を DialogueMoveDecision に変換する。"""
    move_raw = data.get("dialogue_move")
    if move_raw is None:
        raise LlmGatewayError("dialogue_move is required")
    try:
        dialogue_move = DialogueMove(str(move_raw))
    except ValueError as exc:
        raise LlmGatewayError(
            f"invalid dialogue_move: {move_raw!r}"
        ) from exc

    response_budget = _parse_response_budget(data.get("response_budget") or {})

    interface_instructions = str(data.get("interface_instructions") or "").strip()
    if not interface_instructions:
        raise LlmGatewayError("interface_instructions must not be empty")

    evidence_raw = data.get("evidence_to_surface")
    if evidence_raw is None:
        evidence_raw = []
    if not isinstance(evidence_raw, list):
        raise LlmGatewayError("evidence_to_surface must be a list")
    evidence_to_surface = tuple(str(item) for item in evidence_raw)

    return DialogueMoveDecision(
        dialogue_move=dialogue_move,
        response_budget=response_budget,
        interface_instructions=interface_instructions,
        evidence_to_surface=evidence_to_surface,
    )
