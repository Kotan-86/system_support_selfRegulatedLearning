# 仕様: docs/spec/dialog-log-save.md#対話ログの-json1件の対話ログ
"""対話ログの JSON 化(共有IF のキーと値の形)。"""
from __future__ import annotations

import json
from typing import Any

from application.tutoring.dto.save_dialog_log import DialogLog
from domain.tutoring.message import Message, MessageRole
from framework_drivers.db.learning.sqlite_learning_session_mapper import format_datetime
from interfaces.tutoring.tutoring_model_json import serialize_interpretation_state_card

FORMAT_VERSION = 1


def _message_to_dict(message: Message) -> dict[str, Any]:
    if message.role is MessageRole.USER:
        return {
            "role": message.role.value,
            "content": message.content,
            "timestamp": format_datetime(message.created_at),
        }
    state_json = serialize_interpretation_state_card(message.interpretation_state)
    return {
        "role": message.role.value,
        "content": message.content,
        # 生成終了の時刻。記録なし(変更前の行)は null(受け付け時刻で代用しない)
        "timestamp": (
            format_datetime(message.responded_at)
            if message.responded_at is not None
            else None
        ),
        "utterance_type": (
            message.utterance_type.value if message.utterance_type is not None else None
        ),
        "dialogue_move": (
            message.dialogue_move.value if message.dialogue_move is not None else None
        ),
        "interpretation_state": (
            json.loads(state_json) if state_json is not None else None
        ),
    }


def dialog_log_to_json_dict(log: DialogLog) -> dict[str, Any]:
    return {
        "format_version": FORMAT_VERSION,
        "participant_id": log.participant_id,
        "lecture_id": log.lecture_id,
        "learning_session_id": log.learning_session_id,
        "tutor_session_id": log.tutor_session_id,
        "ended_at": format_datetime(log.ended_at),
        "end_method": log.end_method.value,
        "messages": [_message_to_dict(m) for m in log.messages],
    }
