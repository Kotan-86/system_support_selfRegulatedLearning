# 仕様: docs/spec/domain-model.md#LearningSession（Aggregate Root）
# 仕様: docs/spec/domain-implementation-plan.md Phase 2
"""
LearningSession 集約ルートの不変条件テスト。

子 Entity（ViewingEvent, QuizAttempt）は集約ルート経由でのみ追加する。
"""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest

from domain.learning.learning_session import LearningSession
from domain.learning.quiz_attempt import QuizAnswer, QuizAttempt
from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import (
    LectureId,
    LearnerId,
    LearningSessionId,
    QuizAttemptId,
    ViewingEventId,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _start_session(
    *,
    session_id: str = "session-1",
    learner_id: str = "learner-1",
    lecture_id: str = "lecture-1",
    existing_sessions: tuple[LearningSession, ...] = (),
) -> LearningSession:
    return LearningSession.start(
        id=LearningSessionId(session_id),
        learner_id=LearnerId(learner_id),
        lecture_id=LectureId(lecture_id),
        started_at=FIXED_NOW,
        existing_sessions=existing_sessions,
    )


class TestLearningSessionIdentity:
    """LearningSession の識別子不変条件を検証する。"""

    def test_learner_id_and_lecture_id_are_immutable(self) -> None:
        """learnerId と lectureId は作成後に変更できない。"""
        session = _start_session()
        with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
            session.learner_id = LearnerId("other-learner")  # type: ignore[misc]

    def test_rejects_duplicate_learner_lecture_pair(self) -> None:
        """同一 (learnerId, lectureId) の 2 件目 LearningSession は拒否される。"""
        existing = _start_session()
        with pytest.raises(ValueError):
            _start_session(existing_sessions=(existing,))

    def test_allows_same_learner_different_lecture(self) -> None:
        """同一 learnerId でも lectureId が異なれば別 Session を生成できる。"""
        existing = _start_session(lecture_id="lecture-1")
        other = _start_session(
            session_id="session-2",
            lecture_id="lecture-2",
            existing_sessions=(existing,),
        )
        assert other.lecture_id == LectureId("lecture-2")

    def test_allows_same_lecture_different_learner(self) -> None:
        """同一 lectureId でも learnerId が異なれば別 Session を生成できる。"""
        existing = _start_session(learner_id="learner-1")
        other = _start_session(
            session_id="session-2",
            learner_id="learner-2",
            existing_sessions=(existing,),
        )
        assert other.learner_id == LearnerId("learner-2")


class TestLearningSessionChildEntities:
    """子 Entity の追加は集約ルート経由に限定される。"""

    def test_record_viewing_event_through_aggregate_root(self) -> None:
        """ViewingEvent は LearningSession.record_viewing_event 経由で追加できる。"""
        session = _start_session()
        updated = session.record_viewing_event(
            event_id=ViewingEventId("event-1"),
            occurred_at=FIXED_NOW,
            video_position=30,
            action=ViewingAction.PLAY,
            position_delta=0,
        )
        assert len(updated.viewing_events) == 1
        assert updated.viewing_events[0].action == ViewingAction.PLAY

    def test_record_quiz_attempt_through_aggregate_root(self) -> None:
        """QuizAttempt は LearningSession.record_quiz_attempt 経由で追加できる。"""
        session = _start_session()
        updated = session.record_quiz_attempt(
            attempt_id=QuizAttemptId("attempt-1"),
            attempted_at=FIXED_NOW,
            score_numerator=1,
            score_denominator=1,
            answers=(
                QuizAnswer(
                    question_index=1,
                    selected_answer="A",
                    is_correct=True,
                ),
            ),
        )
        assert len(updated.quiz_attempts) == 1
        assert updated.quiz_attempts[0].score_numerator == 1

    def test_viewing_event_not_publicly_constructible(self) -> None:
        """ViewingEvent の直接コンストラクタは公開 API ではない。"""
        with pytest.raises(TypeError):
            ViewingEvent(  # type: ignore[call-arg]
                id=ViewingEventId("event-1"),
                occurred_at=FIXED_NOW,
                video_position=0,
                action=ViewingAction.PLAY,
                position_delta=0,
            )

    def test_quiz_attempt_not_publicly_constructible(self) -> None:
        """QuizAttempt の直接コンストラクタは公開 API ではない。"""
        with pytest.raises(TypeError):
            QuizAttempt(  # type: ignore[call-arg]
                id=QuizAttemptId("attempt-1"),
                attempted_at=FIXED_NOW,
                score_numerator=1,
                score_denominator=1,
                answers=(),
            )

    def test_record_viewing_event_enforces_invariants(self) -> None:
        """集約ルート経由でも ViewingEvent の不変条件が enforce される。"""
        session = _start_session()
        with pytest.raises(ValueError):
            session.record_viewing_event(
                event_id=ViewingEventId("event-bad"),
                occurred_at=FIXED_NOW,
                video_position=10,
                action=ViewingAction.PLAY,
                position_delta=-1,
            )
