# 仕様: docs/spec/interfaces-layer.md#既存-API-対応表
"""GetLearningSnapshotController の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.common.errors import ErrorCode, ValidationError, VideoMetadataGatewayError
from application.learning.use_cases.get_learning_snapshot import GetLearningSnapshotUseCase
from domain.learning.lecture import Lecture
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.shared.ids import LectureId, LearnerId
from interfaces.learning.catalog.learner_type_catalog import StaticLearnerTypeCatalog
from interfaces.learning.classifiers.stub_learner_type_classifier import (
    StubLearnerTypeClassifier,
)
from interfaces.learning.controllers.get_learning_snapshot_controller import (
    GetLearningSnapshotController,
)
from interfaces.learning.presenters.lad_dashboard_presenter import LadDashboardPresenter
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.learning.view_models.lad_dashboard import LadDashboardViewModel
from tests.test_interfaces.fakes.fake_video_duration_resolver import (
    FakeVideoDurationResolver,
)
from tests.test_application.fakes.learning.fake_lecture_catalog import FakeLectureCatalog
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)
from tests.test_application.test_learning.test_get_learning_snapshot import (
    _get_snapshot_use_case,
    _record_viewing_use_case,
)
from application.learning.dto.record_viewing_event import RecordViewingEventRequest
from domain.learning.viewing_event import ViewingAction

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _lecture(*, lecture_id: str = "lecture-1") -> Lecture:
    return Lecture.create(
        id=LectureId(lecture_id),
        title="サンプル講義",
        video_url="https://example.com/video.mp4",
        srt_path="/path/to/subtitles.srt",
        quiz_definition=QuizDefinition(
            questions=(
                Question(
                    index=1,
                    text="問1",
                    choices=("A", "B"),
                    correct_answer="A",
                ),
            )
        ),
    )


def _controller(
    use_case: GetLearningSnapshotUseCase,
    *,
    lectures: tuple[Lecture, ...] | None = None,
    video_duration_resolver: FakeVideoDurationResolver | None = None,
) -> GetLearningSnapshotController:
    catalog = FakeLectureCatalog(
        lectures=lectures if lectures is not None else (_lecture(),)
    )
    presenter = LadDashboardPresenter(
        catalog=StaticLearnerTypeCatalog(),
        classifier=StubLearnerTypeClassifier(),
    )
    resolver = video_duration_resolver or FakeVideoDurationResolver(duration_sec=600)
    return GetLearningSnapshotController(
        use_case=use_case,
        presenter=presenter,
        lecture_catalog=catalog,
        video_duration_resolver=resolver,
    )


class TestGetLearningSnapshotController:
    """Controller の ingress と UC 連携を検証する。"""

    def test_empty_participant_id_returns_validation_error_view_model(self) -> None:
        use_case = _get_snapshot_use_case()
        controller = _controller(use_case)

        result = controller.execute("")

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.VALIDATION_ERROR.value
        assert result.status_kind.value == "validation"

    def test_no_session_returns_success_lad_view_model(self) -> None:
        use_case = _get_snapshot_use_case()
        controller = _controller(use_case)

        result = controller.execute("learner-1", lecture_id="lecture-1")

        assert isinstance(result, LadDashboardViewModel)
        # 仕様: docs/spec/bugs/lad-video-segments-over-10min.md#受入基準 AC7
        assert [s.segment_start_sec for s in result.video_segments] == [
            0, 120, 240, 360, 480,
        ]
        assert sum(sum(s.action_counts.values()) for s in result.video_segments) == 0
        assert result.score is None
        assert result.learner_profile is not None
        assert result.learner_profile.type_code is None

    def test_no_session_with_video_duration_818_returns_seven_zero_segments(self) -> None:
        # 仕様: docs/spec/bugs/lad-video-segments-over-10min.md#受入基準 AC7
        use_case = _get_snapshot_use_case()
        controller = _controller(
            use_case, video_duration_resolver=FakeVideoDurationResolver(duration_sec=818)
        )

        result = controller.execute("learner-1", lecture_id="lecture-1")

        assert isinstance(result, LadDashboardViewModel)
        assert [s.segment_start_sec for s in result.video_segments] == [
            120 * i for i in range(7)
        ]

    def test_viewing_after_10min_with_duration_818_is_in_dense_segments(self) -> None:
        # 仕様: docs/spec/bugs/lad-video-segments-over-10min.md#受入基準 AC1 / AC5
        repository = InMemoryLearningSessionRepository()
        use_case = _get_snapshot_use_case(repository=repository)
        controller = _controller(
            use_case, video_duration_resolver=FakeVideoDurationResolver(duration_sec=818)
        )
        record_viewing = _record_viewing_use_case(repository)
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                occurred_at=FIXED_NOW,
                video_position=650,
                action=ViewingAction.PAUSE,
                position_delta=0,
            )
        )

        result = controller.execute("learner-1", lecture_id="lecture-1")

        assert isinstance(result, LadDashboardViewModel)
        by_start = {s.segment_start_sec: s for s in result.video_segments}
        assert sorted(by_start) == [120 * i for i in range(7)]
        assert by_start[600].action_counts["pause"] == 1
        assert sum(
            sum(s.action_counts.values()) for s in result.video_segments
        ) == sum(result.action_counts.values()) == 1

    def test_missing_lecture_returns_lecture_not_found(self) -> None:
        use_case = _get_snapshot_use_case(lectures=())
        controller = _controller(use_case, lectures=())

        result = controller.execute("learner-1", lecture_id="missing")

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.LECTURE_NOT_FOUND.value
        assert result.status_kind.value == "not_found"

    def test_after_viewing_event_returns_aggregated_view_model(self) -> None:
        repository = InMemoryLearningSessionRepository()
        use_case = _get_snapshot_use_case(repository=repository)
        controller = _controller(use_case)
        record_viewing = _record_viewing_use_case(repository)
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId("lecture-1"),
                occurred_at=FIXED_NOW,
                video_position=125,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )

        result = controller.execute("learner-1", lecture_id="lecture-1")

        assert isinstance(result, LadDashboardViewModel)
        assert result.action_counts["play"] == 1
        # 仕様: docs/spec/bugs/lad-video-segments-over-10min.md#受入基準 AC6 / AC5
        by_start = {s.segment_start_sec: s for s in result.video_segments}
        assert sorted(by_start) == [0, 120, 240, 360, 480]
        assert by_start[120].action_counts["play"] == 1
        assert sum(
            sum(s.action_counts.values()) for s in result.video_segments
        ) == sum(result.action_counts.values())
        assert result.content_updated_at == FIXED_NOW

    def test_video_duration_validation_error_returns_error_view_model(self) -> None:
        use_case = _get_snapshot_use_case()
        resolver = FakeVideoDurationResolver(
            error=ValidationError("duration must be positive"),
        )
        controller = _controller(use_case, video_duration_resolver=resolver)

        result = controller.execute("learner-1", lecture_id="lecture-1")

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.VALIDATION_ERROR.value
        assert result.status_kind.value == "validation"
        assert len(resolver.resolve_calls) == 1

    def test_video_metadata_gateway_error_returns_error_view_model(self) -> None:
        use_case = _get_snapshot_use_case()
        resolver = FakeVideoDurationResolver(
            error=VideoMetadataGatewayError("YouTube API unavailable"),
        )
        controller = _controller(use_case, video_duration_resolver=resolver)

        result = controller.execute("learner-1", lecture_id="lecture-1")

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.VIDEO_METADATA_GATEWAY_ERROR.value
        assert result.status_kind.value == "gateway"
        assert len(resolver.resolve_calls) == 1
