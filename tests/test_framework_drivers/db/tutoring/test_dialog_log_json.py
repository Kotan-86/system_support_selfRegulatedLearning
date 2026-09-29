# 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-1 A3, A5, A6, A8)
# 仕様: docs/spec/dialog-log-save.md#対話ログの-json1件の対話ログ
"""対話ログの JSON 化: 共有IF のキーと値の形。"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from application.tutoring.dto.save_dialog_log import DialogLog, EndMethod
from domain.shared.ids import MessageId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from domain.tutoring.message import Message, MessageRole
from framework_drivers.db.tutoring.dialog_log_json import dialog_log_to_json_dict
from interfaces.tutoring.tutoring_model_json import serialize_interpretation_state_card
from tests.test_application.fakes.tutoring.fake_student_model_gateway import (
    sample_updated_state_card,
)

T0 = datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)
T7 = datetime(2026, 9, 29, 1, 0, 7, tzinfo=timezone.utc)
ENDED = datetime(2026, 9, 29, 1, 5, 0, tzinfo=timezone.utc)

TIME_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$"
AXES = {
    "task_understanding",
    "answer_rationale",
    "felt_dissonance",
    "domain_connection",
    "process_memory",
    "lad_connection",
    "ai_hypotheses",
    "learner_load",
}


def _user(text: str = "質問", at: datetime = T0, mid: str = "1") -> Message:
    return Message.create(
        id=MessageId(mid), role=MessageRole.USER, content=text, created_at=at
    )


def _assistant_with_metadata() -> Message:
    return Message.create(
        id=MessageId("2"),
        role=MessageRole.ASSISTANT,
        content="応答",
        created_at=T0,
        utterance_type=LearnerUtteranceType.FACT_REQUEST,
        dialogue_move=DialogueMove.ELICIT_REASON,
        interpretation_state=sample_updated_state_card(),
        responded_at=T7,
    )


def _log(messages: tuple[Message, ...], *, method: EndMethod = EndMethod.END_BUTTON) -> DialogLog:
    return DialogLog(
        participant_id="1",
        lecture_id="lecture-1",
        learning_session_id="ls-1",
        tutor_session_id="ts-1",
        ended_at=ENDED,
        end_method=method,
        messages=messages,
    )


class TestTopLevel:
    def test_a8_top_level_keys_and_values(self) -> None:
        body = dialog_log_to_json_dict(_log((_user(),)))

        assert set(body) == {
            "format_version",
            "participant_id",
            "lecture_id",
            "learning_session_id",
            "tutor_session_id",
            "ended_at",
            "end_method",
            "messages",
        }
        assert body["format_version"] == 1
        assert body["participant_id"] == "1"
        assert body["lecture_id"] == "lecture-1"
        assert body["learning_session_id"] == "ls-1"
        assert body["tutor_session_id"] == "ts-1"
        assert body["ended_at"] == "2026-09-29T01:05:00+00:00"
        assert body["end_method"] == "end_button"

    def test_a8_page_leave_value(self) -> None:
        body = dialog_log_to_json_dict(_log((), method=EndMethod.PAGE_LEAVE))

        assert body["end_method"] == "page_leave"

    def test_a13_empty_messages_is_empty_list(self) -> None:
        body = dialog_log_to_json_dict(_log(()))

        assert body["messages"] == []

    def test_is_json_serializable_and_round_trips(self) -> None:
        body = dialog_log_to_json_dict(_log((_user(), _assistant_with_metadata())))

        assert json.loads(json.dumps(body, ensure_ascii=False)) == body

    def test_ended_at_truncates_below_seconds(self) -> None:
        log = DialogLog(
            participant_id="1",
            lecture_id="lecture-1",
            learning_session_id="ls-1",
            tutor_session_id="ts-1",
            ended_at=datetime(2026, 9, 29, 1, 5, 0, 987654, tzinfo=timezone.utc),
            end_method=EndMethod.END_BUTTON,
            messages=(),
        )

        assert dialog_log_to_json_dict(log)["ended_at"] == "2026-09-29T01:05:00+00:00"


class TestMessages:
    def test_a2_a3_order_role_and_content_preserved(self) -> None:
        messages = (
            _user("質問1", mid="1"),
            Message.create(
                id=MessageId("2"), role=MessageRole.ASSISTANT, content="回答1", created_at=T0
            ),
            _user("質問2", mid="3"),
            Message.create(
                id=MessageId("4"), role=MessageRole.ASSISTANT, content="回答2", created_at=T0
            ),
        )

        body = dialog_log_to_json_dict(_log(messages))

        assert [(m["role"], m["content"]) for m in body["messages"]] == [
            ("user", "質問1"),
            ("assistant", "回答1"),
            ("user", "質問2"),
            ("assistant", "回答2"),
        ]

    def test_a5_a6_user_message_has_only_role_content_timestamp(self) -> None:
        body = dialog_log_to_json_dict(_log((_user(),)))

        (user,) = body["messages"]
        assert set(user) == {"role", "content", "timestamp"}
        assert user["timestamp"] == "2026-09-29T01:00:00+00:00"

    def test_a5_a6_assistant_has_response_time_and_pipeline_metadata(self) -> None:
        body = dialog_log_to_json_dict(_log((_assistant_with_metadata(),)))

        (assistant,) = body["messages"]
        assert set(assistant) == {
            "role",
            "content",
            "timestamp",
            "utterance_type",
            "dialogue_move",
            "interpretation_state",
        }
        # AI の応答の時刻は生成を終えた時刻(受け付けた時刻 created_at ではない)
        assert assistant["timestamp"] == "2026-09-29T01:00:07+00:00"
        assert assistant["utterance_type"] == "FACT_REQUEST"
        assert assistant["dialogue_move"] == "ELICIT_REASON"
        # messages.interpretation_state(JSON 文字列)を解釈したものと等しい
        stored = serialize_interpretation_state_card(sample_updated_state_card())
        assert assistant["interpretation_state"] == json.loads(stored)
        assert set(assistant["interpretation_state"]) == AXES
        for axis in AXES:
            assert set(assistant["interpretation_state"][axis]) == {"status", "note"}

    def test_a5_assistant_without_response_time_has_null_timestamp(self) -> None:
        """変更前に保存された AI 応答: timestamp は null。created_at で代用しない。"""
        legacy = Message.create(
            id=MessageId("2"),
            role=MessageRole.ASSISTANT,
            content="旧の応答",
            created_at=T0,
        )

        body = dialog_log_to_json_dict(_log((legacy,)))

        (assistant,) = body["messages"]
        assert "timestamp" in assistant
        assert assistant["timestamp"] is None

    def test_a6_assistant_without_metadata_has_keys_with_null(self) -> None:
        canned = Message.create(
            id=MessageId("2"),
            role=MessageRole.ASSISTANT,
            content="固定の応答",
            created_at=T0,
            responded_at=T7,
        )

        body = dialog_log_to_json_dict(_log((canned,)))

        (assistant,) = body["messages"]
        assert assistant["utterance_type"] is None
        assert assistant["dialogue_move"] is None
        assert assistant["interpretation_state"] is None
        assert assistant["timestamp"] == "2026-09-29T01:00:07+00:00"

    def test_a5_timestamps_follow_the_shared_time_format(self) -> None:
        import re

        with_micro = Message.create(
            id=MessageId("2"),
            role=MessageRole.ASSISTANT,
            content="x",
            created_at=T0,
            responded_at=datetime(2026, 9, 29, 1, 0, 7, 999999, tzinfo=timezone.utc),
        )

        body = dialog_log_to_json_dict(_log((_user(), with_micro)))

        for message in body["messages"]:
            assert re.match(TIME_PATTERN, message["timestamp"]), message["timestamp"]
        assert body["messages"][1]["timestamp"] == "2026-09-29T01:00:07+00:00"
