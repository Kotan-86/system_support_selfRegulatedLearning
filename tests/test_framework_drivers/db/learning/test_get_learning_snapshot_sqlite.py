# 仕様: docs/spec/application-usecase.md#GetLearningSnapshot
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-2-Learning-Read
"""GetLearningSnapshot Read 経路と SqliteLearningSessionRepository の統合テスト。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from application.common.result import Ok
from application.learning.dto.get_learning_snapshot import GetLearningSnapshotRequest
from application.learning.dto.record_quiz_attempt import RecordQuizAttemptRequest
from application.learning.dto.record_viewing_event import RecordViewingEventRequest
from application.learning.use_cases.get_learning_snapshot import GetLearningSnapshotUseCase
from domain.learning.quiz_attempt import QuizAnswer
from domain.learning.viewing_event import ViewingAction
from domain.shared.ids import LectureId, LearnerId
from framework_drivers.db.learning.sqlite_learning_session_repository import (
    SqliteLearningSessionRepository,
)
from framework_drivers.db.learning.static_lecture_catalog import StaticLectureCatalog
from framework_drivers.external.youtube.youtube_video_duration_resolver import (
    YoutubeVideoDurationResolver,
)
from framework_drivers.platform.learning_read_wiring import (
    build_get_learning_snapshot_controller,
)
from interfaces.common.default_lecture import DEFAULT_LECTURE_ID_VALUE
from interfaces.common.json_encoding import lad_dashboard_view_model_to_json_dict
from interfaces.learning.view_models.lad_dashboard import LadDashboardViewModel
from tests.test_framework_drivers.db.learning.test_record_learning_write_sqlite import (
    _five_answers,
    _quiz_use_case,
    _viewing_use_case,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
VIDEO_DURATION_SEC = 600


def _get_snapshot_use_case(
    repository: SqliteLearningSessionRepository,
) -> GetLearningSnapshotUseCase:
    return GetLearningSnapshotUseCase(
        repository=repository,
        lecture_catalog=StaticLectureCatalog(),
    )


def _snapshot_request(
    *,
    learner_id: str = "learner-1",
    lecture_id: str = DEFAULT_LECTURE_ID_VALUE,
) -> GetLearningSnapshotRequest:
    return GetLearningSnapshotRequest(
        learner_id=LearnerId(learner_id),
        lecture_id=LectureId(lecture_id),
    )


def _youtube_api_payload(*, duration: str, video_id: str = "ZXuZHNjS2tA") -> bytes:
    return json.dumps(
        {
            "items": [
                {
                    "id": video_id,
                    "contentDetails": {"duration": duration},
                }
            ]
        }
    ).encode("utf-8")


class TestGetLearningSnapshotWithSqliteRepository:
    """GetLearningSnapshotUseCase + SQLite Repository Read 経路の受入基準。"""

    def test_empty_snapshot_returns_ok_with_none_content_updated_at(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
    ) -> None:
        use_case = _get_snapshot_use_case(sqlite_learning_session_repository)

        result = use_case.execute(_snapshot_request())

        assert isinstance(result, Ok)
        snapshot = result.value.snapshot
        assert snapshot.viewing_events == ()
        assert snapshot.latest_quiz_attempt is None
        assert snapshot.quiz_answers == ()
        assert result.value.content_updated_at is None

    def test_after_viewing_write_snapshot_contains_event(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
    ) -> None:
        record_viewing = _viewing_use_case(sqlite_learning_session_repository)
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                occurred_at=FIXED_NOW,
                video_position=125,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )

        result = _get_snapshot_use_case(sqlite_learning_session_repository).execute(
            _snapshot_request()
        )

        assert isinstance(result, Ok)
        assert len(result.value.snapshot.viewing_events) == 1
        assert result.value.snapshot.viewing_events[0].action is ViewingAction.PLAY
        assert result.value.content_updated_at == FIXED_NOW

    def test_after_quiz_write_snapshot_contains_latest_attempt(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
    ) -> None:
        record_quiz = _quiz_use_case(sqlite_learning_session_repository)
        second_at = FIXED_NOW + timedelta(minutes=10)
        record_quiz.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                attempted_at=FIXED_NOW,
                score_numerator=4,
                score_denominator=5,
                answers=_five_answers(wrong_at=3),
            )
        )
        record_quiz.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                attempted_at=second_at,
                score_numerator=5,
                score_denominator=5,
                answers=_five_answers(),
            )
        )

        result = _get_snapshot_use_case(sqlite_learning_session_repository).execute(
            _snapshot_request()
        )

        assert isinstance(result, Ok)
        latest = result.value.snapshot.latest_quiz_attempt
        assert latest is not None
        assert latest.score_numerator == 5
        assert result.value.content_updated_at == second_at


class TestGetLearningSnapshotControllerWithSqliteRepository:
    """GetLearningSnapshotController + SQLite + YouTube Resolver の統合テスト。"""

    def test_empty_snapshot_returns_lad_dashboard_view_model(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        def http_get(url: str) -> bytes:
            return _youtube_api_payload(duration="PT10M")

        resolver = YoutubeVideoDurationResolver(
            api_key="test-key",
            http_get=http_get,
        )
        controller = build_get_learning_snapshot_controller(
            learning_db_conn,
            video_duration_resolver=resolver,
        )

        result = controller.execute("learner-1")

        assert isinstance(result, LadDashboardViewModel)
        assert result.video_segments == ()
        assert result.quiz_results == ()
        assert result.score is None
        assert result.content_updated_at is None
        assert result.learner_profile is not None
        assert result.learner_profile.type_code == "persistent"

    def test_after_writes_returns_aggregated_lad_view_model(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        record_viewing = _viewing_use_case(sqlite_learning_session_repository)
        record_quiz = _quiz_use_case(sqlite_learning_session_repository)
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                occurred_at=FIXED_NOW,
                video_position=125,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )
        quiz_at = FIXED_NOW + timedelta(minutes=5)
        record_quiz.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("learner-1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                attempted_at=quiz_at,
                score_numerator=5,
                score_denominator=5,
                answers=_five_answers(),
            )
        )

        def http_get(url: str) -> bytes:
            return _youtube_api_payload(duration="PT10M")

        controller = build_get_learning_snapshot_controller(
            learning_db_conn,
            video_duration_resolver=YoutubeVideoDurationResolver(
                api_key="test-key",
                http_get=http_get,
            ),
        )

        result = controller.execute("learner-1")

        assert isinstance(result, LadDashboardViewModel)
        assert result.action_counts["play"] == 1
        assert result.video_segments[0].segment_start_sec == 120
        assert result.score == 5
        assert len(result.quiz_results) == 5
        assert result.content_updated_at == quiz_at

    def test_json_dict_contains_required_lad_keys(
        self,
        learning_db_conn: sqlite3.Connection,
    ) -> None:
        controller = build_get_learning_snapshot_controller(
            learning_db_conn,
            video_duration_resolver=YoutubeVideoDurationResolver(
                api_key="test-key",
                http_get=lambda url: _youtube_api_payload(duration="PT10M"),
            ),
        )

        result = controller.execute("learner-1")
        assert isinstance(result, LadDashboardViewModel)

        payload = lad_dashboard_view_model_to_json_dict(result)
        assert set(payload) == {
            "action_counts",
            "video_segments",
            "quiz_results",
            "score",
            "learner_profile",
            "content_updated_at",
        }
        assert "viewing_logs" not in payload
        assert "latest_quiz_attempt" not in payload
        assert "quiz_answers" not in payload
