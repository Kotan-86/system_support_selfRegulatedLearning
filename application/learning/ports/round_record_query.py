# 仕様: docs/spec/multi-video-learning.md#制約関連機能(2つの DB にまたがる判定)
"""回の終了・対話セッションの有無を、学習セッションごとに読む Port(tutor.db 側)。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection

from domain.shared.ids import LearningSessionId


class RoundRecordQuery(ABC):
    @abstractmethod
    def ended_learning_session_ids(
        self, ids: Collection[LearningSessionId]
    ) -> frozenset[LearningSessionId]:
        """ids のうち、対話ログが終了ボタン(end_button)で保存された(= 回を終えた)もの。"""

    @abstractmethod
    def learning_session_ids_with_tutor_session(
        self, ids: Collection[LearningSessionId]
    ) -> frozenset[LearningSessionId]:
        """ids のうち、対話セッション(発言0件を含む)が1つ以上あるもの。"""
