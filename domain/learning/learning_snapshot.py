# 仕様: docs/spec/domain-model.md#Read Model: LearningSnapshot
# 仕様: docs/spec/domain-implementation-plan.md Phase 3
"""Learning コンテキストの Read Model（Entity ではない）。"""
from __future__ import annotations

from dataclasses import dataclass

from domain.learning.quiz_attempt import QuizAnswer, QuizAttempt
from domain.learning.viewing_event import ViewingEvent
from domain.shared.ids import LectureId, LearnerId, LearningSessionId


@dataclass(frozen=True)
class LearningSnapshot:
    """
    LAD 表示および Tutoring への Published Language。

    スコープは常に 1 LearningSession のみ。
    """

    session_id: LearningSessionId
    learner_id: LearnerId
    lecture_id: LectureId
    viewing_events: tuple[ViewingEvent, ...]
    latest_quiz_attempt: QuizAttempt | None
    quiz_answers: tuple[QuizAnswer, ...]
    lecture_transcript_excerpts: tuple[str, ...] = ()
