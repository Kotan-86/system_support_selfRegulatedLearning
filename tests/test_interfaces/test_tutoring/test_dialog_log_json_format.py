# 仕様: docs/spec/research-dialog-download.md#json-の形
# 仕様: docs/spec/dialog-log-save.md#対話ログの-json1件の対話ログ
"""発言1件の JSON 化(保存と研究用ダウンロードで共有)。形は dialog-log-save.md のとおり。"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from domain.shared.ids import MessageId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from domain.tutoring.message import Message, MessageRole
from interfaces.tutoring.dialog_log_json_format import (
    FORMAT_VERSION,
    format_log_timestamp,
    message_to_json_dict,
)
from interfaces.tutoring.tutoring_model_json import serialize_interpretation_state_card
from tests.test_application.fakes.tutoring.fake_student_model_gateway import (
    sample_updated_state_card,
)

T0 = datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)
T7 = datetime(2026, 9, 29, 1, 0, 7, tzinfo=timezone.utc)
TIME_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$"


def _user(text: str = "質問") -> Message:
    return Message.create(id=MessageId("1"), role=MessageRole.USER, content=text, created_at=T0)


def _assistant(**kwargs) -> Message:
    return Message.create(
        id=MessageId("2"),
        role=MessageRole.ASSISTANT,
        content="応答",
        created_at=T0,
        **kwargs,
    )


def test_format_version_is_one() -> None:
    assert FORMAT_VERSION == 1


class TestFormatLogTimestamp:
    def test_iso_8601_to_the_second_with_offset(self) -> None:
        assert format_log_timestamp(T0) == "2026-09-29T01:00:00+00:00"

    def test_below_second_is_truncated_not_rounded(self) -> None:
        value = datetime(2026, 9, 29, 1, 0, 7, 999999, tzinfo=timezone.utc)

        assert format_log_timestamp(value) == "2026-09-29T01:00:07+00:00"


class TestMessageToJsonDict:
    def test_user_message_has_only_role_content_timestamp(self) -> None:
        body = message_to_json_dict(_user("こんにちは\n改行"))

        assert body == {
            "role": "user",
            "content": "こんにちは\n改行",
            "timestamp": "2026-09-29T01:00:00+00:00",
        }

    def test_assistant_message_has_response_time_and_pipeline_metadata(self) -> None:
        message = _assistant(
            utterance_type=LearnerUtteranceType.FACT_REQUEST,
            dialogue_move=DialogueMove.ELICIT_REASON,
            interpretation_state=sample_updated_state_card(),
            responded_at=T7,
        )

        body = message_to_json_dict(message)

        assert list(body) == [
            "role",
            "content",
            "timestamp",
            "utterance_type",
            "dialogue_move",
            "interpretation_state",
        ]
        assert body["role"] == "assistant"
        assert body["content"] == "応答"
        # AI の応答の時刻は生成を終えた時刻(受け付けた時刻ではない)
        assert body["timestamp"] == "2026-09-29T01:00:07+00:00"
        assert body["utterance_type"] == "FACT_REQUEST"
        assert body["dialogue_move"] == "ELICIT_REASON"
        stored = serialize_interpretation_state_card(sample_updated_state_card())
        assert body["interpretation_state"] == json.loads(stored)
        assert isinstance(body["interpretation_state"], dict)

    def test_assistant_without_response_time_has_null_timestamp(self) -> None:
        body = message_to_json_dict(_assistant())

        assert "timestamp" in body
        assert body["timestamp"] is None

    def test_assistant_without_metadata_has_null_values(self) -> None:
        body = message_to_json_dict(_assistant(responded_at=T7))

        assert body["utterance_type"] is None
        assert body["dialogue_move"] is None
        assert body["interpretation_state"] is None

    def test_timestamps_follow_the_shared_time_format(self) -> None:
        value = datetime(2026, 9, 29, 1, 0, 7, 500000, tzinfo=timezone.utc)

        for message in (_user(), _assistant(responded_at=value)):
            assert re.match(TIME_PATTERN, message_to_json_dict(message)["timestamp"])

    def test_result_is_json_serializable(self) -> None:
        message = _assistant(
            utterance_type=LearnerUtteranceType.FACT_REQUEST,
            interpretation_state=sample_updated_state_card(),
            responded_at=T7,
        )

        body = message_to_json_dict(message)

        assert json.loads(json.dumps(body, ensure_ascii=False)) == body
