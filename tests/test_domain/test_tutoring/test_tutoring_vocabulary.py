# 仕様: docs/spec/domain-model.md#Tutoring-VO
# 仕様: interfaces/tutoring/prompts.py#Learner-Utterance-Type / Coach-Moves
"""Tutoring 語彙（LearnerUtteranceType / DialogueMove）の受入基準テスト。"""
from __future__ import annotations

from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.learner_utterance_type import LearnerUtteranceType

# interfaces/tutoring/prompts.py の Coach Move 見出しと対応
PROMPT_COACH_MOVES: frozenset[str] = frozenset(
    {
        "ORIENT_SHARED_REVIEW",
        "OPEN_DISSONANCE",
        "ELICIT_REASON",
        "TASK_STANDARD_CHECK",
        "UNCERTAINTY_DECOMPOSITION",
        "REPAIR_OVERLOAD",
        "DATA_CHECK",
        "REVOICE_LEARNER_INTERPRETATION",
        "HYPOTHESIS_OFFER",
        "WAIT_MINIMAL_RESPONSE",
        "TERM_OR_RUBRIC_CHECK",
        "JOINT_EVIDENCE_CHECK",
    }
)

PROMPT_UTTERANCE_TYPES: frozenset[str] = frozenset(
    {
        "FACT_REQUEST",
        "RUBRIC_CONFUSION",
        "VAGUE_MEMORY",
        "LEARNER_INTERPRETATION",
        "OVERLOAD_OR_RESISTANCE",
    }
)


class TestLearnerUtteranceType:
    """LearnerUtteranceType の 5 種類。"""

    def test_utterance_type_has_five_values(self) -> None:
        assert len(LearnerUtteranceType) == 5
        assert {member.value for member in LearnerUtteranceType} == PROMPT_UTTERANCE_TYPES


class TestDialogueMove:
    """DialogueMove の Coach Move 列挙。"""

    def test_dialogue_move_enum_covers_prompts(self) -> None:
        enum_values = {member.value for member in DialogueMove}
        assert enum_values == PROMPT_COACH_MOVES
        assert len(DialogueMove) == len(PROMPT_COACH_MOVES)
