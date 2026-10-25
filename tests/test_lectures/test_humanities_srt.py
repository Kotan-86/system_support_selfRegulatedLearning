"""
lecture-4〜6(文系)の字幕 subtitles.srt の構造と同一性。

仕様: docs/spec/humanities-lectures.md#受入基準 AC2・AC8
  AC8: (a) バイト数と SHA-256 が前提の表の値と一致 (b) BOM なし (c) 番号が 1 からの連番
       (d) 2 行目が時刻行 (e) 文が空でない (f) 開始時刻が減らない
       (g) parse_srt_file のセグメント数がブロック数と一致 (h) 最終の終了時刻
  校正前との比較(proofread)はしない。期待値は tests/test_lectures/humanities_data.py(仕様の表の値)。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from interfaces.tutoring.srt import parse_srt_file
from tests.test_lectures.humanities_data import HUMANITIES_BY_ID, HUMANITIES_IDS

ROOT = Path(__file__).resolve().parent.parent.parent
TIME_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})$")


def _srt_path(lecture_id: str) -> Path:
    return ROOT / "lectures" / lecture_id / "subtitles.srt"


def _read(lecture_id: str) -> bytes:
    path = _srt_path(lecture_id)
    assert path.is_file(), f"{path} が無い(AC2・AC8)"
    return path.read_bytes()


def _blocks(data: bytes) -> list[list[str]]:
    """空行で区切ったブロック。改行は CRLF と LF の両方を区切りとして扱う。"""
    text = data.decode("utf-8")
    blocks: list[list[str]] = [[]]
    for line in re.split(r"\r\n|\n", text):
        if line == "":
            if blocks[-1]:
                blocks.append([])
        else:
            blocks[-1].append(line)
    if not blocks[-1]:
        blocks.pop()
    return blocks


def _sec(m: tuple[str, ...]) -> tuple[float, float]:
    h1, m1, s1, ms1, h2, m2, s2, ms2 = (int(x) for x in m)
    return h1 * 3600 + m1 * 60 + s1 + ms1 / 1000, h2 * 3600 + m2 * 60 + s2 + ms2 / 1000


@pytest.mark.parametrize("lecture_id", HUMANITIES_IDS)
class TestHumanitiesSrt:
    def test_ac2_file_exists(self, lecture_id: str) -> None:
        # 仕様: humanities-lectures.md#受入基準 AC2
        assert _srt_path(lecture_id).is_file()

    def test_ac8a_bytes_and_sha256_match_received_file(self, lecture_id: str) -> None:
        # 仕様: humanities-lectures.md#受入基準 AC8(a)
        data = _read(lecture_id)
        exp = HUMANITIES_BY_ID[lecture_id]
        assert len(data) == exp.srt_bytes
        assert hashlib.sha256(data).hexdigest() == exp.srt_sha256

    def test_ac8b_no_bom(self, lecture_id: str) -> None:
        # 仕様: humanities-lectures.md#受入基準 AC8(b)
        assert not _read(lecture_id).startswith(b"\xef\xbb\xbf")

    def test_ac8c_to_f_block_structure(self, lecture_id: str) -> None:
        # 仕様: humanities-lectures.md#受入基準 AC8(c)(d)(e)(f)
        blocks = _blocks(_read(lecture_id))
        assert len(blocks) == HUMANITIES_BY_ID[lecture_id].srt_blocks
        prev_start = -1.0
        for expected_no, block in enumerate(blocks, 1):
            assert len(block) >= 3, f"ブロック{expected_no}: 番号・時刻・文の3行以上が要る {block!r}"
            assert block[0].strip() == str(expected_no), f"(c) 番号が連番でない: {block[0]!r}"
            m = TIME_RE.match(block[1])
            assert m, f"(d) ブロック{expected_no}: 時刻行の形式が違う {block[1]!r}"
            assert "".join(block[2:]).strip() != "", f"(e) ブロック{expected_no}: 文が空"
            start, _end = _sec(m.groups())
            assert start >= prev_start, f"(f) ブロック{expected_no}: 開始時刻が減っている"
            prev_start = start

    def test_ac8g_h_parse_srt_file_segments_and_last_end(self, lecture_id: str) -> None:
        # 仕様: humanities-lectures.md#受入基準 AC8(g)(h)
        _read(lecture_id)
        exp = HUMANITIES_BY_ID[lecture_id]
        segments = parse_srt_file(_srt_path(lecture_id))
        assert len(segments) == exp.srt_blocks
        assert segments[-1]["end_sec"] == pytest.approx(exp.srt_last_end_sec, abs=1e-6)


def test_ac7_no_display_srt_is_placed_for_humanities_lectures() -> None:
    """AC4(実現内容4)・AC7: 表示用の整形済み字幕は置かない(画面は subtitles.srt で表示する)。"""
    # 仕様: humanities-lectures.md#受入基準 AC7
    for lecture_id in HUMANITIES_IDS:
        assert _srt_path(lecture_id).is_file()  # subtitles.srt は在る
        assert not (_srt_path(lecture_id).parent / "subtitles.display.srt").exists()
