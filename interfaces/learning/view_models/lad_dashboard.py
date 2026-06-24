# 仕様: docs/spec/interfaces-layer.md#LadDashboardViewModel
"""LAD ダッシュボード用 ViewModel。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VideoSegmentViewModel:
    """動画 120 秒区間ごとの操作集計。"""

    segment_start_sec: int
    action_counts: dict[str, int]


@dataclass(frozen=True)
class QuizResultRowViewModel:
    """小テスト結果の 1 行（問題文付き）。"""

    question_index: int
    question_text: str
    selected_choice: str
    is_correct: bool


@dataclass(frozen=True)
class LearningBehaviorViewModel:
    """学習者プロファイルの動的指標。"""

    label: str
    value: int


@dataclass(frozen=True)
class LearnerProfileViewModel:
    """学習者タイプと行動指標のプロファイル。"""

    type_code: str | None
    type_name: str | None
    learning_behaviors: tuple[LearningBehaviorViewModel, ...]
    characteristics: str | None
    motivation: str | None
    performance: str | None


@dataclass(frozen=True)
class LadDashboardViewModel:
    """GET /api/participants/{id}/lad の成功レスポンス契約。"""

    action_counts: dict[str, int]
    video_segments: tuple[VideoSegmentViewModel, ...]
    quiz_results: tuple[QuizResultRowViewModel, ...]
    score: int | None
    learner_profile: LearnerProfileViewModel | None
    content_updated_at: datetime | None
