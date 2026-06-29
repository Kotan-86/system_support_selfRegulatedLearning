"""
POST /chat でプロンプトに講義字幕（SRT 参照）が含まれることを検証する。

視聴ログに current_time が登録されているとき、その位置に対応する SRT のテキストが
プロンプトの「講義字幕」として LLM に渡されることを確認する。
"""
from pathlib import Path

import pytest


def _viewing_log_payload(current_time: int = 15):
    """current_time 秒地点を視聴したログ（lecture-1 SRT の 15 秒付近は「整数倍」等）。"""
    return {
        "participant_id": "1",
        "time_stamp": "2026-02-23T11:18:42",
        "current_time": current_time,
        "action": "play",
        "duration": 0.0,
    }


class TestSrtInPrompt:
    """チャット時に講義字幕（SRT）がプロンプトに含まれる。"""

    def test_prompt_includes_lecture_transcript_section_when_srt_configured(
        self, chat_lad_client, fake_llm_gateway
    ) -> None:
        """
        視聴ログを current_time=15 で登録したのち POST /chat すると、
        渡されたプロンプトに「講義字幕」セクションと、その位置の字幕テキストが含まれる。
        participant_id=1 は lecture-1 に解決され、カタログの SRT パスが使われる。
        """

        root = Path(__file__).resolve().parent.parent.parent
        srt_path = root / "lectures" / "lecture-1" / "subtitles.srt"
        if not srt_path.is_file():
            pytest.skip("lectures/lecture-1/subtitles.srt が存在しないためスキップ")

        client = chat_lad_client
        client.post(
            "/api/viewing-log",
            json=_viewing_log_payload(15),
            content_type="application/json",
        )

        fake_llm_gateway.generate_calls.clear()
        r = client.post(
            "/chat",
            json={"message": "このあたりの説明がわかりません", "participant_id": "1"},
            content_type="application/json",
        )

        assert r.status_code == 200
        assert len(fake_llm_gateway.generate_calls) >= 1
        prompt = fake_llm_gateway.generate_calls[-1]

        assert "講義字幕" in prompt or "lecture_transcript" in prompt, (
            "プロンプトに講義字幕（lecture_transcript）のセクションが含まれること"
        )
        assert "整数倍" in prompt, (
            "プロンプトに視聴箇所に対応する講義字幕のテキストが含まれること"
        )
