# 仕様: docs/spec/research-lad-csv-download.md#小テストの-csv-の列この順pbi-2決定-q1
"""研究用の小テスト CSV ダウンロードの DTO(生ログ。回答1つ = 1行)。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchQuizAnswerRow:
    """受験の1問の回答。回答のない受験は question_index 等が None の1行。"""

    participant_id: str
    lecture_id: str
    learning_session_id: str
    attempt_id: int
    attempted_at: str
    score_numerator: int
    score_denominator: int
    question_index: int | None
    selected_answer: str | None
    is_correct: int | None


@dataclass(frozen=True)
class ExportQuizAnswersRequest:
    """`participant_id` が None なら全参加者。文字列は検証も変換もせず完全一致で照合する。"""

    participant_id: str | None


@dataclass(frozen=True)
class ExportQuizAnswersResponse:
    rows: tuple[ResearchQuizAnswerRow, ...]
