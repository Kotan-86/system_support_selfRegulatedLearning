# 仕様: docs/spec/application-usecase.md#InterfaceModelGateway
"""ITS Interface Model Port（学習者向け発話生成）。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.dialogue_move_decision import DialogueMoveDecision
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from domain.tutoring.message import Message


class InterfaceModelGateway(ABC):
    """選択された Move に従い学習者向け発話を生成する。"""

    @abstractmethod
    def generate(
        self,
        decision: DialogueMoveDecision,
        interpretation: LearnerInterpretationResult,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
    ) -> str:
        """Stage 3: プレーンテキストの応答を返す。"""
