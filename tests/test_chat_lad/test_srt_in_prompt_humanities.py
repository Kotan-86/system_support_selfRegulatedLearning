"""
POST /chat に講義ID(lecture-4〜6)を指定したとき、その講義の字幕と講義情報がプロンプトに入る。

仕様: docs/spec/humanities-lectures.md#受入基準 AC11
  講義IDに lecture-N を指定して視聴ログ(再生位置 15 秒)を送り、続けて同じ講義IDで /chat を送ると、
  プロンプトに lecture-N の字幕のその位置の文と、lecture-N の講義情報の章の題が含まれ、
  lecture-1 の字幕のその位置の文は含まれない。LLM は Fake。
期待する字幕の文は、subtitles.srt を parse_srt_file で読んで、その位置を含む最初のキューから求める。
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from interfaces.tutoring.srt import parse_srt_file
from tests.login_helpers import login_as
from tests.test_lectures.humanities_data import HUMANITIES_IDS

ROOT = Path(__file__).resolve().parent.parent.parent
POSITION_SEC = 15


def _cue_text_at(lecture_id: str, position: float) -> str:
    """位置を含む最初のキュー、なければ位置以降で始まる最初のキューの文。"""
    path = ROOT / "lectures" / lecture_id / "subtitles.srt"
    assert path.is_file(), f"{path} が無い"
    segments = parse_srt_file(path)
    for seg in segments:
        if seg["start_sec"] <= position <= seg["end_sec"]:
            return seg["text"].strip()
    for seg in segments:
        if seg["start_sec"] >= position:
            return seg["text"].strip()
    raise AssertionError("位置に対応するキューが無い")


def _outline_titles(lecture_id: str) -> list[str]:
    number = lecture_id.split("-")[1]
    module = importlib.import_module(
        f"framework_drivers.db.learning.lecture_outlines.lecture_{number}"
    )
    return [section.title for section in module.build_lecture_outline().sections]


@pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
def test_ac11_prompt_has_the_lectures_subtitle_and_outline_not_lecture_1(
    chat_lad_client, fake_llm_gateway, lecture_id: str
) -> None:
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC11
    own_text = _cue_text_at(lecture_id, POSITION_SEC)
    lecture_1_text = _cue_text_at("lecture-1", POSITION_SEC)
    assert own_text and own_text != lecture_1_text  # 前提: 区別できる文であること

    client = chat_lad_client
    # 講義は選択で決まる(#34): 別の参加者 P01 が lecture_id の講義を選んだ状態にする("1" は lecture-1 を選択済み)
    login_as(client, "P01", lecture=lecture_id)
    r = client.post(
        "/api/viewing-log",
        json={
            "participant_id": "P01",
            "lecture_id": lecture_id,
            "time_stamp": "2026-10-26T11:18:42",
            "current_time": POSITION_SEC,
            "action": "play",
            "duration": 0.0,
        },
    )
    assert r.status_code == 201

    fake_llm_gateway.generate_calls.clear()
    r = client.post(
        "/chat",
        json={"message": "このあたりの説明がわかりません", "participant_id": "P01", "lecture_id": lecture_id},
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    assert fake_llm_gateway.generate_calls
    prompt = fake_llm_gateway.generate_calls[-1]

    assert own_text in prompt, "その講義の字幕のその位置の文がプロンプトにない"
    assert lecture_1_text not in prompt, "lecture-1 の字幕がプロンプトに入っている"
    titles = _outline_titles(lecture_id)
    assert titles
    for title in titles:
        assert title in prompt, f"講義情報の章の題 {title!r} がプロンプトにない"
