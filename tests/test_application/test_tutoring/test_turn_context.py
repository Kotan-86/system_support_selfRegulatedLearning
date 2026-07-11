# 仕様: docs/spec/application-usecase.md#RunTutoringPipeline
"""TurnContext DTO の受入基準テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.tutoring.dto.tutoring_pipeline import TurnContext
from domain.learning.learning_snapshot import LearningSnapshot
from domain.shared.ids import LearnerId, LearningSessionId, LectureId, MessageId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.message import Message, MessageRole
from tests.test_application.test_learning.test_get_learning_snapshot import _lecture

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _empty_snapshot() -> LearningSnapshot:
    return LearningSnapshot(
        session_id=LearningSessionId("session-1"),
        learner_id=LearnerId("learner-1"),
        lecture_id=LectureId("lecture-1"),
        viewing_events=(),
        latest_quiz_attempt=None,
        quiz_answers=(),
    )


def _assistant_message(*, dialogue_move: DialogueMove | None = None) -> Message:
    return Message.create(
        id=MessageId("msg-asst"),
        role=MessageRole.ASSISTANT,
        content="応答",
        created_at=FIXED_NOW,
        dialogue_move=dialogue_move,
    )


def _user_message() -> Message:
    return Message.create(
        id=MessageId("msg-user"),
        role=MessageRole.USER,
        content="質問",
        created_at=FIXED_NOW,
    )


class TestTurnContextFromMessages:
    """TurnContext.from_messages の構築。"""

    def test_first_turn_has_zero_turn_index_and_empty_history(self) -> None:
        context = TurnContext.from_messages(
            (), lecture=_lecture(), snapshot=_empty_snapshot()
        )

        assert context.is_first_assistant_turn is True
        assert context.turn_index == 0
        assert context.move_history.records == ()
        assert context.has_lad_data is False
        assert context.lad_check_pending is False

    def test_counts_assistant_turns_and_builds_move_history(self) -> None:
        messages = (
            _user_message(),
            _assistant_message(dialogue_move=DialogueMove.ORIENT_SHARED_REVIEW),
            _user_message(),
            _assistant_message(dialogue_move=DialogueMove.ELICIT_REASON),
        )

        context = TurnContext.from_messages(
            messages, lecture=_lecture(), snapshot=_empty_snapshot()
        )

        assert context.is_first_assistant_turn is False
        assert context.turn_index == 2
        assert len(context.move_history.records) == 2
        assert context.move_history.records[0].dialogue_move is DialogueMove.ORIENT_SHARED_REVIEW
        assert context.move_history.records[1].dialogue_move is DialogueMove.ELICIT_REASON
        assert context.has_lad_data is False
        assert context.lad_check_pending is False


class TestTurnContextLadFlags:
    """LAD 可用性フラグ（has_lad_data / lad_check_pending）。"""

    def test_has_lad_data_true_when_viewing_events_present(self) -> None:
        from domain.learning.viewing_event import ViewingAction, ViewingEvent
        from domain.shared.ids import ViewingEventId

        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=(
                ViewingEvent.create(
                    id=ViewingEventId("event-1"),
                    occurred_at=FIXED_NOW,
                    video_position=0,
                    action=ViewingAction.PLAY,
                    position_delta=0,
                ),
            ),
            latest_quiz_attempt=None,
            quiz_answers=(),
        )

        context = TurnContext.from_messages(
            (), lecture=_lecture(), snapshot=snapshot
        )

        assert context.has_lad_data is True
        assert context.lad_check_pending is True

    def test_lad_check_pending_false_after_data_check_in_session(self) -> None:
        from domain.learning.viewing_event import ViewingAction, ViewingEvent
        from domain.shared.ids import ViewingEventId

        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=(
                ViewingEvent.create(
                    id=ViewingEventId("event-1"),
                    occurred_at=FIXED_NOW,
                    video_position=0,
                    action=ViewingAction.PLAY,
                    position_delta=0,
                ),
            ),
            latest_quiz_attempt=None,
            quiz_answers=(),
        )
        messages = (
            _user_message(),
            _assistant_message(dialogue_move=DialogueMove.DATA_CHECK),
        )

        context = TurnContext.from_messages(
            messages, lecture=_lecture(), snapshot=snapshot
        )

        assert context.has_lad_data is True
        assert context.lad_check_pending is False
