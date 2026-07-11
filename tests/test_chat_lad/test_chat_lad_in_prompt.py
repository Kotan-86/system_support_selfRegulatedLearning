"""
Phase 3 Step 3.2: POST /chat でプロンプトに学習データ（LAD）が含まれる

学習データを事前に登録した状態で POST /chat すると、
LLM に渡されるプロンプトに lecture_log / quiz_result が含まれることを検証する。
"""
import pytest


def _viewing_log_payload():
    return {
        "participant_id": "1",
        "time_stamp": "2026-02-23T11:18:42",
        "current_time": 0,
        "action": "play",
        "duration": 0.0,
    }


def _quiz_attempt_payload():
    return {
        "participant_id": "1",
        "timestamp": "2026-02-23T12:00:00",
        "score_numerator": 4,
        "score_denominator": 5,
        "answers": [
            {"question_index": 1, "selected_answer": "A", "is_correct": 1},
            {"question_index": 2, "selected_answer": "B", "is_correct": 0},
        ],
    }


class TestChatLadInPrompt:
    """既存セッションでチャットすると、その参加者の LAD がプロンプトに含まれる。"""

    def test_prompt_includes_lad_when_lad_data_exists(
        self, chat_lad_client, fake_llm_gateway
    ) -> None:
        """
        視聴ログ・小テストを登録したのち、その participant_id で POST /chat すると、
        渡されたプロンプトに学習データ（スコア 4/5 や視聴・小テストに相当する記述）が含まれる。
        """
        client = chat_lad_client
        client.post(
            "/api/viewing-log",
            json=_viewing_log_payload(),
            content_type="application/json",
        )
        client.post(
            "/api/quiz-attempts",
            json=_quiz_attempt_payload(),
            content_type="application/json",
        )
        fake_llm_gateway.generate_calls.clear()
        r = client.post(
            "/chat",
            json={"message": "小テストの問2がわかりません", "participant_id": "1"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert len(fake_llm_gateway.generate_calls) >= 1
        prompt = fake_llm_gateway.generate_calls[-1]
        assert (
            ("4" in prompt and "5" in prompt)
            or "視聴" in prompt
            or "小テスト" in prompt
            or "再生開始" in prompt
            or "視聴ログ要約" in prompt
        ), "プロンプトに学習データ（LAD）が含まれること"
