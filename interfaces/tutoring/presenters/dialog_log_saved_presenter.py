# 仕様: docs/spec/dialog-log-save.md#保存-API
"""SaveDialogLogResponse -> ViewModel。"""
from __future__ import annotations

from application.tutoring.dto.save_dialog_log import SaveDialogLogResponse

from interfaces.tutoring.view_models.dialog_log_saved import DialogLogSavedViewModel


class DialogLogSavedPresenter:
    """SaveDialogLogResponse を DialogLogSavedViewModel へ変換する。"""

    def present(self, response: SaveDialogLogResponse) -> DialogLogSavedViewModel:
        ended_at = response.ended_at
        if ended_at.microsecond:
            # 共有IFの時刻の形式: 秒まで(秒未満は切り捨て)
            ended_at = ended_at.replace(microsecond=0)
        return DialogLogSavedViewModel(
            tutor_session_id=str(response.tutor_session_id),
            ended_at=ended_at.isoformat(),
            end_method=response.end_method.value,
        )
