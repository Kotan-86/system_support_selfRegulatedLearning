# 仕様: docs/spec/domain-model.md#LearningSession（Aggregate Root）
# 仕様: docs/spec/domain-implementation-plan.md Phase 2
"""Learning コンテキストの LearningSession 集約ルート。"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Iterable

from domain.learning.quiz_attempt import QuizAnswer, QuizAttempt
from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import (
    LectureId,
    LearnerId,
    LearningSessionId,
    ParticipantProgramId,
    QuizAttemptId,
    ViewingEventId,
)


@dataclass(frozen=True)
class LearningSession:
    """1 学習者 × 1 講義 × 1 試行の学習記録（集約ルート）。"""

    id: LearningSessionId
    learner_id: LearnerId
    lecture_id: LectureId
    started_at: datetime
    participant_program_id: ParticipantProgramId | None = None
    viewing_events: tuple[ViewingEvent, ...] = ()
    quiz_attempts: tuple[QuizAttempt, ...] = ()

    @classmethod
    def start(
        cls,
        *,
        id: LearningSessionId,
        learner_id: LearnerId,
        lecture_id: LectureId,
        started_at: datetime,
        existing_sessions: Iterable[LearningSession] = (),
        participant_program_id: ParticipantProgramId | None = None,
    ) -> LearningSession:
        for existing in existing_sessions:
            if (
                existing.learner_id == learner_id
                and existing.lecture_id == lecture_id
            ):
                raise ValueError(
                    "LearningSession already exists for (learner_id, lecture_id)"
                )

        return cls(
            id=id,
            learner_id=learner_id,
            lecture_id=lecture_id,
            started_at=started_at,
            participant_program_id=participant_program_id,
        )

    def record_viewing_event(
        self,
        *,
        event_id: ViewingEventId,
        occurred_at: datetime,
        video_position: int,
        action: ViewingAction,
        position_delta: float,
    ) -> LearningSession:
        event = ViewingEvent.create(
            id=event_id,
            occurred_at=occurred_at,
            video_position=video_position,
            action=action,
            position_delta=position_delta,
        )
        return replace(self, viewing_events=(*self.viewing_events, event))

    def record_quiz_attempt(
        self,
        *,
        attempt_id: QuizAttemptId,
        attempted_at: datetime,
        score_numerator: int,
        score_denominator: int,
        answers: tuple[QuizAnswer, ...],
    ) -> LearningSession:
        attempt = QuizAttempt.create(
            id=attempt_id,
            attempted_at=attempted_at,
            score_numerator=score_numerator,
            score_denominator=score_denominator,
            answers=answers,
        )
        return replace(self, quiz_attempts=(*self.quiz_attempts, attempt))
