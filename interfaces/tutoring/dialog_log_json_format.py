# 仕様: docs/spec/dialog-log-save.md#対話ログの-json1件の対話ログ
"""発言の JSON 化(保存側と研究用ダウンロードで共有する)。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Final

from domain.tutoring.message import Message, MessageRole
from interfaces.tutoring.tutoring_model_json import serialize_interpretation_state_card

FORMAT_VERSION: Final = 1


def format_log_timestamp(value: datetime) -> str:
    """ISO 8601 文字列へ変換する(秒未満は切り捨て)。"""
    if value.microsecond:
        value = value.replace(microsecond=0)
    return value.isoformat()


def message_to_json_dict(message: Message) -> dict[str, Any]:
    if message.role is MessageRole.USER:
        return {
            "role": message.role.value,
            "content": message.content,
            "timestamp": format_log_timestamp(message.created_at),
        }
    state_json = serialize_interpretation_state_card(message.interpretation_state)
    return {
        "role": message.role.value,
        "content": message.content,
        # 生成終了の時刻。記録なし(変更前の行)は null(受け付け時刻で代用しない)
        "timestamp": (
            format_log_timestamp(message.responded_at)
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
