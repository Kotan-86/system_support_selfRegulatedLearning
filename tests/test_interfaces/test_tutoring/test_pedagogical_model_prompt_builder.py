# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
"""PedagogicalModelPromptBuilder の Stage 2 プロンプト注入テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.tutoring.dto.tutoring_pipeline import TurnContext
from domain.learning.learning_snapshot import LearningSnapshot
from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import (
    LearnerId,
    LearningSessionId,
    LectureId,
    MessageId,
    ViewingEventId,
)
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.interpretation_state import InterpretationStateCard
from domain.tutoring.learner_interpretation import LearnerInterpretationResult
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from domain.tutoring.message import Message, MessageRole
from interfaces.tutoring.context_formatters import EMPTY_PLACEHOLDER
from interfaces.tutoring.pedagogical_model_prompt_builder import (
    PedagogicalModelPromptBuilder,
)
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


def _viewing_event(
    *,
    video_position: int,
    action: ViewingAction,
    position_delta: int = 0,
) -> ViewingEvent:
    return ViewingEvent.create(
        id=ViewingEventId("event-1"),
        occurred_at=FIXED_NOW,
        video_position=video_position,
        action=action,
        position_delta=position_delta,
    )


def _assistant_message(*, dialogue_move: DialogueMove) -> Message:
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


def _interpretation(
    *,
    evidence_references: tuple[str, ...] = (),
) -> LearnerInterpretationResult:
    return LearnerInterpretationResult(
        utterance_type=LearnerUtteranceType.VAGUE_MEMORY,
        state_card=InterpretationStateCard.empty(),
        evidence_references=evidence_references,
    )


class TestPedagogicalModelPromptBuilder:
    """Stage 2 プロンプトへの TurnContext / Snapshot 注入。"""

    def test_includes_anti_loop_rule(self) -> None:
        turn_context = TurnContext.from_messages(
            (), lecture=_lecture(), snapshot=_empty_snapshot()
        )
        prompt = PedagogicalModelPromptBuilder().build(
            _interpretation(),
            snapshot=_empty_snapshot(),
            turn_context=turn_context,
        )

        assert "## Anti-Loop Rule" in prompt
        assert "REVOICE_LEARNER_INTERPRETATION" in prompt

    def test_includes_move_history_json(self) -> None:
        messages = (
            _user_message(),
            _assistant_message(dialogue_move=DialogueMove.ORIENT_SHARED_REVIEW),
            _user_message(),
            _assistant_message(
                dialogue_move=DialogueMove.REVOICE_LEARNER_INTERPRETATION
            ),
        )
        turn_context = TurnContext.from_messages(
            messages, lecture=_lecture(), snapshot=_empty_snapshot()
        )
        prompt = PedagogicalModelPromptBuilder().build(
            _interpretation(),
            snapshot=_empty_snapshot(),
            turn_context=turn_context,
        )

        assert "## Recent Coach Move History" in prompt
        assert '"dialogue_move": "ORIENT_SHARED_REVIEW"' in prompt
        assert '"dialogue_move": "REVOICE_LEARNER_INTERPRETATION"' in prompt
        assert '"target_fields"' in prompt

    def test_includes_turn_index(self) -> None:
        messages = (
            _user_message(),
            _assistant_message(dialogue_move=DialogueMove.ELICIT_REASON),
        )
        turn_context = TurnContext.from_messages(
            messages, lecture=_lecture(), snapshot=_empty_snapshot()
        )
        prompt = PedagogicalModelPromptBuilder().build(
            _interpretation(),
            snapshot=_empty_snapshot(),
            turn_context=turn_context,
        )

        assert "* turn_index: 1" in prompt

    def test_json_output_example_includes_scaffolding_fields(self) -> None:
        turn_context = TurnContext.from_messages(
            (), lecture=_lecture(), snapshot=_empty_snapshot()
        )
        prompt = PedagogicalModelPromptBuilder().build(
            _interpretation(),
            snapshot=_empty_snapshot(),
            turn_context=turn_context,
        )

        assert '"scaffolding_level": "high"' in prompt
        assert '"allow_composite_turn": false' in prompt

    def test_includes_lad_digest_section(self) -> None:
        turn_context = TurnContext.from_messages(
            (), lecture=_lecture(), snapshot=_empty_snapshot()
        )
        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=(
                _viewing_event(
                    video_position=90,
                    action=ViewingAction.FORWARD_SKIP,
                    position_delta=30,
                ),
            ),
            latest_quiz_attempt=None,
            quiz_answers=(),
        )
        prompt = PedagogicalModelPromptBuilder().build(
            _interpretation(),
            snapshot=snapshot,
            turn_context=turn_context,
        )

        assert "## LAD データ要約" in prompt
        assert "## 視聴ログ要約" in prompt
        assert "早送り: 1回" in prompt

    def test_lad_digest_empty_when_no_viewing_events(self) -> None:
        turn_context = TurnContext.from_messages(
            (), lecture=_lecture(), snapshot=_empty_snapshot()
        )
        prompt = PedagogicalModelPromptBuilder().build(
            _interpretation(),
            snapshot=_empty_snapshot(),
            turn_context=turn_context,
        )

        assert "## LAD データ要約" in prompt
        assert EMPTY_PLACEHOLDER in prompt

    def test_includes_lad_flags_in_student_model_output_section(self) -> None:
        turn_context = TurnContext.from_messages(
            (), lecture=_lecture(), snapshot=_empty_snapshot()
        )
        prompt = PedagogicalModelPromptBuilder().build(
            _interpretation(),
            snapshot=_empty_snapshot(),
            turn_context=turn_context,
        )

        assert "* has_lad_data: false" in prompt
        assert "* lad_check_pending: false" in prompt

    def test_lad_check_pending_true_when_lad_data_without_data_check(self) -> None:
        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=(
                _viewing_event(
                    video_position=90,
                    action=ViewingAction.FORWARD_SKIP,
                    position_delta=30,
                ),
            ),
            latest_quiz_attempt=None,
            quiz_answers=(),
        )
        turn_context = TurnContext.from_messages(
            (), lecture=_lecture(), snapshot=snapshot
        )
        prompt = PedagogicalModelPromptBuilder().build(
            _interpretation(),
            snapshot=snapshot,
            turn_context=turn_context,
        )

        assert "* has_lad_data: true" in prompt
        assert "* lad_check_pending: true" in prompt

    def test_includes_evidence_references_section(self) -> None:
        turn_context = TurnContext.from_messages(
            (), lecture=_lecture(), snapshot=_empty_snapshot()
        )
        prompt = PedagogicalModelPromptBuilder().build(
            _interpretation(
                evidence_references=(
                    "lad_segment_00:00-02:00",
                    "quiz_q1",
                )
            ),
            snapshot=_empty_snapshot(),
            turn_context=turn_context,
        )

        assert "## Student evidence_references" in prompt
        assert "lad_segment_00:00-02:00, quiz_q1" in prompt
