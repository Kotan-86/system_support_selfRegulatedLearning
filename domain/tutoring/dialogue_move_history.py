# 仕様: docs/spec/domain-model.md#Tutoring-VO（DialogueMoveHistory）
"""直近 Coach Move 履歴の Value Object。"""
from __future__ import annotations

from dataclasses import dataclass

from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.message import Message, MessageRole

# Move → State Card 軸の対応（教授プロンプトの使用条件に基づく）
_MOVE_TO_TARGET_FIELDS: dict[DialogueMove, tuple[str, ...]] = {
    DialogueMove.ORIENT_SHARED_REVIEW: ("task_understanding", "process_memory"),
    DialogueMove.OPEN_DISSONANCE: ("felt_dissonance",),
    DialogueMove.ELICIT_REASON: ("answer_rationale",),
    DialogueMove.TASK_STANDARD_CHECK: ("task_understanding",),
    DialogueMove.UNCERTAINTY_DECOMPOSITION: ("learner_load",),
    DialogueMove.REPAIR_OVERLOAD: ("learner_load",),
    DialogueMove.DATA_CHECK: ("lad_connection",),
    DialogueMove.REVOICE_LEARNER_INTERPRETATION: (
        "answer_rationale",
        "felt_dissonance",
    ),
    DialogueMove.HYPOTHESIS_OFFER: ("ai_hypotheses",),
    DialogueMove.WAIT_MINIMAL_RESPONSE: (),
    DialogueMove.TERM_OR_RUBRIC_CHECK: ("task_understanding", "domain_connection"),
    DialogueMove.JOINT_EVIDENCE_CHECK: ("domain_connection", "process_memory"),
}


def target_fields_for_move(move: DialogueMove) -> tuple[str, ...]:
    """Coach Move が主に対象とする State Card 軸名を返す。"""
    return _MOVE_TO_TARGET_FIELDS.get(move, ())


@dataclass(frozen=True)
class DialogueMoveRecord:
    """1 assistant ターンで選択された Coach Move の記録。"""

    turn_index: int
    dialogue_move: DialogueMove
    target_fields: tuple[str, ...]


@dataclass(frozen=True)
class DialogueMoveHistory:
    """直近 N 件の Coach Move 履歴。"""

    records: tuple[DialogueMoveRecord, ...] = ()

    @classmethod
    def from_messages(
        cls, messages: tuple[Message, ...], *, window: int = 3
    ) -> DialogueMoveHistory:
        """assistant Message から dialogue_move を抽出し、直近 window 件を保持する。"""
        records: list[DialogueMoveRecord] = []
        turn_index = 0
        for message in messages:
            if message.role is not MessageRole.ASSISTANT:
                continue
            turn_index += 1
            if message.dialogue_move is None:
                continue
            records.append(
                DialogueMoveRecord(
                    turn_index=turn_index,
                    dialogue_move=message.dialogue_move,
                    target_fields=target_fields_for_move(message.dialogue_move),
                )
            )
        if window > 0 and len(records) > window:
            records = records[-window:]
        return cls(records=tuple(records))

    def has_consecutive(self, move: DialogueMove, *, count: int = 2) -> bool:
        """直近 count 件がすべて同一 Move かどうか。"""
        if count < 1 or len(self.records) < count:
            return False
        recent = self.records[-count:]
        return all(record.dialogue_move is move for record in recent)
