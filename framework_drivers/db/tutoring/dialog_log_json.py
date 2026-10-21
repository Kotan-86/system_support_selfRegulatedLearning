# 仕様: docs/spec/dialog-log-save.md#対話ログの-json1件の対話ログ
"""対話ログの JSON 化(共有IF のキーと値の形)。発言の変換は interfaces と共有する。"""
from __future__ import annotations

from typing import Any

from application.tutoring.dto.save_dialog_log import DialogLog
from interfaces.tutoring.dialog_log_json_format import (
    FORMAT_VERSION,
    format_log_timestamp,
    message_to_json_dict,
)

__all__ = ["FORMAT_VERSION", "dialog_log_to_json_dict"]


def dialog_log_to_json_dict(log: DialogLog) -> dict[str, Any]:
    return {
        "format_version": FORMAT_VERSION,
        "participant_id": log.participant_id,
        "lecture_id": log.lecture_id,
        "learning_session_id": log.learning_session_id,
        "tutor_session_id": log.tutor_session_id,
        "ended_at": format_log_timestamp(log.ended_at),
        "end_method": log.end_method.value,
        "messages": [message_to_json_dict(m) for m in log.messages],
    }
