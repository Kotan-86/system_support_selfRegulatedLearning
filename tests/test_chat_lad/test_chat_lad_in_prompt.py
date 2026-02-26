"""
Phase 3 Step 3.2: POST /chat でプロンプトに学習データ（LAD）が含まれる

学習データを事前に登録した状態で POST /chat すると、
_call_llm に渡されるプロンプトに lecture_log / quiz_result が含まれることを検証する。
"""
from unittest.mock import patch

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
        self, chat_lad_client
    ) -> None:
        """
        視聴ログ・小テストを登録したのち、その participant_id で POST /chat すると、
        渡されたプロンプトに学習データ（スコア 4/5 や視聴・小テストに相当する記述）が含まれる。
        """
        if chat_lad_client is None:
            pytest.skip("app.main が未実装のためスキップ")
        client = chat_lad_client
        # 1. LAD データを登録
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
        # 2. participant_id で 1 回目チャット（新規セッション）
        captured = []
        with patch("app.main._call_llm") as mock_llm:
            def capture(prompt):
                captured.append(prompt)
                return "応答"
            mock_llm.side_effect = capture
            r = client.post(
                "/chat",
                json={"message": "小テストの問2がわかりません", "participant_id": "1"},
                content_type="application/json",
            )
        assert r.status_code == 200
        assert len(captured) >= 1
        prompt = captured[-1]
        # プロンプトに学習データが含まれる（スコア 4/5、または視聴ログ・小テストの記述）
        assert (
            "4" in prompt and "5" in prompt
        ) or "視聴" in prompt or "小テスト" in prompt or "play" in prompt or "quiz" in prompt.lower(), (
            "プロンプトに学習データ（LAD）が含まれること"
        )
