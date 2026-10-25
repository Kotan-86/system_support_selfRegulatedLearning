"""
整形済みの表示用字幕(subtitles.display.srt)があっても、AI チューターのプロンプトに入る字幕は
元の SRT 由来で、整形済みファイルの文を含まない。

仕様: docs/spec/subtitle-formatting.md#受入基準 AC14
既存の test_srt_in_prompt.py は変更しない。整形済みファイルは一時ディレクトリで再現する
(本物の整形済みファイルの有無に依らない)。
"""
from dataclasses import replace
from pathlib import Path

from framework_drivers.db.learning.static_lecture_catalog import (
    StaticLectureCatalog,
    build_near_term_lectures,
)
from interfaces.tutoring.srt import get_segments_for_times, parse_srt_file

ROOT = Path(__file__).resolve().parent.parent.parent
MARKER = "表示専用の目印文ZZZ"


def _viewing_log_payload(current_time: int = 15):
    return {
        "participant_id": "1",
        "time_stamp": "2026-02-23T11:18:42",
        "current_time": current_time,
        "action": "play",
        "duration": 0.0,
    }


def test_ac14_prompt_uses_original_srt_not_display_file(
    chat_lad_client, fake_llm_gateway, monkeypatch, tmp_path: Path
) -> None:
    """AC14: 整形済みファイルがある講義でも、プロンプトの字幕は元の SRT から作ったものと一致し、
    整形済みファイルの文を含まない。"""
    # 仕様: docs/spec/subtitle-formatting.md#受入基準 AC14
    real_srt = ROOT / "lectures" / "lecture-1" / "subtitles.srt"
    lec_dir = tmp_path / "lec"
    lec_dir.mkdir()
    # 一時ディレクトリの SRT が使われていることを示す目印(QQQ)を、実データの文に足しておく
    tmp_srt = lec_dir / "subtitles.srt"
    tmp_srt.write_bytes(real_srt.read_bytes().replace("整数倍".encode(), "整数倍QQQ".encode()))
    # 全時間帯を覆う整形済みファイル(元の SRT の文は1つも含まない)
    (lec_dir / "subtitles.display.srt").write_bytes(
        f"1\r\n00:00:00,000 --> 00:30:00,000\r\n{MARKER}".encode("utf-8")
    )
    lectures = tuple(
        replace(lec, srt_path=str(lec_dir / "subtitles.srt")) if str(lec.id) == "lecture-1" else lec
        for lec in build_near_term_lectures()
    )
    monkeypatch.setattr(
        "framework_drivers.platform.wiring._lecture_catalog",
        lambda: StaticLectureCatalog(lectures),
    )

    chat_lad_client.post(
        "/api/viewing-log", json=_viewing_log_payload(15), content_type="application/json"
    )
    fake_llm_gateway.generate_calls.clear()
    r = chat_lad_client.post(
        "/chat",
        json={"message": "このあたりの説明がわかりません", "participant_id": "1"},
        content_type="application/json",
    )
    assert r.status_code == 200
    prompt = fake_llm_gateway.generate_calls[-1]

    expected = get_segments_for_times(parse_srt_file(tmp_srt), [15])
    assert expected, "前提: 元の SRT の 15 秒付近に字幕がある"
    assert expected in prompt, "プロンプトの字幕は元の SRT から作ったものと一致する"
    assert "整数倍QQQ" in prompt, "一時ディレクトリの元の SRT が使われている(前提)"
    assert MARKER not in prompt, "整形済みファイルの文がプロンプトに入っている"
