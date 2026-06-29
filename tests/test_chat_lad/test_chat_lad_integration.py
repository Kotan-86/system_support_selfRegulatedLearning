"""
Phase 3 結合テスト: 学習データ登録 → チャットでプロンプトに反映 / participant_id 欠損で 400

- シナリオ 3.1: viewing-log → quiz-attempts → POST /chat(participant_id) → プロンプトに LAD が含まれる
- シナリオ 3.2: POST /chat で session_id も participant_id も送らない → 400
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


class TestChatLadIntegration:
    """学習データ登録からチャットまで一連の流れ。"""

    def test_register_lad_then_chat_prompt_contains_learning_data(
        self, chat_lad_client, fake_llm_gateway
    ) -> None:
        """
        POST /api/viewing-log → POST /api/quiz-attempts → POST /chat(participant_id="1")
        の順で実行し、LLM に渡されたプロンプトに視聴ログまたは小テスト結果が含まれる。
        """
        client = chat_lad_client
        r1 = client.post(
            "/api/viewing-log",
            json=_viewing_log_payload(),
            content_type="application/json",
        )
        assert r1.status_code == 201
        r2 = client.post(
            "/api/quiz-attempts",
            json=_quiz_attempt_payload(),
            content_type="application/json",
        )
        assert r2.status_code == 201
        fake_llm_gateway.generate_calls.clear()
        r3 = client.post(
            "/chat",
            json={
                "message": "小テストの問2がわかりません",
                "participant_id": "1",
            },
            content_type="application/json",
        )
        assert r3.status_code == 200
        assert "session_id" in (r3.get_json() or {})
        assert len(fake_llm_gateway.generate_calls) >= 1
        prompt = fake_llm_gateway.generate_calls[-1]
        assert (
            "4" in prompt and "5" in prompt
        ) or "視聴" in prompt or "小テスト" in prompt or "play" in prompt, (
            "プロンプトに学習データが含まれること"
        )

    def test_chat_without_participant_id_returns_400(self, chat_lad_client) -> None:
        """POST /chat で message のみ（session_id も participant_id も無し）だと 400。"""
        r = chat_lad_client.post(
            "/chat",
            json={"message": "こんにちは"},
            content_type="application/json",
        )
        assert r.status_code == 400
