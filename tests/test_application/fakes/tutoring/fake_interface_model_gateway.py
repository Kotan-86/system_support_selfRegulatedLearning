# 仕様: docs/spec/application-usecase.md#InterfaceModelGateway
"""InterfaceModelGateway の Fake 実装（テスト用）。"""
from __future__ import annotations

from dataclasses import dataclass

from application.tutoring.ports.interface_model_gateway import InterfaceModelGateway
from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.dialogue_move_decision import DialogueMoveDecision
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from domain.tutoring.message import Message


@dataclass(frozen=True)
class GenerateCall:
    """generate 呼び出しの記録。"""

    decision: DialogueMoveDecision
    interpretation: LearnerInterpretationResult
    snapshot: LearningSnapshot
    messages: tuple[Message, ...]
    user_message: str
    lecture: Lecture


class FakeInterfaceModelGateway(InterfaceModelGateway):
    """固定の応答テキストを返す Fake InterfaceModelGateway。"""

    def __init__(self, *, response: str = "fake-assistant-response") -> None:
        self._response = response
        self.generate_calls: list[GenerateCall] = []

    def generate(
        self,
        decision: DialogueMoveDecision,
        interpretation: LearnerInterpretationResult,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
    ) -> str:
        self.generate_calls.append(
            GenerateCall(
                decision=decision,
                interpretation=interpretation,
                snapshot=snapshot,
                messages=messages,
                user_message=user_message,
                lecture=lecture,
            )
        )
        return self._response

    def set_response(self, response: str) -> None:
        """テスト用: 返却する応答テキストを変更する。"""
        self._response = response
