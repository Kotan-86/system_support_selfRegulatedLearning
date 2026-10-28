# 仕様: docs/spec/framework-drivers-layer.md#HTTP-契約
# 仕様: docs/spec/lecture-selection.md#実現内容what
# 仕様: docs/spec/participant-login.md#3-参加者の特定fr-52
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-4-platform-配線
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-5-講義動画フロント
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-6-LAD-AI-統合フロント
"""Flask アプリ factory — 全 API を Controller 経由で配線する。"""
from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, g, redirect, render_template, request, url_for
from jinja2 import ChoiceLoader, FileSystemLoader

from application.common.errors import ErrorCode
from domain.shared.ids import LearnerId, LectureId
from framework_drivers.db.learning.quiz_definitions import (
    lecture_1,
    lecture_2,
    lecture_3,
    lecture_4,
    lecture_5,
    lecture_6,
)
from framework_drivers.db.learning.sqlite_connection import connect_learning_db
from framework_drivers.db.learning.static_lecture_catalog import StaticLectureCatalog
from framework_drivers.db.tutoring.sqlite_connection import connect_tutor_db
from framework_drivers.external.youtube.youtube_video_id import extract_youtube_video_id
from interfaces.common.learner_lecture_mapping import resolve_lecture_id_for_participant
from framework_drivers.platform.http_response import (
    controller_result_to_flask_response,
    http_status_for_error,
)
from framework_drivers.platform.https_enforcement import register_https_enforcement
from framework_drivers.platform.participant_auth import (
    DEFAULT_AFTER_LOGIN_PATH,
    current_participant_id,
    load_secret_key,
    register_participant_auth,
)
from framework_drivers.platform.participant_credentials import (
    PARTICIPANT_CREDENTIALS_FILE_ENV,
    load_credentials_file,
)
from framework_drivers.platform.participant_scope import resolve_claimed_participant_id
from framework_drivers.platform.research_auth import register_research_auth
from interfaces.learning.view_models.errors import ErrorViewModel
from framework_drivers.platform.wiring import (
    build_export_dialog_logs_controller,
    build_get_last_updated_controller,
    build_get_learning_snapshot_controller,
    build_record_quiz_attempt_controller,
    build_record_viewing_event_controller,
    build_save_dialog_log_controller,
    build_select_lecture_use_case,
    build_send_chat_message_controller,
    get_learning_db_path,
    get_tutor_db_path,
    init_databases,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_PLATFORM_ROOT = Path(__file__).resolve().parent

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


_TUTOR_SESSION_NOT_FOUND_CODE = ErrorCode.TUTOR_SESSION_NOT_FOUND.value

_STATIC_LECTURE_CATALOG = StaticLectureCatalog()

_QUIZ_MODULES = {
    "lecture-1": lecture_1,
    "lecture-2": lecture_2,
    "lecture-3": lecture_3,
    "lecture-4": lecture_4,
    "lecture-5": lecture_5,
    "lecture-6": lecture_6,
}


def _quiz_template_context(lecture_id: str) -> dict[str, object]:
    """講義 ID からテンプレート用の小テスト表示データを組み立てる（正解は answer_key のみ）。"""
    module = _QUIZ_MODULES.get(lecture_id)
    if module is None:
        raise ValueError(f"Unknown lecture_id: {lecture_id}")

    lecture = _STATIC_LECTURE_CATALOG.find_by_id(LectureId(lecture_id))
    if lecture is None:
        raise ValueError(f"Unknown lecture_id: {lecture_id}")

    quiz = lecture.quiz_definition
    return {
        "quiz_title": module.QUIZ_TITLE,
        "quiz_description": module.QUIZ_DESCRIPTION,
        "quiz_questions": [
            {"index": question.index, "text": question.text, "choices": question.choices}
            for question in quiz.questions
        ],
        "quiz_answer_key": {
            question.index: question.correct_answer for question in quiz.questions
        },
    }


def _resolve_youtube_video_id_for_participant(
    participant_id: str,
    *,
    lecture_id: str | None = None,
) -> tuple[str, str]:
    """participant から講義 ID と YouTube video ID を解決する。

    Raises:
        ValueError: lecture_id 解決失敗、未知講義、または video URL が不正なとき。
    """
    resolve_result = resolve_lecture_id_for_participant(participant_id, lecture_id)
    if resolve_result.is_err:
        raise ValueError(str(resolve_result.error))

    resolved_lecture_id = resolve_result.value
    lecture = _STATIC_LECTURE_CATALOG.find_by_id(resolved_lecture_id)
    if lecture is None:
        raise ValueError(f"Unknown lecture_id: {resolved_lecture_id}")

    video_id = extract_youtube_video_id(lecture.video_url)
    if video_id is None:
        raise ValueError(
            f"lecture {resolved_lecture_id} の video_url から YouTube video ID を解決できません"
        )
    return str(resolved_lecture_id), video_id


def _subtitle_cues_for_lecture(lecture_id: str) -> list[dict[str, object]]:
    """講義の SRT を画面用の字幕キュー(秒)にする。読めないときは空。

    仕様: docs/spec/subtitle-display.md#受入基準 (AC11, AC12)
    重なりの整理はしない(画面側で行う)。
    """
    from interfaces.tutoring.srt import parse_srt_file

    lecture = _STATIC_LECTURE_CATALOG.find_by_id(LectureId(lecture_id))
    if lecture is None:
        return []
    # 仕様: docs/spec/subtitle-formatting.md#受入基準 (AC11, AC13)
    # 整形済み(同じディレクトリの subtitles.display.srt)が読めて1件以上あれば優先、なければ元の SRT
    srt_path = Path(lecture.srt_path)
    segments: list[dict] = []
    try:
        segments = parse_srt_file(srt_path.with_name("subtitles.display.srt"))
    except (OSError, ValueError):
        segments = []
    if not segments:
        try:
            segments = parse_srt_file(srt_path)
        except (OSError, ValueError):
            return []
    return [
        {"start": s["start_sec"], "end": s["end_sec"], "text": s["text"]}
        for s in segments
    ]


SELECT_LECTURE_PATH = "/select-lecture"
_CONFIRM_LECTURE_PATH = "/select-lecture/confirm"


def _json_error(error: str, status: int) -> Response:
    return Response(json.dumps({"error": error}), status=status, mimetype="application/json")


def _reject_foreign_claim(claimed: object) -> Response | None:
    """送られた participant_id が本人と異なる/不正な型なら、DB・LLM の前に 403/400 を返す。"""
    status = resolve_claimed_participant_id(claimed, current_participant_id())
    if status is None:
        return None
    return _json_error("forbidden" if status == 403 else "invalid_participant_id", status)


def _selected_lecture_id() -> str | None:
    """ログインした協力者が選んだ講義(保存された選択)。未選択なら None。"""
    selected = build_select_lecture_use_case(g.learning_conn).find_selected(
        LearnerId(current_participant_id())
    )
    return None if selected is None else str(selected)


def _guard_lecture(claimed: object) -> tuple[str | None, Response | None]:
    """参加者の API の講義を、保存された選択で決める。

    検査の順序(仕様 What 4節。participant_id の検査は呼び出し側が先に行う):
    未選択 409 → 値の形 400 → 選択との不一致 403。
    """
    selected = _selected_lecture_id()
    if selected is None:
        return None, _json_error("lecture_not_selected", 409)
    if claimed is None:
        return selected, None
    if isinstance(claimed, bool) or not isinstance(claimed, (str, int, float)) or claimed == "":
        return None, _json_error("invalid_lecture_id", 400)
    if str(claimed) != selected:
        return None, _json_error("forbidden", 403)
    return selected, None


def _own_payload(payload: object) -> tuple[object, Response | None]:
    """本文の participant_id と lecture_id を検査し、ログインした ID と選択した講義を入れた本文を返す。

    本文が JSON オブジェクトでないときは、そのまま Controller の検証に任せる(未選択は 409)。
    """
    if not isinstance(payload, dict):
        _, rejection = _guard_lecture(None)
        return payload, rejection
    rejection = _reject_foreign_claim(payload.get("participant_id"))
    if rejection is not None:
        return payload, rejection
    selected, rejection = _guard_lecture(payload.get("lecture_id"))
    if rejection is not None:
        return payload, rejection
    return {
        **payload,
        "participant_id": current_participant_id(),
        "lecture_id": selected,
    }, None


def create_app(*, clock: Callable[[], datetime] | None = None) -> Flask:
    """Flask アプリを生成し、Composition Root 経由でルートを登録する。

    SECRET_KEY・参加者の設定ファイルに不備があれば、DB を開く前に例外で止まる。
    """
    clock = clock or (lambda: datetime.now(timezone.utc))
    secret_key = load_secret_key()
    credentials = load_credentials_file(os.environ.get(PARTICIPANT_CREDENTIALS_FILE_ENV))
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
    app.config["SECRET_KEY"] = secret_key

    # http の判定は最初(認証・DB の前)。仕様: docs/spec/https-enforcement.md
    register_https_enforcement(app)
    # 研究者の認証・参加者のログインは DB 接続の before_request より前(未認証なら DB を開かない)
    register_research_auth(app)
    register_participant_auth(app, credentials=credentials, clock=clock)

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
        """ルート: 選択済みなら /lecture へ、未選択なら選択の画面へ(未ログインは認証層がログイン画面へ)。"""
        if _selected_lecture_id() is None:
            return redirect(SELECT_LECTURE_PATH, 302)
        return redirect(DEFAULT_AFTER_LOGIN_PATH, 302)

    @app.route(SELECT_LECTURE_PATH, methods=["GET", "POST"])
    def select_lecture():
        """GET: 選択の画面(題名と系統をカタログの順に)。POST: 最初の操作(確認の画面。保存しない)。

        仕様: docs/spec/lecture-selection.md#2-選択の画面と導線
        """
        if _selected_lecture_id() is not None:
            return redirect(DEFAULT_AFTER_LOGIN_PATH, 302)
        if request.method == "GET":
            return render_template(
                "select_lecture.html",
                lectures=_STATIC_LECTURE_CATALOG.list_all(),
                participant_id=current_participant_id(),
            )
        raw = request.form.get("lecture_id", "").strip()
        chosen = _STATIC_LECTURE_CATALOG.find_by_id(LectureId(raw)) if raw else None
        if chosen is None:
            return Response("lecture not found", status=400, mimetype="text/plain")
        return render_template("select_lecture_confirm.html", lecture=chosen)

    @app.route(_CONFIRM_LECTURE_PATH, methods=["POST"])
    def confirm_lecture():
        """POST: 選択の確定。保存済みの選択は変えない(二重送信・別の講義の送信は最初の講義へ)。

        仕様: docs/spec/lecture-selection.md#3-選択の保存と固定fr-63
        """
        raw = request.form.get("lecture_id", "").strip()
        if not raw:
            return Response("lecture_id is required", status=400, mimetype="text/plain")
        use_case = build_select_lecture_use_case(g.learning_conn)
        learner_id = LearnerId(current_participant_id())
        try:
            result = use_case.execute(learner_id, LectureId(raw), datetime.now(timezone.utc))
        except sqlite3.IntegrityError:
            # 同時の確定で一意制約に当たった: 先に保存された選択に従う(増やさない)
            result = None
        if result is not None and result.is_err:
            return Response("lecture not found", status=400, mimetype="text/plain")
        return redirect(DEFAULT_AFTER_LOGIN_PATH, 302)

    @app.route("/reflect")
    def reflect():
        """GET /reflect: LAD + AI 振り返り統合画面(ログインした本人の画面。クエリの participant_id は無視)。"""
        # 仕様: docs/spec/lecture-selection.md#4-講義-id-の一貫fr-62(DR-001・DR-003)
        selected = _selected_lecture_id()
        if selected is None:
            return redirect(SELECT_LECTURE_PATH, 302)
        lecture_id = request.args.get("lecture_id")
        if lecture_id == "":
            return Response("lecture not found", status=404, mimetype="text/plain")
        if lecture_id is not None and lecture_id != selected:
            return Response("forbidden", status=403, mimetype="text/plain")
        return render_template(
            "reflect.html",
            participant_id=current_participant_id(),
            lecture_id=selected,
            **_REFLECT_FIXED_TEXT,
        )

    @app.route("/lecture")
    def lecture():
        """GET /lecture: 選択した講義の動画ページ(クエリの participant_id・選択と異なる lecture_id は無視)。"""
        # 仕様: docs/spec/lecture-selection.md#4-講義-id-の一貫fr-62(Q3・DR-003)
        participant_id = current_participant_id()
        selected = _selected_lecture_id()
        if selected is None:
            return redirect(SELECT_LECTURE_PATH, 302)
        try:
            if request.args.get("lecture_id") == "":
                raise ValueError("lecture_id must not be empty")
            lecture_id, youtube_video_id = _resolve_youtube_video_id_for_participant(
                participant_id,
                lecture_id=selected,
            )
            quiz_context = _quiz_template_context(lecture_id)
        except ValueError as exc:
            return (
                render_template(
                    "lecture.html",
                    participant_id=participant_id,
                    lecture_id="",
                    youtube_video_id="",
                    lecture_error=str(exc),
                ),
                404,
            )
        return render_template(
            "lecture.html",
            participant_id=participant_id,
            lecture_id=lecture_id,
            youtube_video_id=youtube_video_id,
            lecture_error="",
            subtitle_cues=_subtitle_cues_for_lecture(lecture_id),
            **quiz_context,
        )

    @app.route("/chat", methods=["POST"])
    def chat():
        """POST /chat: SendChatMessageController 経由で AI 応答を返す。"""
        data, rejection = _own_payload(request.get_json(silent=True) or {})
        if rejection is not None:
            return rejection
        controller = build_send_chat_message_controller(
            learning_connection=g.learning_conn,
            tutor_connection=g.tutor_conn,
        )
        result = controller.execute(data, sent_at=datetime.now(timezone.utc))
        if isinstance(result, ErrorViewModel) and result.error_code == _TUTOR_SESSION_NOT_FOUND_CODE:
            # 他人のセッションと存在しないセッションを、応答からも区別させない(ID を本文に写さない)
            result = replace(result, message="tutor session not found")
        return controller_result_to_flask_response(result)

    @app.route("/api/dialog-log", methods=["POST"])
    def api_dialog_log():
        """POST /api/dialog-log: 対話ログを保存する(仕様: dialog-log-save.md#保存-API)。"""
        data, rejection = _own_payload(request.get_json(silent=True))
        if rejection is not None:
            return rejection
        controller = build_save_dialog_log_controller(
            learning_connection=g.learning_conn,
            tutor_connection=g.tutor_conn,
        )
        result = controller.execute(
            data, received_at=datetime.now(timezone.utc)
        )
        return controller_result_to_flask_response(result)

    @app.route("/api/quiz-attempts", methods=["POST"])
    def api_quiz_attempts():
        """POST /api/quiz-attempts: 小テスト 1 試行を記録する。"""
        data, rejection = _own_payload(request.get_json(silent=True) or {})
        if rejection is not None:
            return rejection
        controller = build_record_quiz_attempt_controller(g.learning_conn)
        result = controller.execute(data)
        return controller_result_to_flask_response(result)

    @app.route("/api/viewing-log", methods=["POST"])
    def api_viewing_log():
        """POST /api/viewing-log: 視聴ログ 1 件を記録する。"""
        data, rejection = _own_payload(request.get_json(silent=True) or {})
        if rejection is not None:
            return rejection
        controller = build_record_viewing_event_controller(g.learning_conn)
        result = controller.execute(data)
        return controller_result_to_flask_response(result)

    @app.route("/api/last-updated", methods=["GET"])
    def api_last_updated():
        """GET /api/last-updated: 学習データの最終更新時刻を返す。"""
        rejection = _reject_foreign_claim(request.args.get("participant_id"))
        if rejection is not None:
            return rejection
        participant_id = current_participant_id()
        lecture_id, rejection = _guard_lecture(request.args.get("lecture_id"))
        if rejection is not None:
            return rejection
        controller = build_get_last_updated_controller(g.learning_conn)
        result = controller.execute(participant_id, lecture_id=lecture_id)
        return controller_result_to_flask_response(result)

    @app.route("/api/participants/<participant_id>/lad", methods=["GET"])
    def api_participants_lad(participant_id: str):
        """GET /api/participants/<participant_id>/lad: LAD ViewModel を返す。"""
        rejection = _reject_foreign_claim(participant_id)
        if rejection is not None:
            return rejection
        participant_id = current_participant_id()
        lecture_id, rejection = _guard_lecture(request.args.get("lecture_id"))
        if rejection is not None:
            return rejection
        controller = build_get_learning_snapshot_controller(g.learning_conn)
        result = controller.execute(participant_id, lecture_id=lecture_id)
        return controller_result_to_flask_response(result)

    def _research_response(execute):
        """研究用の応答。予期しない例外・エラーは本文や値を出さない固定の応答にする(R9)。"""
        try:
            controller = build_export_dialog_logs_controller(
                learning_connection=g.learning_conn,
                tutor_connection=g.tutor_conn,
            )
            result = execute(controller)
            if isinstance(result, ErrorViewModel):
                return Response("Error", status=http_status_for_error(result), mimetype="text/plain")
            return controller_result_to_flask_response(result)
        except Exception:  # noqa: BLE001 - 例外の文言に本文が入りうるため記録しない
            return Response("Internal Server Error", status=500, mimetype="text/plain")

    @app.route("/research/participants/<participant_id>/dialog-logs", methods=["GET"])
    def research_participant_dialog_logs(participant_id: str):
        """GET: 参加者別の対話ログ(仕様: research-dialog-download.md)。"""
        return _research_response(lambda c: c.execute_for_participant(participant_id))

    @app.route("/research/dialog-logs", methods=["GET"])
    def research_all_dialog_logs():
        """GET: 全参加者一括の対話ログ(仕様: research-dialog-download.md)。"""
        return _research_response(lambda c: c.execute_all())

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
