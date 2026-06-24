# 仕様: docs/spec/interfaces-layer.md#LAD-表示要件と-ViewModel-契約
"""GetLearningSnapshot の結果を LAD ViewModel へ変換する。"""
from __future__ import annotations

from application.learning.dto.get_learning_snapshot import GetLearningSnapshotResponse
from domain.learning.lecture import Lecture

from interfaces.learning.ports.learner_type_catalog import LearnerTypeCatalog
from interfaces.learning.ports.learner_type_classifier import LearnerTypeClassifier
from interfaces.learning.services.quiz_result_rows import build_quiz_result_rows
from interfaces.learning.services.viewing_behavior_metrics import ViewingBehaviorMetrics
from interfaces.learning.view_models.lad_dashboard import (
    LadDashboardViewModel,
    LearnerProfileViewModel,
    LearningBehaviorViewModel,
    VideoSegmentViewModel,
)


class LadDashboardPresenter:
    """LearningSnapshot を LAD 表示用 ViewModel へ変換する。"""

    def __init__(
        self,
        classifier: LearnerTypeClassifier,
        catalog: LearnerTypeCatalog,
    ) -> None:
        self._classifier = classifier
        self._catalog = catalog

    def present(
        self,
        response: GetLearningSnapshotResponse,
        lecture: Lecture,
    ) -> LadDashboardViewModel:
        snapshot = response.snapshot
        metrics = ViewingBehaviorMetrics.from_events(snapshot.viewing_events)
        type_code = self._classifier.classify(metrics)
        catalog_entry = self._catalog.lookup(type_code) if type_code else None

        learning_behaviors = tuple(
            LearningBehaviorViewModel(label=item.label, value=item.value)
            for item in metrics.learning_behaviors()
        )
        learner_profile = LearnerProfileViewModel(
            type_code=type_code,
            type_name=catalog_entry.type_name if catalog_entry else None,
            learning_behaviors=learning_behaviors,
            characteristics=catalog_entry.characteristics if catalog_entry else None,
            motivation=catalog_entry.motivation if catalog_entry else None,
            performance=catalog_entry.performance if catalog_entry else None,
        )

        score = (
            snapshot.latest_quiz_attempt.score_numerator
            if snapshot.latest_quiz_attempt is not None
            else None
        )

        return LadDashboardViewModel(
            action_counts=dict(metrics.action_counts),
            video_segments=tuple(
                VideoSegmentViewModel(
                    segment_start_sec=segment.segment_start_sec,
                    action_counts=dict(segment.action_counts),
                )
                for segment in metrics.video_segments
            ),
            quiz_results=build_quiz_result_rows(
                snapshot.quiz_answers,
                lecture.quiz_definition,
            ),
            score=score,
            learner_profile=learner_profile,
            content_updated_at=response.content_updated_at,
        )
