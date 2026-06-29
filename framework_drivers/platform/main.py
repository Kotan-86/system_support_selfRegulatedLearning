# 仕様: docs/spec/framework-drivers-layer.md#HTTP-契約
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-4-platform-配線
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-5-講義動画フロント
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-6-LAD-AI-統合フロント
"""Flask アプリ factory — 全 API を Controller 経由で配線する。"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for
from jinja2 import ChoiceLoader, FileSystemLoader

from framework_drivers.db.learning.sqlite_connection import connect_learning_db
from framework_drivers.db.learning.static_lecture_catalog import build_near_term_lecture
from framework_drivers.db.tutoring.sqlite_connection import connect_tutor_db
from framework_drivers.external.youtube.youtube_video_id import extract_youtube_video_id
from framework_drivers.platform.http_response import controller_result_to_flask_response
from framework_drivers.platform.wiring import (
    build_get_last_updated_controller,
    build_get_learning_snapshot_controller,
    build_record_quiz_attempt_controller,
    build_record_viewing_event_controller,
    build_send_chat_message_controller,
    get_learning_db_path,
    get_tutor_db_path,
    init_databases,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_PLATFORM_ROOT = Path(__file__).resolve().parent

_DEFAULT_QUIZ_FORM_URL = "https://forms.gle/imt5HxuzNHnJkeW26"
"""lecture_video_platform/lectureVideoPlatform.html と同一の Google Form URL。"""

_REFLECT_FIXED_TEXT = {
    "reflection_intro": (
        "動画視聴中の操作（再生・一時停止・スキップ・シーク）の分布を確認し、"
        "どの操作が多かったか振り返ってみましょう。"
    ),
    "segment_chart_hint": (
        "動画を 2 分（120 秒）ごとの区間に分け、各区間での操作回数を表示します。"
        "操作が集中している区間は、理解に時間がかかった箇所かもしれません。"
    ),
    "quiz_reflection_hint": (
        "小テストの正誤と選択した回答を確認し、"
        "間違えた問題は動画のどの部分と関連しているか考えてみましょう。"
    ),
    "profile_reflection_hint": (
        "学習者タイプと視聴行動の指標を参考に、"
        "自分の学習スタイルと改善点を振り返ってみましょう。"
    ),
}


def _resolve_quiz_form_url() -> str:
    return os.environ.get("QUIZ_FORM_URL", _DEFAULT_QUIZ_FORM_URL).strip()


def _resolve_lecture_youtube_video_id() -> str:
    lecture = build_near_term_lecture()
    video_id = extract_youtube_video_id(lecture.video_url)
    if video_id is None:
        raise RuntimeError(
            "近い実験講義の video_url から YouTube video ID を解決できません"
        )
    return video_id


def create_app() -> Flask:
    """Flask アプリを生成し、Composition Root 経由でルートを登録する。"""
    init_databases()

    app = Flask(
        __name__,
        template_folder=str(_PLATFORM_ROOT / "templates"),
        static_folder=str(_PLATFORM_ROOT / "static"),
    )
    app.jinja_loader = ChoiceLoader(
        [
            FileSystemLoader(str(_PLATFORM_ROOT / "templates")),
            FileSystemLoader(str(_PROJECT_ROOT / "app" / "templates")),
        ]
    )
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "tutor_secret_key")

    @app.before_request
    def _open_db_connections() -> None:
        g.learning_conn = connect_learning_db(get_learning_db_path())
        g.tutor_conn = connect_tutor_db(get_tutor_db_path())

    @app.teardown_appcontext
    def _close_db_connections(exc: BaseException | None) -> None:
        for attr in ("learning_conn", "tutor_conn"):
            conn = g.pop(attr, None)
            if conn is not None:
                conn.close()

    @app.route("/")
    def index():
        """ルート: /reflect へリダイレクト（クエリ文字列を保持）。"""
        target = url_for("reflect")
        if request.query_string:
            target = f"{target}?{request.query_string.decode()}"
        return redirect(target)

    @app.route("/reflect")
    def reflect():
        """GET /reflect: LAD + AI 振り返り統合画面（participant_id クエリ必須）。"""
        participant_id = request.args.get("participant_id", "").strip()
        if not participant_id:
            return (
                render_template(
                    "reflect.html",
                    missing_participant_id=True,
                    participant_id="",
                    **_REFLECT_FIXED_TEXT,
                ),
                400,
            )
        return render_template(
            "reflect.html",
            missing_participant_id=False,
            participant_id=participant_id,
            **_REFLECT_FIXED_TEXT,
        )

    @app.route("/lecture")
    def lecture():
        """GET /lecture: 講義動画ページ（participant_id クエリ必須）。"""
        participant_id = request.args.get("participant_id", "").strip()
        if not participant_id:
            return (
                render_template(
                    "lecture.html",
                    missing_participant_id=True,
                    participant_id="",
                    youtube_video_id="",
                    quiz_form_url=_resolve_quiz_form_url(),
                ),
                400,
            )
        return render_template(
            "lecture.html",
            missing_participant_id=False,
            participant_id=participant_id,
            youtube_video_id=_resolve_lecture_youtube_video_id(),
            quiz_form_url=_resolve_quiz_form_url(),
        )

    @app.route("/chat", methods=["POST"])
    def chat():
        """POST /chat: SendChatMessageController 経由で AI 応答を返す。"""
        data = request.get_json(silent=True) or {}
        controller = build_send_chat_message_controller(
            learning_connection=g.learning_conn,
            tutor_connection=g.tutor_conn,
        )
        result = controller.execute(data, sent_at=datetime.now(timezone.utc))
        return controller_result_to_flask_response(result)

    @app.route("/api/quiz-attempts", methods=["POST"])
    def api_quiz_attempts():
        """POST /api/quiz-attempts: 小テスト 1 試行を記録する。"""
        data = request.get_json(silent=True) or {}
        controller = build_record_quiz_attempt_controller(g.learning_conn)
        result = controller.execute(data)
        return controller_result_to_flask_response(result)

    @app.route("/api/viewing-log", methods=["POST"])
    def api_viewing_log():
        """POST /api/viewing-log: 視聴ログ 1 件を記録する。"""
        data = request.get_json(silent=True) or {}
        controller = build_record_viewing_event_controller(g.learning_conn)
        result = controller.execute(data)
        return controller_result_to_flask_response(result)

    @app.route("/api/last-updated", methods=["GET"])
    def api_last_updated():
        """GET /api/last-updated: 学習データの最終更新時刻を返す。"""
        participant_id = request.args.get("participant_id")
        if not participant_id:
            from interfaces.learning.view_models.last_updated import LastUpdatedViewModel

            return controller_result_to_flask_response(
                LastUpdatedViewModel(last_updated=None)
            )
        lecture_id = request.args.get("lecture_id")
        controller = build_get_last_updated_controller(g.learning_conn)
        result = controller.execute(participant_id, lecture_id=lecture_id)
        return controller_result_to_flask_response(result)

    @app.route("/api/participants/<participant_id>/lad", methods=["GET"])
    def api_participants_lad(participant_id: str):
        """GET /api/participants/<participant_id>/lad: LAD ViewModel を返す。"""
        controller = build_get_learning_snapshot_controller(g.learning_conn)
        lecture_id = request.args.get("lecture_id")
        result = controller.execute(participant_id, lecture_id=lecture_id)
        return controller_result_to_flask_response(result)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
