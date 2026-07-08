# 仕様: docs/spec/domain-model.md#Message（対話メッセージ）
"""Message のパイプラインメタデータ付帯テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from domain.shared.ids import LearningSessionId, MessageId, TutorSessionId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.interpretation_state import InterpretationFieldStatus
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from domain.tutoring.message import Message, MessageRole
from domain.tutoring.tutor_session import TutorSession
from tests.test_application.fakes.tutoring.fake_student_model_gateway import (
    sample_updated_state_card,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


class TestMessageMetadata:
    """assistant Message に VO 付帯フィールドを保持する。"""

    def test_assistant_message_stores_dialogue_move(self) -> None:
        message = Message.create(
            id=MessageId("msg-1"),
            role=MessageRole.ASSISTANT,
            content="応答",
            created_at=FIXED_NOW,
            utterance_type=LearnerUtteranceType.VAGUE_MEMORY,
            dialogue_move=DialogueMove.JOINT_EVIDENCE_CHECK,
        )

        assert message.utterance_type is LearnerUtteranceType.VAGUE_MEMORY
        assert message.dialogue_move is DialogueMove.JOINT_EVIDENCE_CHECK
        assert message.interpretation_state is None

    def test_assistant_message_stores_interpretation_state(self) -> None:
        state_card = sample_updated_state_card()
        message = Message.create(
            id=MessageId("msg-2"),
            role=MessageRole.ASSISTANT,
            content="応答",
            created_at=FIXED_NOW,
            interpretation_state=state_card,
        )

        assert message.interpretation_state == state_card
        assert (
            message.interpretation_state.task_understanding.status
            is InterpretationFieldStatus.HYPOTHESIZED
        )

    def test_user_message_metadata_is_none(self) -> None:
        session = TutorSession.start(
            id=TutorSessionId("tutor-1"),
            learning_session_id=LearningSessionId("learning-1"),
            started_at=FIXED_NOW,
        )
        updated = session.append_message(
            message_id=MessageId("msg-user"),
            role=MessageRole.USER,
            content="質問です",
            created_at=FIXED_NOW,
        )

        user_message = updated.messages[0]
        assert user_message.utterance_type is None
        assert user_message.dialogue_move is None
        assert user_message.interpretation_state is None

    def test_metadata_defaults_to_none(self) -> None:
        message = Message.create(
            id=MessageId("msg-default"),
            role=MessageRole.ASSISTANT,
            content="応答",
            created_at=FIXED_NOW,
        )

        assert message.utterance_type is None
        assert message.dialogue_move is None
        assert message.interpretation_state is None
