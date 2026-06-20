# 仕様: docs/spec/domain-model.md#Read Model: LearningSnapshot
# 仕様: docs/spec/domain-implementation-plan.md Phase 3
"""
LearningSnapshot Read Model と LearningSnapshotBuilder のテスト。

1 LearningSession スコープの Published Language を組み立てる。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from domain.learning.lecture import Lecture
from domain.learning.learning_session import LearningSession
from domain.learning.learning_snapshot import LearningSnapshot
from domain.learning.quiz_attempt import QuizAnswer
from domain.learning.services.learning_snapshot_builder import LearningSnapshotBuilder
from domain.learning.viewing_event import ViewingAction
from domain.shared.ids import (
    LectureId,
    LearnerId,
    LearningSessionId,
    QuizAttemptId,
    ViewingEventId,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _lecture(*, sample_quiz_definition, lecture_id: str = "lecture-1") -> Lecture:
    return Lecture.create(
        id=LectureId(lecture_id),
        title="講義1",
        video_url="https://example.com/video.mp4",
        srt_path="/path/to/sub.srt",
        quiz_definition=sample_quiz_definition,
    )


def _session(
    *,
    session_id: str = "session-1",
    learner_id: str = "learner-1",
    lecture_id: str = "lecture-1",
) -> LearningSession:
    return LearningSession.start(
        id=LearningSessionId(session_id),
        learner_id=LearnerId(learner_id),
        lecture_id=LectureId(lecture_id),
        started_at=FIXED_NOW,
    )


class TestLearningSnapshotBuilder:
    """LearningSnapshotBuilder が 1 Session スコープの Read Model を生成する。"""

    def test_builds_snapshot_with_required_fields(
        self, sample_quiz_definition
    ) -> None:
        """出力に sessionId, learnerId, lectureId, viewingEvents, latestQuizAttempt, quizAnswers が含まれる。"""
        session = (
            _session()
            .record_viewing_event(
                event_id=ViewingEventId("ve-1"),
                occurred_at=FIXED_NOW,
                video_position=10,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
            .record_quiz_attempt(
                attempt_id=QuizAttemptId("qa-1"),
                attempted_at=FIXED_NOW,
                score_numerator=1,
                score_denominator=2,
                answers=(
                    QuizAnswer(
                        question_index=1, selected_answer="A", is_correct=True
                    ),
                ),
            )
        )
        lecture = _lecture(sample_quiz_definition=sample_quiz_definition)

        snapshot = LearningSnapshotBuilder.build(session=session, lecture=lecture)

        assert isinstance(snapshot, LearningSnapshot)
        assert snapshot.session_id == session.id
        assert snapshot.learner_id == session.learner_id
        assert snapshot.lecture_id == session.lecture_id
        assert len(snapshot.viewing_events) == 1
        assert snapshot.latest_quiz_attempt is not None
        assert snapshot.latest_quiz_attempt.id == QuizAttemptId("qa-1")
        assert len(snapshot.quiz_answers) == 1
        assert snapshot.quiz_answers[0].question_index == 1

    def test_selects_latest_quiz_attempt_by_attempted_at(
        self, sample_quiz_definition
    ) -> None:
        """複数 QuizAttempt があるとき attemptedAt が最新のものを latestQuizAttempt にする。"""
        older = FIXED_NOW
        newer = FIXED_NOW + timedelta(hours=1)
        session = (
            _session()
            .record_quiz_attempt(
                attempt_id=QuizAttemptId("qa-old"),
                attempted_at=older,
                score_numerator=1,
                score_denominator=2,
                answers=(
                    QuizAnswer(
                        question_index=1, selected_answer="A", is_correct=True
                    ),
                ),
            )
            .record_quiz_attempt(
                attempt_id=QuizAttemptId("qa-new"),
                attempted_at=newer,
                score_numerator=2,
                score_denominator=2,
                answers=(
                    QuizAnswer(
                        question_index=1, selected_answer="B", is_correct=False
                    ),
                    QuizAnswer(
                        question_index=2, selected_answer="Y", is_correct=True
                    ),
                ),
            )
        )
        lecture = _lecture(sample_quiz_definition=sample_quiz_definition)

        snapshot = LearningSnapshotBuilder.build(session=session, lecture=lecture)

        assert snapshot.latest_quiz_attempt is not None
        assert snapshot.latest_quiz_attempt.id == QuizAttemptId("qa-new")
        assert len(snapshot.quiz_answers) == 2
        assert snapshot.quiz_answers[1].question_index == 2

    def test_no_quiz_attempts_yields_none_and_empty_answers(
        self, sample_quiz_definition
    ) -> None:
        """QuizAttempt が無いとき latestQuizAttempt は None、quizAnswers は空。"""
        session = _session()
        lecture = _lecture(sample_quiz_definition=sample_quiz_definition)

        snapshot = LearningSnapshotBuilder.build(session=session, lecture=lecture)

        assert snapshot.latest_quiz_attempt is None
        assert snapshot.quiz_answers == ()

    def test_snapshot_scope_is_single_session_only(
        self, sample_quiz_definition
    ) -> None:
        """Builder 出力は入力 LearningSession のデータのみを含む（他 Session の混入なし）。"""
        session = (
            _session(session_id="session-a", learner_id="learner-a")
            .record_viewing_event(
                event_id=ViewingEventId("ve-a"),
                occurred_at=FIXED_NOW,
                video_position=5,
                action=ViewingAction.PAUSE,
                position_delta=0,
            )
        )
        lecture = _lecture(sample_quiz_definition=sample_quiz_definition)

        snapshot = LearningSnapshotBuilder.build(session=session, lecture=lecture)

        assert snapshot.session_id == LearningSessionId("session-a")
        assert snapshot.learner_id == LearnerId("learner-a")
        assert all(event.id == ViewingEventId("ve-a") for event in snapshot.viewing_events)

    def test_rejects_lecture_id_mismatch(self, sample_quiz_definition) -> None:
        """Session.lectureId と Lecture.id が一致しないとき拒否する。"""
        session = _session(lecture_id="lecture-1")
        lecture = _lecture(
            lecture_id="lecture-other", sample_quiz_definition=sample_quiz_definition
        )

        with pytest.raises(ValueError):
            LearningSnapshotBuilder.build(session=session, lecture=lecture)

    def test_builder_does_not_return_prompt_string(
        self, sample_quiz_definition
    ) -> None:
        """Builder は LLM プロンプト文字列を生成しない。"""
        session = _session()
        lecture = _lecture(sample_quiz_definition=sample_quiz_definition)

        result = LearningSnapshotBuilder.build(session=session, lecture=lecture)

        assert not isinstance(result, str)
