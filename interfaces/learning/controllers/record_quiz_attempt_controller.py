# 仕様: docs/spec/interfaces-layer.md#既存-API-対応表
"""RecordQuizAttempt の Controller。"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from application.common.errors import AppError, ValidationError
from application.common.result import Result
from application.learning.dto.record_quiz_attempt import (
    RecordQuizAttemptRequest,
    RecordQuizAttemptResponse,
)
from application.learning.use_cases.record_quiz_attempt import RecordQuizAttemptUseCase

from interfaces.common.error_presenter import present_error
from interfaces.common.ingress import (
    parse_attempted_at,
    parse_learner_id,
    parse_lecture_id,
    parse_quiz_answers,
    parse_required_int,
)
from interfaces.learning.presenters.record_quiz_attempt_presenter import (
    RecordQuizAttemptPresenter,
)
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.learning.view_models.record_responses import (
    RecordQuizAttemptSuccessViewModel,
)


class RecordQuizAttemptController:
    """GAS 小テスト payload を正規化し、UC 実行後に成功 ViewModel を返す。"""

    def __init__(
        self,
        use_case: RecordQuizAttemptUseCase,
        presenter: RecordQuizAttemptPresenter,
    ) -> None:
        self._use_case = use_case
        self._presenter = presenter

    def execute(
        self,
        payload: Mapping[str, Any],
    ) -> RecordQuizAttemptSuccessViewModel | ErrorViewModel:
        learner_result = parse_learner_id(str(payload.get("participant_id") or ""))
        if learner_result.is_err:
            return present_error(learner_result.error)

        lecture_result = parse_lecture_id(payload.get("lecture_id"))
        if lecture_result.is_err:
            return present_error(lecture_result.error)

        attempted_at_raw = payload.get("timestamp")
        if attempted_at_raw is None:
            attempted_at_raw = payload.get("created_at")
        attempted_result = parse_attempted_at(attempted_at_raw)
        if attempted_result.is_err:
            return present_error(attempted_result.error)

        score_numerator_result = parse_required_int(
            payload.get("score_numerator"),
            field_name="score_numerator",
        )
        if score_numerator_result.is_err:
            return present_error(score_numerator_result.error)

        score_denominator_result = parse_required_int(
            payload.get("score_denominator"),
            field_name="score_denominator",
        )
        if score_denominator_result.is_err:
            return present_error(score_denominator_result.error)

        answers_result = parse_quiz_answers(payload.get("answers"))
        if answers_result.is_err:
            return present_error(answers_result.error)

        request = RecordQuizAttemptRequest(
            learner_id=learner_result.value,
            lecture_id=lecture_result.value,
            attempted_at=attempted_result.value,
            score_numerator=score_numerator_result.value,
            score_denominator=score_denominator_result.value,
            answers=answers_result.value,
        )
        result = self._use_case.execute(request)
        return self._present_or_error(result)

    def _present_or_error(
        self,
        result: Result[RecordQuizAttemptResponse, AppError],
    ) -> RecordQuizAttemptSuccessViewModel | ErrorViewModel:
        if result.is_err:
            return present_error(result.error)

        return self._presenter.present(result.value)
