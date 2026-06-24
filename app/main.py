"""
LLM チューター用 Flask アプリ。
対話履歴は db パッケージで永続化し、プロンプトに組み込む。
"""
import os
import re
from pathlib import Path

from flask import Flask, request, jsonify, render_template
from tenacity import retry, stop_after_attempt, wait_exponential

from app.prompts import SYSTEM_PROMPT
from app.srt import get_segments_for_times, parse_srt_file
from application.common.viewing_seconds import parse_position_delta, parse_video_position
from db import init_db, repository
from db import learning_repository as learning_repo

app = Flask(__name__)
app.config["SECRET_KEY"] = "tutor_secret_key"

HISTORY_LIMIT = 20

# 初回メッセージが半角数字のみ（学習者ID）のときの定型文（LLM を呼ばない）
FIRST_MESSAGE_CANNED_RESPONSE = (
    "学習者IDを確認しました。学習で気になったことや質問があれば、いつでも送ってください。"
)

# Vertex AI: 遅延初期化用
_vertex_model = None


def _get_vertex_model():
    """Vertex AI モデルを遅延初期化して返す。"""
    global _vertex_model
    if _vertex_model is not None:
        return _vertex_model
    import vertexai
    from vertexai.generative_models import GenerativeModel

    project_id = os.environ.get("VERTEX_PROJECT_ID", "flash-adapter-475404-q6")
    location = os.environ.get("VERTEX_LOCATION", "us-east4")
    vertexai.init(project=project_id, location=location)
    _vertex_model = GenerativeModel("gemini-2.5-flash")
    return _vertex_model


def _call_llm(prompt: str) -> str:
    """受け取った 1 本のプロンプトを LLM に送り、応答文字列を返す。テストでは patch 対象。"""
    model = _get_vertex_model()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _generate(prompt_text: str):
        return model.generate_content(prompt_text)

    response = _generate(prompt)
    text = response.text if response and response.text else ""
    return text or "（応答を取得できませんでした）"


def _format_history(history: list[dict]) -> str:
    """get_history の返り値をプロンプト用の文字列に整形する。"""
    lines = []
    for row in history:
        role = row.get("role", "")
        content = row.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _format_lecture_log(lad: dict) -> str:
    """LAD 辞書の viewing_logs を時系列で「時刻・action・current_time」など簡潔に列挙する。データが無い場合は "(なし)"。"""
    logs = lad.get("viewing_logs") or []
    if not logs:
        return "(なし)"
    lines = []
    for row in logs:
        ts = row.get("time_stamp", "")
        action = row.get("action", "")
        current = row.get("current_time", "")
        duration = row.get("duration", "")
        lines.append(f"{ts} action={action} current_time={current} duration={duration}")
    return "\n".join(lines)


def _build_lecture_transcript(lad: dict) -> str:
    """LAD の viewing_logs の current_time に対応する SRT 字幕を抽出する。SRT 未設定・なしの場合は "(なし)"。"""
    srt_path_str = os.environ.get("LECTURE_SRT_PATH")
    if not srt_path_str:
        root = Path(__file__).resolve().parent.parent
        srt_path = root / "demoLectureVideoSub.srt"
    else:
        srt_path = Path(srt_path_str)
    if not srt_path.exists():
        return "(なし)"
    try:
        segments = parse_srt_file(srt_path)
    except (OSError, ValueError):
        return "(なし)"
    logs = lad.get("viewing_logs") or []
    times = [row["current_time"] for row in logs if row.get("current_time") is not None]
    text = get_segments_for_times(segments, times)
    return text if text else "(なし)"


def _format_quiz_result(lad: dict) -> str:
    """LAD 辞書の latest_quiz_attempt のスコアと quiz_answers の各問正誤を「問N: 正解/不正解」で列挙する。データが無い場合は "(なし)"。"""
    attempt = lad.get("latest_quiz_attempt")
    answers = lad.get("quiz_answers") or []
    if not attempt and not answers:
        return "(なし)"
    parts = []
    if attempt:
        num = attempt.get("score_numerator", "")
        den = attempt.get("score_denominator", "")
        parts.append(f"スコア: {num}/{den}")
    for a in answers:
        q = a.get("question_index", "?")
        ok = "正解" if a.get("is_correct") else "不正解"
        parts.append(f"問{q}: {ok}")
    return "\n".join(parts) if parts else "(なし)"


@app.route("/")
def index():
    """ルート: チャット画面の HTML を返す。"""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """POST /chat: message を受け取り JSON で応答を返す。session_id が無ければ participant_id 必須で新規作成し、履歴をプロンプトに含める。"""
    data = request.get_json(silent=True) or {}
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "メッセージがありません"}), 400

    session_id = data.get("session_id")
    if not session_id:
        participant_id = data.get("participant_id")
        if not participant_id:
            return jsonify({"error": "新規チャット時は participant_id が必須です"}), 400
        session_id = repository.create_session(participant_id)
    else:
        participant_id = repository.get_participant_id_for_session(session_id)
        if participant_id is None:
            return jsonify({"error": "セッションが見つかりません"}), 404

    history = repository.get_history(session_id, limit=HISTORY_LIMIT)

    # 履歴が空かつメッセージが半角数字のみのときは定型文を返し LLM を呼ばない
    if not history and re.match(r"^[0-9]+$", user_message.strip()):
        bot_response = FIRST_MESSAGE_CANNED_RESPONSE
        repository.add_message(session_id, "user", user_message)
        repository.add_message(session_id, "assistant", bot_response)
        return jsonify({"response": bot_response, "session_id": session_id})

    history_str = _format_history(history)
    init_db.init_learning_db()
    lad = learning_repo.get_lad_data_for_participant(participant_id)
    lecture_log_str = _format_lecture_log(lad)
    quiz_result_str = _format_quiz_result(lad)
    lecture_transcript_str = _build_lecture_transcript(lad)

    prompt = SYSTEM_PROMPT.format(
        history=history_str or "(履歴なし)",
        user_message=user_message,
        lecture_log=lecture_log_str,
        quiz_result=quiz_result_str,
        lecture_transcript=lecture_transcript_str,
    )

    bot_response = _call_llm(prompt)

    repository.add_message(session_id, "user", user_message)
    repository.add_message(session_id, "assistant", bot_response)

    return jsonify({"response": bot_response, "session_id": session_id})


@app.route("/api/quiz-attempts", methods=["POST"])
def api_quiz_attempts():
    """POST /api/quiz-attempts: 小テスト 1 試行を JSON で受け取り、学習データ用 DB に保存する。"""
    init_db.init_learning_db()
    data = request.get_json(silent=True) or {}
    participant_id = data.get("participant_id")
    created_at = data.get("timestamp") or data.get("created_at")
    score_numerator = data.get("score_numerator")
    score_denominator = data.get("score_denominator")
    answers = data.get("answers")

    if not participant_id:
        return jsonify({"error": "participant_id は必須です"}), 400
    if created_at is None:
        return jsonify({"error": "timestamp または created_at は必須です"}), 400
    if score_numerator is None or score_denominator is None:
        return jsonify({"error": "score_numerator と score_denominator は必須です"}), 400
    if not isinstance(answers, list):
        return jsonify({"error": "answers は配列である必要があります"}), 400

    try:
        attempt_id = learning_repo.insert_quiz_attempt(
            participant_id=str(participant_id),
            created_at=str(created_at),
            score_numerator=int(score_numerator),
            score_denominator=int(score_denominator),
            answers=answers,
        )
        return jsonify({"attempt_id": attempt_id}), 201
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": f"不正なデータ: {e!s}"}), 400


@app.route("/api/viewing-log", methods=["POST"])
def api_viewing_log():
    """POST /api/viewing-log: 視聴ログ 1 件を JSON で受け取り、学習データ用 DB に保存する。"""
    init_db.init_learning_db()
    data = request.get_json(silent=True) or {}
    participant_id = data.get("participant_id")
    time_stamp = data.get("time_stamp")
    current_time = data.get("current_time")
    action = data.get("action")
    duration = data.get("duration")

    if not participant_id:
        return jsonify({"error": "participant_id は必須です"}), 400
    if time_stamp is None:
        return jsonify({"error": "time_stamp は必須です"}), 400
    if current_time is None:
        return jsonify({"error": "current_time は必須です"}), 400
    if not action:
        return jsonify({"error": "action は必須です"}), 400
    if duration is None:
        return jsonify({"error": "duration は必須です"}), 400

    parsed_current_time = parse_video_position(current_time)
    if parsed_current_time.is_err:
        return jsonify({"error": parsed_current_time.error.message}), 400
    parsed_duration = parse_position_delta(duration)
    if parsed_duration.is_err:
        return jsonify({"error": parsed_duration.error.message}), 400

    try:
        learning_repo.insert_viewing_log(
            participant_id=str(participant_id),
            time_stamp=str(time_stamp),
            current_time=parsed_current_time.value,
            action=str(action),
            duration=parsed_duration.value,
        )
        return "", 201
    except (TypeError, ValueError) as e:
        return jsonify({"error": f"不正なデータ: {e!s}"}), 400


@app.route("/api/last-updated", methods=["GET"])
def api_last_updated():
    """GET /api/last-updated: 学習データ用 DB の視聴ログ・小テストの最終更新時刻を返す。"""
    init_db.init_learning_db()
    last = learning_repo.get_last_updated()
    return jsonify({"last_updated": last}), 200


@app.route("/api/participants/<participant_id>/lad", methods=["GET"])
def api_participants_lad(participant_id: str):
    """GET /api/participants/<participant_id>/lad: 指定参加者の LAD 用データ（視聴ログ・最新小テスト結果）を返す。"""
    init_db.init_learning_db()
    data = learning_repo.get_lad_data_for_participant(participant_id)
    return jsonify(data), 200


# 起動時に対話用 DB（tutor.db）を 1 回だけ初期化（sessions / messages を作成）
init_db.init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
