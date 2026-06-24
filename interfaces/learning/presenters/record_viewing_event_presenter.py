# 仕様: docs/spec/interfaces-layer.md#Write-応答-ViewModel
"""RecordViewingEvent の成功応答 ViewModel を生成する。"""
from __future__ import annotations

from application.learning.dto.record_viewing_event import RecordViewingEventResponse

from interfaces.learning.view_models.record_responses import (
    RecordViewingEventSuccessViewModel,
)


class RecordViewingEventPresenter:
    """RecordViewingEventResponse を成功 ViewModel へ変換する。"""

    def present(
        self, _response: RecordViewingEventResponse
    ) -> RecordViewingEventSuccessViewModel:
        return RecordViewingEventSuccessViewModel()
