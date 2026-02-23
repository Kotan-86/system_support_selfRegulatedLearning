"""
LLM チューター用 Flask アプリ。
対話履歴は db パッケージで永続化し、プロンプトに組み込む。
"""
import os

from flask import Flask, request, jsonify, render_template
from tenacity import retry, stop_after_attempt, wait_exponential

from app.prompts import SYSTEM_PROMPT
from db import repository

app = Flask(__name__)
app.config["SECRET_KEY"] = "tutor_secret_key"

HISTORY_LIMIT = 20

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


@app.route("/")
def index():
    """ルート: チャット画面の HTML を返す。"""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """POST /chat: message を受け取り JSON で応答を返す。session_id が無ければ新規作成し、履歴をプロンプトに含める。"""
    data = request.get_json(silent=True) or {}
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "メッセージがありません"}), 400

    session_id = data.get("session_id")
    if not session_id:
        session_id = repository.create_session()

    history = repository.get_history(session_id, limit=HISTORY_LIMIT)
    history_str = _format_history(history)
    prompt = SYSTEM_PROMPT.format(
        history=history_str or "(履歴なし)",
        user_message=user_message,
        lecture_log="",
        quiz_result="",
    )

    bot_response = _call_llm(prompt)

    repository.add_message(session_id, "user", user_message)
    repository.add_message(session_id, "assistant", bot_response)

    return jsonify({"response": bot_response, "session_id": session_id})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
