# 仕様: docs/spec/framework-drivers-persistence.md#mapper-契約what
"""Message パイプラインメタデータの SQLite mapper テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from domain.shared.ids import MessageId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from domain.tutoring.message import Message, MessageRole
from framework_drivers.db.tutoring.sqlite_tutor_session_mapper import (
    message_row_to_message,
    message_to_insert_params,
)
from domain.shared.ids import TutorSessionId
from tests.test_application.fakes.tutoring.fake_student_model_gateway import (
    sample_updated_state_card,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


class TestMessageMapperMetadata:
    """mapper が VO メタデータを JSON 等で永続化する。"""

    def test_message_to_insert_params_serializes_metadata(self) -> None:
        state_card = sample_updated_state_card()
        message = Message.create(
            id=MessageId("42"),
            role=MessageRole.ASSISTANT,
            content="reply",
            created_at=FIXED_NOW,
            utterance_type=LearnerUtteranceType.FACT_REQUEST,
            dialogue_move=DialogueMove.ORIENT_SHARED_REVIEW,
            interpretation_state=state_card,
        )

        params = message_to_insert_params(message, TutorSessionId("tutor-1"))

        assert params[0] == "tutor-1"
        assert params[1] == "assistant"
        assert params[2] == "reply"
        assert params[3] == "2026-06-21T12:00:00+00:00"
        assert params[4] == "FACT_REQUEST"
        assert params[5] == "ORIENT_SHARED_REVIEW"
        assert params[6] is not None
        assert "task_understanding" in params[6]

    def test_message_row_to_message_restores_metadata(self) -> None:
        state_card = sample_updated_state_card()
        source = Message.create(
            id=MessageId("7"),
            role=MessageRole.ASSISTANT,
            content="reply",
            created_at=FIXED_NOW,
            utterance_type=LearnerUtteranceType.VAGUE_MEMORY,
            dialogue_move=DialogueMove.JOINT_EVIDENCE_CHECK,
            interpretation_state=state_card,
        )
        _, _, _, _, utterance_type, dialogue_move, interpretation_state = (
            message_to_insert_params(source, TutorSessionId("tutor-1"))
        )

        restored = message_row_to_message(
            {
                "id": 7,
                "session_id": "tutor-1",
                "role": "assistant",
                "content": "reply",
                "created_at": "2026-06-21T12:00:00+00:00",
                "utterance_type": utterance_type,
                "dialogue_move": dialogue_move,
                "interpretation_state": interpretation_state,
            }
        )

        assert restored.utterance_type is LearnerUtteranceType.VAGUE_MEMORY
        assert restored.dialogue_move is DialogueMove.JOINT_EVIDENCE_CHECK
        assert restored.interpretation_state == state_card

    def test_message_row_to_message_without_metadata_columns(self) -> None:
        message = message_row_to_message(
            {
                "id": 1,
                "session_id": "tutor-1",
                "role": "user",
                "content": "hello",
                "created_at": "2026-06-21T12:00:00+00:00",
            }
        )

        assert message.role is MessageRole.USER
        assert message.utterance_type is None
        assert message.dialogue_move is None
        assert message.interpretation_state is None
