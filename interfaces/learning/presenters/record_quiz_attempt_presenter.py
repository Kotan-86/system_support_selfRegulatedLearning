# 仕様: docs/spec/interfaces-layer.md#Write-応答-ViewModel
"""RecordQuizAttempt の成功応答 ViewModel を生成する。"""
from __future__ import annotations

from application.learning.dto.record_quiz_attempt import RecordQuizAttemptResponse

from interfaces.learning.view_models.record_responses import (
    RecordQuizAttemptSuccessViewModel,
)


class RecordQuizAttemptPresenter:
    """RecordQuizAttemptResponse を成功 ViewModel へ変換する。"""

    def present(
        self, _response: RecordQuizAttemptResponse
    ) -> RecordQuizAttemptSuccessViewModel:
        return RecordQuizAttemptSuccessViewModel()
