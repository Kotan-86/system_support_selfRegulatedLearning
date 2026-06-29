# 仕様: docs/spec/framework-drivers-layer.md#HTTP-契約
# 仕様: docs/spec/application-error-handling.md#エラーステータス一覧
"""ViewModel を Flask レスポンスへ変換する。"""
from __future__ import annotations

from typing import Any

from flask import Response, jsonify

from interfaces.common.json_encoding import (
    chat_response_view_model_to_json_dict,
    error_view_model_to_json_dict,
    lad_dashboard_view_model_to_json_dict,
    last_updated_view_model_to_json_dict,
    record_quiz_attempt_success_to_json_dict,
    record_viewing_event_success_to_json_dict,
)
from interfaces.learning.view_models.errors import ErrorViewModel, StatusKind
from interfaces.learning.view_models.last_updated import LastUpdatedViewModel
from interfaces.learning.view_models.lad_dashboard import LadDashboardViewModel
from interfaces.learning.view_models.record_responses import (
    RecordQuizAttemptSuccessViewModel,
    RecordViewingEventSuccessViewModel,
)
from interfaces.tutoring.view_models.chat_response import ChatResponseViewModel

_HTTP_STATUS_BY_KIND: dict[StatusKind, int] = {
    StatusKind.NOT_FOUND: 404,
    StatusKind.CONFLICT: 409,
    StatusKind.VALIDATION: 400,
    StatusKind.GATEWAY: 502,
}

ControllerResult = (
    LadDashboardViewModel
    | LastUpdatedViewModel
    | RecordViewingEventSuccessViewModel
    | RecordQuizAttemptSuccessViewModel
    | ChatResponseViewModel
    | ErrorViewModel
)


def http_status_for_error(view_model: ErrorViewModel) -> int:
    """ErrorViewModel.status_kind から HTTP ステータスコードを返す。"""
    return _HTTP_STATUS_BY_KIND[view_model.status_kind]


def controller_result_to_flask_response(
    result: ControllerResult,
) -> tuple[Response, int]:
    """Controller 出力を Flask レスポンス（body, status）へ変換する。"""
    if isinstance(result, ErrorViewModel):
        body: dict[str, Any] = error_view_model_to_json_dict(result)
        body["error"] = result.message
        return jsonify(body), http_status_for_error(result)

    if isinstance(result, LadDashboardViewModel):
        return jsonify(lad_dashboard_view_model_to_json_dict(result)), 200

    if isinstance(result, LastUpdatedViewModel):
        return jsonify(last_updated_view_model_to_json_dict(result)), 200

    if isinstance(result, RecordViewingEventSuccessViewModel):
        # API 契約: 成功時は空ボディ + 201
        return Response(status=201), 201

    if isinstance(result, RecordQuizAttemptSuccessViewModel):
        return jsonify(record_quiz_attempt_success_to_json_dict(result)), 201

    if isinstance(result, ChatResponseViewModel):
        return jsonify(chat_response_view_model_to_json_dict(result)), 200

    raise TypeError(f"Unsupported controller result type: {type(result)!r}")


def view_model_to_flask_response(
    result: LadDashboardViewModel | ErrorViewModel,
) -> tuple[Response, int]:
    """LAD 経路向けの後方互換ラッパ。"""
    return controller_result_to_flask_response(result)
