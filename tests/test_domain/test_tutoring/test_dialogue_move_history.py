# 仕様: docs/spec/domain-model.md#Tutoring-VO（DialogueMoveHistory）
"""DialogueMoveHistory の受入基準テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from domain.shared.ids import MessageId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.dialogue_move_history import (
    DialogueMoveHistory,
    target_fields_for_move,
)
from domain.tutoring.message import Message, MessageRole

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _assistant_message(
    *,
    content: str = "応答",
    dialogue_move: DialogueMove | None = None,
) -> Message:
    return Message.create(
        id=MessageId("msg-asst"),
        role=MessageRole.ASSISTANT,
        content=content,
        created_at=FIXED_NOW,
        dialogue_move=dialogue_move,
    )


def _user_message(*, content: str = "質問") -> Message:
    return Message.create(
        id=MessageId("msg-user"),
        role=MessageRole.USER,
        content=content,
        created_at=FIXED_NOW,
    )


class TestDialogueMoveHistoryFromMessages:
    """from_messages が assistant の dialogue_move を抽出する。"""

    def test_empty_messages_returns_empty_history(self) -> None:
        history = DialogueMoveHistory.from_messages(())

        assert history.records == ()

    def test_skips_assistant_without_dialogue_move(self) -> None:
        messages = (
            _user_message(),
            _assistant_message(),
            _user_message(content="2通目"),
            _assistant_message(dialogue_move=DialogueMove.ELICIT_REASON),
        )

        history = DialogueMoveHistory.from_messages(messages)

        assert len(history.records) == 1
        assert history.records[0].dialogue_move is DialogueMove.ELICIT_REASON
        assert history.records[0].turn_index == 2

    def test_assigns_target_fields_from_mapping(self) -> None:
        history = DialogueMoveHistory.from_messages(
            (_assistant_message(dialogue_move=DialogueMove.OPEN_DISSONANCE),)
        )

        assert history.records[0].target_fields == ("felt_dissonance",)

    def test_window_limits_recent_records(self) -> None:
        messages = (
            _assistant_message(
                content="1",
                dialogue_move=DialogueMove.ORIENT_SHARED_REVIEW,
            ),
            _user_message(),
            _assistant_message(
                content="2",
                dialogue_move=DialogueMove.ELICIT_REASON,
            ),
            _user_message(content="3"),
            _assistant_message(
                content="3",
                dialogue_move=DialogueMove.REVOICE_LEARNER_INTERPRETATION,
            ),
            _user_message(content="4"),
            _assistant_message(
                content="4",
                dialogue_move=DialogueMove.DATA_CHECK,
            ),
        )

        history = DialogueMoveHistory.from_messages(messages, window=2)

        assert len(history.records) == 2
        assert history.records[0].dialogue_move is DialogueMove.REVOICE_LEARNER_INTERPRETATION
        assert history.records[1].dialogue_move is DialogueMove.DATA_CHECK


class TestDialogueMoveHistoryHasConsecutive:
    """has_consecutive が直近同一 Move を検出する。"""

    def test_returns_false_when_insufficient_records(self) -> None:
        history = DialogueMoveHistory.from_messages(
            (_assistant_message(dialogue_move=DialogueMove.ELICIT_REASON),)
        )

        assert history.has_consecutive(DialogueMove.ELICIT_REASON) is False

    def test_returns_true_for_two_consecutive_same_moves(self) -> None:
        messages = (
            _assistant_message(dialogue_move=DialogueMove.REVOICE_LEARNER_INTERPRETATION),
            _user_message(),
            _assistant_message(dialogue_move=DialogueMove.REVOICE_LEARNER_INTERPRETATION),
        )
        history = DialogueMoveHistory.from_messages(messages)

        assert history.has_consecutive(DialogueMove.REVOICE_LEARNER_INTERPRETATION) is True

    def test_returns_false_when_last_moves_differ(self) -> None:
        messages = (
            _assistant_message(dialogue_move=DialogueMove.REVOICE_LEARNER_INTERPRETATION),
            _user_message(),
            _assistant_message(dialogue_move=DialogueMove.ELICIT_REASON),
        )
        history = DialogueMoveHistory.from_messages(messages)

        assert history.has_consecutive(DialogueMove.REVOICE_LEARNER_INTERPRETATION) is False


class TestTargetFieldsForMove:
    """全 Coach Move に target_fields マッピングがある。"""

    def test_every_dialogue_move_has_mapping_entry(self) -> None:
        for move in DialogueMove:
            fields = target_fields_for_move(move)
            assert isinstance(fields, tuple)
