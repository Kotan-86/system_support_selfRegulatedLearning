# 仕様: docs/spec/research-lad-csv-download.md#対象と並び順
"""研究用の小テスト回答取得のユースケース。"""
from __future__ import annotations

from application.common.errors import AppError
from application.common.result import Result, ok
from application.learning.dto.export_quiz_answers import (
    ExportQuizAnswersRequest,
    ExportQuizAnswersResponse,
)
from application.learning.ports.quiz_answer_export_query import QuizAnswerExportQuery


class ExportQuizAnswersUseCase:
    """参加者ID(文字列) → 講義ID(文字列) → attempt_id → question_index(数値)の昇順に並べる。

    時刻では並べない。回答のない受験(question_index が None)の行は1行だけなので順序に影響しない。
    """

    def __init__(self, query: QuizAnswerExportQuery) -> None:
        self._query = query

    def execute(
        self, request: ExportQuizAnswersRequest
    ) -> Result[ExportQuizAnswersResponse, AppError]:
        if request.participant_id is None:
            rows = self._query.list_all()
        else:
            rows = self._query.list_for_participant(request.participant_id)
        ordered = sorted(
            rows,
            key=lambda r: (
                r.participant_id,
                r.lecture_id,
                r.attempt_id,
                -1 if r.question_index is None else r.question_index,
            ),
        )
        return ok(ExportQuizAnswersResponse(rows=tuple(ordered)))
