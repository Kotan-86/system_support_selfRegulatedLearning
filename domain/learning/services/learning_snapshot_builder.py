# 仕様: docs/spec/domain-model.md#Domain Service（Learning）
# 仕様: docs/spec/domain-implementation-plan.md Phase 3
"""LearningSession と Lecture から LearningSnapshot を組み立てる Domain Service。"""
from __future__ import annotations

from domain.learning.lecture import Lecture
from domain.learning.learning_session import LearningSession
from domain.learning.learning_snapshot import LearningSnapshot


class LearningSnapshotBuilder:
    """LearningSession + Lecture から 1 Session スコープの Read Model を生成する。"""

    @staticmethod
    def build(*, session: LearningSession, lecture: Lecture) -> LearningSnapshot:
        if session.lecture_id != lecture.id:
            raise ValueError(
                "session.lecture_id must match lecture.id when building LearningSnapshot"
            )

        latest = _latest_quiz_attempt(session)
        quiz_answers = latest.answers if latest is not None else ()

        return LearningSnapshot(
            session_id=session.id,
            learner_id=session.learner_id,
            lecture_id=session.lecture_id,
            viewing_events=session.viewing_events,
            latest_quiz_attempt=latest,
            quiz_answers=quiz_answers,
        )


def _latest_quiz_attempt(session: LearningSession):
    if not session.quiz_attempts:
        return None
    return max(session.quiz_attempts, key=lambda attempt: attempt.attempted_at)
