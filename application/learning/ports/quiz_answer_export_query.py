# 仕様: docs/spec/research-lad-csv-download.md#対象と並び順
"""研究用の小テスト回答の読み出しポート(読み取り専用)。"""
from __future__ import annotations

from abc import ABC, abstractmethod

from application.learning.dto.export_quiz_answers import ResearchQuizAnswerRow


class QuizAnswerExportQuery(ABC):
    """小テストの受験・回答を研究用に読み出す。

    契約:
    - DB に書かない(SELECT のみ。commit しない)。
    - 回答のない受験も1行として返す(回答の列は None)。
    - 学習セッションに対応のない受験は除外する。
    - 並びは問わない(並び替えはユースケースが行う)。
    """

    @abstractmethod
    def list_for_participant(self, participant_id: str) -> tuple[ResearchQuizAnswerRow, ...]:
        """`participant_id` と完全一致する学習セッションの受験の行を返す。"""

    @abstractmethod
    def list_all(self) -> tuple[ResearchQuizAnswerRow, ...]:
        """全学習セッションの受験の行を返す。"""
