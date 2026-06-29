# 仕様: docs/spec/interfaces-layer.md#LadDashboardViewModel
"""ViewModel を JSON シリアライズ可能な dict へ変換する（Flask 非依存）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.learning.view_models.last_updated import LastUpdatedViewModel
from interfaces.learning.view_models.lad_dashboard import (
    LadDashboardViewModel,
    LearnerProfileViewModel,
    LearningBehaviorViewModel,
    QuizResultRowViewModel,
    VideoSegmentViewModel,
)
from interfaces.learning.view_models.record_responses import (
    RecordQuizAttemptSuccessViewModel,
    RecordViewingEventSuccessViewModel,
)
from interfaces.tutoring.view_models.chat_response import ChatResponseViewModel


def datetime_to_json(value: datetime | None) -> str | None:
    """datetime を ISO 8601 文字列へ変換する。"""
    if value is None:
        return None
    return value.isoformat()


def learning_behavior_to_json(item: LearningBehaviorViewModel) -> dict[str, Any]:
    return {"label": item.label, "value": item.value}


def learner_profile_to_json(profile: LearnerProfileViewModel | None) -> dict[str, Any] | None:
    if profile is None:
        return None
    return {
        "type_code": profile.type_code,
        "type_name": profile.type_name,
        "learning_behaviors": [
            learning_behavior_to_json(item) for item in profile.learning_behaviors
        ],
        "characteristics": profile.characteristics,
        "motivation": profile.motivation,
        "performance": profile.performance,
    }


def video_segment_to_json(segment: VideoSegmentViewModel) -> dict[str, Any]:
    return {
        "segment_start_sec": segment.segment_start_sec,
        "action_counts": dict(segment.action_counts),
    }


def quiz_result_row_to_json(row: QuizResultRowViewModel) -> dict[str, Any]:
    return {
        "question_index": row.question_index,
        "question_text": row.question_text,
        "selected_choice": row.selected_choice,
        "is_correct": row.is_correct,
    }


def lad_dashboard_view_model_to_json_dict(
    view_model: LadDashboardViewModel,
) -> dict[str, Any]:
    """LadDashboardViewModel を JSON 化可能な dict へ変換する。"""
    return {
        "action_counts": dict(view_model.action_counts),
        "video_segments": [
            video_segment_to_json(segment) for segment in view_model.video_segments
        ],
        "quiz_results": [
            quiz_result_row_to_json(row) for row in view_model.quiz_results
        ],
        "score": view_model.score,
        "learner_profile": learner_profile_to_json(view_model.learner_profile),
        "content_updated_at": datetime_to_json(view_model.content_updated_at),
    }


def error_view_model_to_json_dict(view_model: ErrorViewModel) -> dict[str, Any]:
    """ErrorViewModel を JSON 化可能な dict へ変換する。"""
    return {
        "error_code": view_model.error_code,
        "message": view_model.message,
        "status_kind": view_model.status_kind.value,
    }


def last_updated_view_model_to_json_dict(
    view_model: LastUpdatedViewModel,
) -> dict[str, Any]:
    """LastUpdatedViewModel を JSON 化可能な dict へ変換する。"""
    return {
        "last_updated": datetime_to_json(view_model.last_updated),
    }


def record_quiz_attempt_success_to_json_dict(
    view_model: RecordQuizAttemptSuccessViewModel,
) -> dict[str, Any]:
    """RecordQuizAttemptSuccessViewModel を JSON 化可能な dict へ変換する。"""
    return {
        "attempt_id": view_model.attempt_id,
        "ok": view_model.ok,
    }


def chat_response_view_model_to_json_dict(
    view_model: ChatResponseViewModel,
) -> dict[str, Any]:
    """ChatResponseViewModel を JSON 化可能な dict へ変換する。"""
    return {
        "response": view_model.response,
        "session_id": view_model.session_id,
    }


def record_viewing_event_success_to_json_dict(
    view_model: RecordViewingEventSuccessViewModel,
) -> dict[str, Any]:
    """RecordViewingEventSuccessViewModel を JSON 化可能な dict へ変換する。"""
    return {"ok": view_model.ok}
