# 仕様: docs/spec/interfaces-layer.md#LAD-表示要件と-ViewModel-契約
"""LadDashboardPresenter の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.learning.dto.get_learning_snapshot import GetLearningSnapshotResponse
from domain.learning.lecture import Lecture
from domain.learning.quiz_attempt import QuizAnswer, QuizAttempt
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import (
    LectureId,
    LearnerId,
    LearningSessionId,
    QuizAttemptId,
    ViewingEventId,
)
from interfaces.learning.catalog.learner_type_catalog import StaticLearnerTypeCatalog
from interfaces.learning.classifiers.stub_learner_type_classifier import (
    StubLearnerTypeClassifier,
)
from interfaces.learning.presenters.lad_dashboard_presenter import LadDashboardPresenter
from domain.learning.learning_snapshot import LearningSnapshot

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _lecture() -> Lecture:
    return Lecture.create(
        id=LectureId("lecture-1"),
        title="サンプル講義",
        video_url="https://example.com/video.mp4",
        srt_path="/path/to/subtitles.srt",
        quiz_definition=QuizDefinition(
            questions=(
                Question(
                    index=1,
                    text="問1の本文",
                    choices=("A", "B"),
                    correct_answer="A",
                ),
                Question(
                    index=2,
                    text="問2の本文",
                    choices=("A", "B"),
                    correct_answer="A",
                ),
            )
        ),
    )


def _presenter(*, type_code: str | None = None) -> LadDashboardPresenter:
    return LadDashboardPresenter(
        classifier=StubLearnerTypeClassifier(fixed_type_code=type_code),
        catalog=StaticLearnerTypeCatalog(),
    )


def _empty_snapshot() -> LearningSnapshot:
    return LearningSnapshot(
        session_id=LearningSessionId("uncreated"),
        learner_id=LearnerId("learner-1"),
        lecture_id=LectureId("lecture-1"),
        viewing_events=(),
        latest_quiz_attempt=None,
        quiz_answers=(),
    )


class TestLadDashboardPresenter:
    """Presenter の変換を検証する。"""

    def test_empty_snapshot_returns_success_view_model_without_static_profile(self) -> None:
        presenter = _presenter()
        response = GetLearningSnapshotResponse(
            snapshot=_empty_snapshot(),
            content_updated_at=None,
        )

        vm = presenter.present(response, _lecture())

        assert vm.action_counts["play"] == 0
        assert vm.video_segments == ()
        assert vm.quiz_results == ()
        assert vm.score is None
        assert vm.content_updated_at is None
        assert vm.learner_profile is not None
        assert vm.learner_profile.type_code is None
        assert vm.learner_profile.type_name is None
        assert vm.learner_profile.characteristics is None
        assert len(vm.learner_profile.learning_behaviors) == 6
        assert all(behavior.value == 0 for behavior in vm.learner_profile.learning_behaviors)

    def test_viewing_events_produce_action_counts_and_segments(self) -> None:
        presenter = _presenter()
        events = (
            ViewingEvent.create(
                id=ViewingEventId("e1"),
                occurred_at=FIXED_NOW,
                video_position=125,
                action=ViewingAction.PLAY,
                position_delta=0,
            ),
            ViewingEvent.create(
                id=ViewingEventId("e2"),
                occurred_at=FIXED_NOW,
                video_position=125,
                action=ViewingAction.PAUSE,
                position_delta=0,
            ),
        )
        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=events,
            latest_quiz_attempt=None,
            quiz_answers=(),
        )
        response = GetLearningSnapshotResponse(
            snapshot=snapshot,
            content_updated_at=FIXED_NOW,
        )

        vm = presenter.present(response, _lecture())

        assert vm.action_counts["play"] == 1
        assert vm.action_counts["pause"] == 1
        assert len(vm.video_segments) == 1
        assert vm.video_segments[0].segment_start_sec == 120

    def test_quiz_results_include_question_text(self) -> None:
        presenter = _presenter()
        attempt = QuizAttempt.create(
            id=QuizAttemptId("attempt-1"),
            attempted_at=FIXED_NOW,
            score_numerator=1,
            score_denominator=2,
            answers=(
                QuizAnswer(question_index=1, selected_answer="A", is_correct=True),
                QuizAnswer(question_index=2, selected_answer="B", is_correct=False),
            ),
        )
        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=(),
            latest_quiz_attempt=attempt,
            quiz_answers=attempt.answers,
        )
        response = GetLearningSnapshotResponse(
            snapshot=snapshot,
            content_updated_at=FIXED_NOW,
        )

        vm = presenter.present(response, _lecture())

        assert vm.score == 1
        assert len(vm.quiz_results) == 2
        first_row = vm.quiz_results[0]
        assert first_row.question_index == 1
        assert first_row.question_text == "問1の本文"
        assert first_row.selected_choice == "A"
        assert first_row.is_correct is True

    def test_type_code_includes_catalog_static_text(self) -> None:
        presenter = _presenter(type_code="advanced")
        response = GetLearningSnapshotResponse(
            snapshot=_empty_snapshot(),
            content_updated_at=None,
        )

        vm = presenter.present(response, _lecture())

        assert vm.learner_profile is not None
        assert vm.learner_profile.type_code == "advanced"
        assert vm.learner_profile.type_name == "Advanced"
        assert vm.learner_profile.characteristics is not None
        assert vm.learner_profile.motivation is not None
        assert vm.learner_profile.performance is not None
