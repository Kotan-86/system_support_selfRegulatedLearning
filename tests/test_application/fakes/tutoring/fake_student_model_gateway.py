# 仕様: docs/spec/application-usecase.md#StudentModelGateway
"""StudentModelGateway の Fake 実装（テスト用）。"""
from __future__ import annotations

from dataclasses import dataclass

from application.tutoring.ports.student_model_gateway import StudentModelGateway
from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.interpretation_state import (
    InterpretationField,
    InterpretationFieldStatus,
    InterpretationStateCard,
)
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from domain.tutoring.message import Message


@dataclass(frozen=True)
class InterpretCall:
    """interpret 呼び出しの記録。"""

    snapshot: LearningSnapshot
    messages: tuple[Message, ...]
    user_message: str
    lecture: Lecture
    previous_state_card: InterpretationStateCard


class FakeStudentModelGateway(StudentModelGateway):
    """固定の LearnerInterpretationResult を返す Fake StudentModelGateway。"""

    def __init__(
        self,
        *,
        utterance_type: LearnerUtteranceType = LearnerUtteranceType.VAGUE_MEMORY,
        state_card: InterpretationStateCard | None = None,
    ) -> None:
        self._utterance_type = utterance_type
        self._state_card = state_card or InterpretationStateCard.empty()
        self.interpret_calls: list[InterpretCall] = []

    def interpret(
        self,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
        previous_state_card: InterpretationStateCard,
    ) -> LearnerInterpretationResult:
        self.interpret_calls.append(
            InterpretCall(
                snapshot=snapshot,
                messages=messages,
                user_message=user_message,
                lecture=lecture,
                previous_state_card=previous_state_card,
            )
        )
        return LearnerInterpretationResult(
            utterance_type=self._utterance_type,
            state_card=self._state_card,
        )

    def set_state_card(self, state_card: InterpretationStateCard) -> None:
        """テスト用: 返却する State Card を変更する。"""
        self._state_card = state_card

    def set_utterance_type(self, utterance_type: LearnerUtteranceType) -> None:
        """テスト用: 返却する発話分類を変更する。"""
        self._utterance_type = utterance_type


def sample_updated_state_card() -> InterpretationStateCard:
    """2 ターン目テスト用: 1 軸が hypothesized の State Card。"""
    return InterpretationStateCard(
        task_understanding=InterpretationField(
            status=InterpretationFieldStatus.HYPOTHESIZED,
            note="小テスト問3を曖昧に記憶",
        ),
        answer_rationale=InterpretationField.unknown(),
        felt_dissonance=InterpretationField.unknown(),
        domain_connection=InterpretationField.unknown(),
        process_memory=InterpretationField.unknown(),
        lad_connection=InterpretationField.unknown(),
        ai_hypotheses=InterpretationField.unknown(),
        learner_load=InterpretationField.unknown(),
    )
