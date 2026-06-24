# 仕様: docs/spec/interfaces-layer.md#ErrorViewModel
"""Learning 向け ViewModel 型。"""

from interfaces.learning.view_models.errors import ErrorViewModel, StatusKind
from interfaces.learning.view_models.lad_dashboard import (
    LadDashboardViewModel,
    LearnerProfileViewModel,
    LearningBehaviorViewModel,
    QuizResultRowViewModel,
    VideoSegmentViewModel,
)
from interfaces.learning.view_models.last_updated import LastUpdatedViewModel
from interfaces.learning.view_models.record_responses import (
    RecordQuizAttemptSuccessViewModel,
    RecordViewingEventSuccessViewModel,
)

__all__ = [
    "ErrorViewModel",
    "LadDashboardViewModel",
    "LastUpdatedViewModel",
    "LearnerProfileViewModel",
    "LearningBehaviorViewModel",
    "QuizResultRowViewModel",
    "RecordQuizAttemptSuccessViewModel",
    "RecordViewingEventSuccessViewModel",
    "StatusKind",
    "VideoSegmentViewModel",
]
