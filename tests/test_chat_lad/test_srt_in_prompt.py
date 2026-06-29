"""
POST /chat でプロンプトに講義字幕（SRT 参照）が含まれることを検証する。

視聴ログに current_time が登録されているとき、その位置に対応する SRT のテキストが
プロンプトの「講義字幕」として LLM に渡されることを確認する。
"""
from pathlib import Path

import pytest


def _viewing_log_payload(current_time: int = 15):
    """current_time 秒地点を視聴したログ（demoLectureVideoSub.srt の 15 秒付近は「線形代数」「ベクトル」等）。"""
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
        self, chat_lad_client, fake_llm_gateway, monkeypatch
    ) -> None:
        """
        視聴ログを current_time=15 で登録したのち POST /chat すると、
        渡されたプロンプトに「講義字幕」セクションと、その位置の字幕テキスト（例: 線形代数・ベクトル）が含まれる。
        """
        if chat_lad_client is None:
            pytest.skip("app.main が未実装のためスキップ")

        root = Path(__file__).resolve().parent.parent.parent
        srt_path = root / "demoLectureVideoSub.srt"
        if not srt_path.exists():
            pytest.skip("demoLectureVideoSub.srt が存在しないためスキップ")

        monkeypatch.setenv("LECTURE_SRT_PATH", str(srt_path))

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
        assert "線形代数" in prompt or "ベクトル" in prompt, (
            "プロンプトに視聴箇所に対応する講義字幕のテキストが含まれること"
        )
