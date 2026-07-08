# 仕様: docs/spec/application-usecase.md#StudentModelGateway
"""ITS Student Model Port（学習者状態診断）。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.tutoring.interpretation_state import InterpretationStateCard
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from domain.tutoring.message import Message


class StudentModelGateway(ABC):
    """学習者発話とコンテキストから解釈状態を診断する。"""

    @abstractmethod
    def interpret(
        self,
        snapshot: LearningSnapshot,
        messages: tuple[Message, ...],
        user_message: str,
        lecture: Lecture,
        previous_state_card: InterpretationStateCard,
    ) -> LearnerInterpretationResult:
        """Stage 1: 発話分類と State Card 更新結果を返す。"""
