# 仕様: docs/spec/interfaces-layer.md#LastUpdatedViewModel
"""LastUpdatedPresenter の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from application.learning.dto.get_learning_snapshot import GetLearningSnapshotResponse
from domain.learning.learning_snapshot import LearningSnapshot
from domain.shared.ids import LectureId, LearnerId, LearningSessionId
from interfaces.learning.presenters.last_updated_presenter import LastUpdatedPresenter

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _empty_snapshot() -> LearningSnapshot:
    return LearningSnapshot(
        session_id=LearningSessionId("uncreated"),
        learner_id=LearnerId("learner-1"),
        lecture_id=LectureId("lecture-1"),
        viewing_events=(),
        latest_quiz_attempt=None,
        quiz_answers=(),
    )


class TestLastUpdatedPresenter:
    """Presenter の変換を検証する。"""

    def test_none_content_updated_at_maps_to_null_last_updated(self) -> None:
        presenter = LastUpdatedPresenter()
        response = GetLearningSnapshotResponse(
            snapshot=_empty_snapshot(),
            content_updated_at=None,
        )

        vm = presenter.present(response)

        assert vm.last_updated is None

    def test_content_updated_at_maps_to_last_updated(self) -> None:
        presenter = LastUpdatedPresenter()
        response = GetLearningSnapshotResponse(
            snapshot=_empty_snapshot(),
            content_updated_at=FIXED_NOW,
        )

        vm = presenter.present(response)

        assert vm.last_updated == FIXED_NOW
