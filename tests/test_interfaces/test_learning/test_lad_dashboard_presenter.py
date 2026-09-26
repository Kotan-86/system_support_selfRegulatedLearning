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
VIDEO_DURATION_SEC = 600


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
        catalog=StaticLearnerTypeCatalog(),
        classifier=StubLearnerTypeClassifier(fixed_type_code=type_code),
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


def _segments_total(vm) -> int:
    return sum(sum(s.action_counts.values()) for s in vm.video_segments)


def _response_with(*specs: tuple[int, ViewingAction]) -> GetLearningSnapshotResponse:
    events = tuple(
        ViewingEvent.create(
            id=ViewingEventId(f"e{index}"),
            occurred_at=FIXED_NOW,
            video_position=position,
            action=action,
            position_delta=0,
        )
        for index, (position, action) in enumerate(specs)
    )
    snapshot = LearningSnapshot(
        session_id=LearningSessionId("session-1"),
        learner_id=LearnerId("learner-1"),
        lecture_id=LectureId("lecture-1"),
        viewing_events=events,
        latest_quiz_attempt=None,
        quiz_answers=(),
    )
    return GetLearningSnapshotResponse(snapshot=snapshot, content_updated_at=FIXED_NOW)


class TestLadDashboardPresenterDenseSegments:
    """仕様: docs/spec/bugs/lad-video-segments-over-10min.md#受入基準(AC1-AC7)。"""

    def test_ac1_ac2_duration_818_shows_segments_after_10min(self) -> None:
        response = _response_with((650, ViewingAction.PAUSE), (790, ViewingAction.PLAY))

        vm = _presenter().present(response, _lecture(), video_duration_sec=818)

        assert [s.segment_start_sec for s in vm.video_segments] == [
            0, 120, 240, 360, 480, 600, 720,
        ]
        by_start = {s.segment_start_sec: s for s in vm.video_segments}
        assert by_start[600].action_counts["pause"] == 1
        assert by_start[720].action_counts["play"] == 1
        for start in (0, 120, 240, 360, 480):
            assert sum(by_start[start].action_counts.values()) == 0
        assert _segments_total(vm) == sum(vm.action_counts.values()) == 2  # AC5

    def test_ac3_position_beyond_duration_is_not_dropped(self) -> None:
        response = _response_with((850, ViewingAction.PLAY))

        vm = _presenter().present(response, _lecture(), video_duration_sec=818)

        assert [s.segment_start_sec for s in vm.video_segments] == [
            120 * i for i in range(8)
        ]
        assert vm.video_segments[-1].segment_start_sec == 840
        assert vm.video_segments[-1].action_counts["play"] == 1
        assert _segments_total(vm) == sum(vm.action_counts.values()) == 1  # AC5

    def test_ac4_duration_720_with_operation_at_720(self) -> None:
        response = _response_with((720, ViewingAction.PLAY))

        vm = _presenter().present(response, _lecture(), video_duration_sec=720)

        assert [s.segment_start_sec for s in vm.video_segments] == [
            120 * i for i in range(7)
        ]
        assert vm.video_segments[-1].action_counts["play"] == 1
        assert _segments_total(vm) == sum(vm.action_counts.values()) == 1  # AC5

    def test_ac4_duration_720_and_601_without_operations_have_six_segments(self) -> None:
        for duration in (720, 601):
            vm = _presenter().present(
                _response_with(), _lecture(), video_duration_sec=duration
            )

            assert [s.segment_start_sec for s in vm.video_segments] == [
                0, 120, 240, 360, 480, 600,
            ]
            assert _segments_total(vm) == 0

    def test_ac6_duration_600_and_300_keep_five_segments(self) -> None:
        for duration in (600, 300):
            vm = _presenter().present(
                _response_with((125, ViewingAction.PLAY)),
                _lecture(),
                video_duration_sec=duration,
            )

            assert [s.segment_start_sec for s in vm.video_segments] == [
                0, 120, 240, 360, 480,
            ]
            by_start = {s.segment_start_sec: s for s in vm.video_segments}
            assert by_start[120].action_counts["play"] == 1
            assert _segments_total(vm) == sum(vm.action_counts.values()) == 1  # AC5

    def test_ac7_empty_snapshot_duration_818_has_seven_zero_segments(self) -> None:
        response = GetLearningSnapshotResponse(
            snapshot=_empty_snapshot(), content_updated_at=None
        )

        vm = _presenter().present(response, _lecture(), video_duration_sec=818)

        assert [s.segment_start_sec for s in vm.video_segments] == [
            120 * i for i in range(7)
        ]
        assert _segments_total(vm) == 0

    def test_ac9_action_counts_and_profile_behaviors_unchanged_by_dense_segments(self) -> None:
        response = _response_with((650, ViewingAction.PAUSE), (790, ViewingAction.PLAY))

        vm = _presenter().present(response, _lecture(), video_duration_sec=818)

        assert vm.action_counts == {
            "play": 1,
            "pause": 1,
            "forward_skip": 0,
            "backward_skip": 0,
            "forward_seek": 0,
            "backward_seek": 0,
        }
        assert vm.learner_profile is not None
        values = {b.label: b.value for b in vm.learner_profile.learning_behaviors}
        assert values["再生回数"] == 1
        assert values["一時停止回数"] == 1


class TestLadDashboardPresenter:
    """Presenter の変換を検証する。"""

    def test_empty_snapshot_returns_success_view_model_without_static_profile(self) -> None:
        presenter = _presenter()
        response = GetLearningSnapshotResponse(
            snapshot=_empty_snapshot(),
            content_updated_at=None,
        )

        vm = presenter.present(response, _lecture(), video_duration_sec=VIDEO_DURATION_SEC)

        assert vm.action_counts["play"] == 0
        # 仕様: docs/spec/bugs/lad-video-segments-over-10min.md#受入基準 AC7
        assert [s.segment_start_sec for s in vm.video_segments] == [0, 120, 240, 360, 480]
        assert _segments_total(vm) == 0
        assert _segments_total(vm) == sum(vm.action_counts.values())
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

        vm = presenter.present(response, _lecture(), video_duration_sec=VIDEO_DURATION_SEC)

        assert vm.action_counts["play"] == 1
        assert vm.action_counts["pause"] == 1
        # 仕様: docs/spec/bugs/lad-video-segments-over-10min.md#受入基準 AC6 / AC5
        assert [s.segment_start_sec for s in vm.video_segments] == [0, 120, 240, 360, 480]
        by_start = {s.segment_start_sec: s for s in vm.video_segments}
        assert by_start[120].action_counts["play"] == 1
        assert by_start[120].action_counts["pause"] == 1
        assert sum(by_start[0].action_counts.values()) == 0
        assert _segments_total(vm) == sum(vm.action_counts.values()) == 2

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

        vm = presenter.present(response, _lecture(), video_duration_sec=VIDEO_DURATION_SEC)

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

        vm = presenter.present(response, _lecture(), video_duration_sec=VIDEO_DURATION_SEC)

        assert vm.learner_profile is not None
        assert vm.learner_profile.type_code == "advanced"
        assert vm.learner_profile.type_name == "Advanced"
        assert vm.learner_profile.characteristics is not None
        assert vm.learner_profile.motivation is not None
        assert vm.learner_profile.performance is not None

    def test_rule_based_classifier_classifies_diligent_from_viewing_events(self) -> None:
        presenter = LadDashboardPresenter(catalog=StaticLearnerTypeCatalog())
        events = tuple(
            ViewingEvent.create(
                id=ViewingEventId(f"pause-{index}"),
                occurred_at=FIXED_NOW,
                video_position=10 * index,
                action=ViewingAction.PAUSE,
                position_delta=0,
            )
            for index in range(6)
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

        vm = presenter.present(response, _lecture(), video_duration_sec=VIDEO_DURATION_SEC)

        assert vm.learner_profile is not None
        assert vm.learner_profile.type_code == "diligent"
        assert vm.learner_profile.type_name == "Diligent"
        assert vm.learner_profile.characteristics is not None
