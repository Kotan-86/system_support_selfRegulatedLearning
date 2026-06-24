# 仕様: docs/spec/domain-model.md#TutorSession（AI 振り返り）
# 仕様: docs/spec/domain-model.md#Message（対話メッセージ）
# 仕様: docs/spec/domain-implementation-plan.md Phase 4
"""Tutoring コンテキストの Entity テスト。"""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest

from domain.shared.ids import LearningSessionId, MessageId, TutorSessionId
from domain.tutoring.message import Message, MessageRole
from domain.tutoring.tutor_session import TutorSession

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _start_tutor_session(
    *,
    session_id: str = "tutor-1",
    learning_session_id: str = "learning-session-1",
) -> TutorSession:
    return TutorSession.start(
        id=TutorSessionId(session_id),
        learning_session_id=LearningSessionId(learning_session_id),
        started_at=FIXED_NOW,
    )


class TestMessage:
    """Message の不変条件を検証する。"""

    def test_one_utterance_per_message(self) -> None:
        """1 Message は role + content の 1 発話モデル。"""
        message = Message.create(
            id=MessageId("msg-1"),
            role=MessageRole.USER,
            content="自分の解釈を言語化したい",
            created_at=FIXED_NOW,
        )
        assert message.role == MessageRole.USER
        assert message.content == "自分の解釈を言語化したい"

    def test_rejects_empty_content(self) -> None:
        """content が空文字のとき拒否される。"""
        with pytest.raises(ValueError):
            Message.create(
                id=MessageId("msg-empty"),
                role=MessageRole.ASSISTANT,
                content="",
                created_at=FIXED_NOW,
            )


class TestTutorSession:
    """TutorSession の不変条件を検証する。"""

    def test_references_learning_via_learning_session_id_only(self) -> None:
        """TutorSession は learningSessionId のみで Learning を参照する。"""
        tutor_session = _start_tutor_session(learning_session_id="ls-42")
        assert tutor_session.learning_session_id == LearningSessionId("ls-42")

    def test_learning_session_id_is_immutable(self) -> None:
        """learningSessionId は作成後に変更できない。"""
        tutor_session = _start_tutor_session()
        with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
            tutor_session.learning_session_id = LearningSessionId("other")  # type: ignore[misc]

    def test_appends_message_via_aggregate_root(self) -> None:
        """Message の追記は TutorSession 集約ルート経由のみ。"""
        tutor_session = _start_tutor_session()
        updated = tutor_session.append_message(
            message_id=MessageId("msg-1"),
            role=MessageRole.USER,
            content="違和感がある",
            created_at=FIXED_NOW,
        )
        assert len(updated.messages) == 1
        assert updated.messages[0].role == MessageRole.USER

    def test_cannot_construct_message_without_aggregate(self) -> None:
        """Message は TutorSession 外から直接公開 factory を持たない（create のみ）。"""
        message = Message.create(
            id=MessageId("msg-direct"),
            role=MessageRole.USER,
            content="直接作成",
            created_at=FIXED_NOW,
        )
        assert message.content == "直接作成"
