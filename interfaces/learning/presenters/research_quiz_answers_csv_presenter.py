# 仕様: docs/spec/research-lad-csv-download.md#小テストの-csv-の列この順pbi-2決定-q1
# 仕様: docs/spec/research-lad-csv-download.md#何本目の列round_number共有if2つの-csv-に共通pbi-c決定-multi-video-learningmd-の-q7q-c1q-c42026-11-14
"""研究用の小テスト回答 CSV の Presenter。行の順はユースケースの結果のまま。"""
from __future__ import annotations

from application.learning.dto.export_quiz_answers import ExportQuizAnswersResponse
from interfaces.common.csv_encoding import encode_csv, guard_formula
from interfaces.learning.presenters.research_viewing_logs_csv_presenter import csv_filename
from interfaces.learning.view_models.research_csv import ResearchCsvViewModel

HEADER = (
    "participant_id",
    "round_number",
    "lecture_id",
    "learning_session_id",
    "attempt_id",
    "attempted_at",
    "score_numerator",
    "score_denominator",
    "question_index",
    "selected_answer",
    "is_correct",
)


def _blank(value: object) -> object:
    return "" if value is None else value


class ResearchQuizAnswersCsvPresenter:
    def present(
        self, response: ExportQuizAnswersResponse, participant_id: str | None
    ) -> ResearchCsvViewModel:
        rows = [
            (
                guard_formula(r.participant_id),
                r.round_number,
                guard_formula(r.lecture_id),
                guard_formula(r.learning_session_id),
                r.attempt_id,
                guard_formula(r.attempted_at),
                r.score_numerator,
                r.score_denominator,
                _blank(r.question_index),
                "" if r.selected_answer is None else guard_formula(r.selected_answer),
                _blank(r.is_correct),
            )
            for r in response.rows
        ]
        return ResearchCsvViewModel(
            filename=csv_filename("quiz-answers", participant_id),
            content=encode_csv(HEADER, rows),
        )
