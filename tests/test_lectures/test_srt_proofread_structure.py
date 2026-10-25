"""
lecture-1〜3 の字幕(元 / 反映後の subtitles.srt と修正案 subtitles.proofread.srt)の構造検査。

元との照合はしない(Q6)。ファイル単体で確認できる条件だけを検査する。
修正案のファイルがないときは、修正案についてはスキップする。
講義ごとの期待値は LECTURES に置く(仕様の「前提」の観測値表)。
仕様: docs/spec/srt-proofreading.md#受入基準
  lecture-1: AC 2〜5、AC 16(継続の検査)
  lecture-2・3: AC 20〜23、AC 35(継続の検査)、AC 24(lecture-1 の検査を弱めない)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from interfaces.tutoring.srt import parse_srt_file

ROOT = Path(__file__).resolve().parent.parent.parent
TIME_RE = re.compile(r"^(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})$")
BRACKET_RE = re.compile(r"\[[^\]]*\]")


@dataclass(frozen=True)
class LectureSpec:
    lecture_id: str
    blocks: int
    lines: int
    last_end: str
    # 効果音: ブロック番号 -> テキスト。ファイル中の [...] 表記はこれだけ。
    sound_effects: dict[int, str]
    # AC の番号(テスト名・メッセージ用)
    ac_structure: str

    @property
    def dir(self) -> Path:
        return ROOT / "lectures" / self.lecture_id

    @property
    def srt_path(self) -> Path:
        return self.dir / "subtitles.srt"

    @property
    def proofread_path(self) -> Path:
        return self.dir / "subtitles.proofread.srt"


# 値の出典: 仕様「前提」(lecture-1: 295/1179/00:13:41,670、lecture-2・3 は観測値表)。
# 実ファイルでも確認済み(2026-10-26)。
LECTURES: dict[str, LectureSpec] = {
    "lecture-1": LectureSpec(
        "lecture-1", 295, 1179, "00:13:41,670",
        {1: "[音楽]", 24: "[音楽]", 190: "[音楽]"}, "AC2〜5",
    ),
    "lecture-2": LectureSpec(
        "lecture-2", 238, 951, "00:10:29,610",
        {238: "[音楽]"}, "AC20〜23",
    ),
    "lecture-3": LectureSpec(
        "lecture-3", 263, 1051, "00:13:40,079",
        {152: "[笑い]", 209: "[音楽]"}, "AC20〜23",
    ),
}


def _split_blocks(lines: list[str]) -> list[list[str]]:
    """空行で区切ったブロックのリスト。"""
    blocks: list[list[str]] = [[]]
    for line in lines:
        if line == "":
            blocks.append([])
        else:
            blocks[-1].append(line)
    return blocks


def check_ac2(data: bytes, spec: LectureSpec) -> list[str]:
    """ブロック数、連番、時刻の形式、最終終了時刻 (lecture-1: AC2 / lecture-2・3: AC20)。"""
    errors: list[str] = []
    lines = data.decode("utf-8", errors="replace").split("\r\n")
    blocks = _split_blocks(lines)
    if len(blocks) != spec.blocks:
        errors.append(f"ブロック数 {len(blocks)} != {spec.blocks}")
    numbers = [b[0] if b else "" for b in blocks]
    if numbers != [str(i) for i in range(1, spec.blocks + 1)]:
        errors.append(f"番号が 1〜{spec.blocks} の連番ではない")
    last_end = None
    for i, b in enumerate(blocks, 1):
        m = TIME_RE.match(b[1]) if len(b) > 1 else None
        if not m:
            errors.append(f"ブロック{i}: 時刻行の形式が不正")
        else:
            last_end = m.group(2)
    if last_end != spec.last_end:
        errors.append(f"最終終了時刻 {last_end} != {spec.last_end}")
    return errors


def check_ac3(data: bytes, spec: LectureSpec) -> list[str]:
    """3行構成、テキスト非空、物理行数 (lecture-1: AC3 / lecture-2・3: AC21)。"""
    errors: list[str] = []
    lines = data.decode("utf-8", errors="replace").split("\r\n")
    if len(lines) != spec.lines:
        errors.append(f"物理行数 {len(lines)} != {spec.lines}")
    for i, b in enumerate(_split_blocks(lines), 1):
        if len(b) != 3:
            errors.append(f"ブロック{i}: 行数 {len(b)} != 3")
        elif not b[2].strip():
            errors.append(f"ブロック{i}: テキストが空")
    return errors


def check_ac4(data: bytes, path: Path, spec: LectureSpec) -> list[str]:
    """UTF-8(BOMなし)、CRLF のみ、末尾改行なし、parse_srt_file のセグメント数
    (lecture-1: AC4 / lecture-2・3: AC22)。"""
    errors: list[str] = []
    if data.startswith(b"\xef\xbb\xbf"):
        errors.append("UTF-8 BOM がある")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        errors.append("UTF-8 としてデコードできない")
    if re.search(rb"(?<!\r)\n", data):
        errors.append("CR を伴わない LF がある")
    if re.search(rb"\r(?!\n)", data):
        errors.append("LF を伴わない CR がある")
    if data.endswith(b"\n") or data.endswith(b"\r"):
        errors.append("末尾に改行がある")
    try:
        n = len(parse_srt_file(path))
    except Exception as e:  # noqa: BLE001
        errors.append(f"parse_srt_file が失敗: {e!r}")
    else:
        if n != spec.blocks:
            errors.append(f"parse_srt_file のセグメント数 {n} != {spec.blocks}")
    return errors


def check_ac5(data: bytes, spec: LectureSpec) -> list[str]:
    """効果音の表記: [...] はこの講義の設定の位置とテキストのものだけ
    (lecture-1: AC5 / lecture-2・3: AC23)。"""
    errors: list[str] = []
    text = data.decode("utf-8", errors="replace")
    blocks = _split_blocks(text.split("\r\n"))
    found = BRACKET_RE.findall(text)
    if len(found) != len(spec.sound_effects):
        errors.append(f"[...] 表記が {len(found)} 個 (期待 {len(spec.sound_effects)})")
    for n, expected in sorted(spec.sound_effects.items()):
        t = blocks[n - 1][2] if len(blocks) >= n and len(blocks[n - 1]) > 2 else None
        if t != expected:
            errors.append(f"ブロック{n} のテキストが {expected} ではない: {t!r}")
    # 設定外のブロックに [...] 表記がない(別の位置への移動・追加を検出)
    for i, b in enumerate(blocks, 1):
        if i not in spec.sound_effects and any(BRACKET_RE.search(line) for line in b):
            errors.append(f"ブロック{i} に想定外の [...] 表記がある")
    return errors


def _targets():
    params = []
    for spec in LECTURES.values():
        params.append(pytest.param((spec, spec.srt_path), id=f"{spec.lecture_id}-subtitles.srt"))
        params.append(
            pytest.param((spec, spec.proofread_path), id=f"{spec.lecture_id}-subtitles.proofread.srt")
        )
    return params


@pytest.fixture(params=_targets())
def srt(request) -> tuple[LectureSpec, Path, bytes]:
    spec: LectureSpec = request.param[0]
    path: Path = request.param[1]
    if not path.is_file():
        pytest.skip(f"{spec.lecture_id}/{path.name} が存在しないためスキップ")
    return spec, path, path.read_bytes()


# 仕様: docs/spec/srt-proofreading.md#受入基準
class TestSrtStructure:
    def test_ac2_ac20_block_count_numbers_and_time_format(self, srt) -> None:
        """AC2(lecture-1)/AC20(lecture-2・3): ブロック数・連番・時刻形式・最終終了時刻。"""
        assert check_ac2(srt[2], srt[0]) == []

    def test_ac3_ac21_three_line_blocks_and_physical_lines(self, srt) -> None:
        """AC3(lecture-1)/AC21(lecture-2・3): 3行構成、テキスト非空、物理行数。"""
        assert check_ac3(srt[2], srt[0]) == []

    def test_ac4_ac22_encoding_newlines_and_parseable(self, srt) -> None:
        """AC4(lecture-1)/AC22(lecture-2・3): UTF-8・CRLF・末尾改行なし・parse_srt_file。"""
        assert check_ac4(srt[2], srt[1], srt[0]) == []

    def test_ac5_ac23_sound_effects_only_at_expected_blocks(self, srt) -> None:
        """AC5(lecture-1)/AC23(lecture-2・3): [...] 表記は講義ごとの位置とテキストだけ。"""
        assert check_ac5(srt[2], srt[0]) == []


class TestLecture1NotWeakened:
    """AC24: 3講義に広げた後も、lecture-1 の期待値は元の値のまま。"""

    def test_ac24_lecture1_expected_values_unchanged(self) -> None:
        s = LECTURES["lecture-1"]
        assert s.blocks == 295
        assert s.lines == 1179
        assert s.last_end == "00:13:41,670"
        assert s.sound_effects == {1: "[音楽]", 24: "[音楽]", 190: "[音楽]"}

    def test_ac24_lecture1_srt_is_checked_and_passes(self) -> None:
        s = LECTURES["lecture-1"]
        assert s.srt_path.is_file(), "lecture-1/subtitles.srt が存在する"
        data = s.srt_path.read_bytes()
        assert check_ac2(data, s) == []
        assert check_ac3(data, s) == []
        assert check_ac4(data, s.srt_path, s) == []
        assert check_ac5(data, s) == []

    def test_ac24_lecture_values_match_spec_table(self) -> None:
        """lecture-2・3 の期待値が仕様の観測値表と一致する。"""
        l2, l3 = LECTURES["lecture-2"], LECTURES["lecture-3"]
        assert (l2.blocks, l2.lines, l2.last_end) == (238, 951, "00:10:29,610")
        assert l2.sound_effects == {238: "[音楽]"}
        assert (l3.blocks, l3.lines, l3.last_end) == (263, 1051, "00:13:40,079")
        assert l3.sound_effects == {152: "[笑い]", 209: "[音楽]"}


# 検査関数自体の検査: 壊した入力で失敗する(proofread が無くても Red を観測できる)。
# AC24: 3講義のどれについても残る。
@pytest.fixture(params=list(LECTURES.values()), ids=list(LECTURES))
def lec(request) -> tuple[LectureSpec, bytes]:
    spec: LectureSpec = request.param
    if not spec.srt_path.is_file():
        pytest.skip(f"{spec.lecture_id}/subtitles.srt が存在しない")
    return spec, spec.srt_path.read_bytes()


def _write(tmp_path: Path, data: bytes) -> Path:
    p = tmp_path / "broken.srt"
    p.write_bytes(data)
    return p


class TestCheckersDetectBreakage:
    def test_ac2_detects_missing_block_and_bad_time(self, lec) -> None:
        spec, good = lec
        parts = good.split(b"\r\n\r\n")
        assert check_ac2(good, spec) == []
        assert check_ac2(b"\r\n\r\n".join(parts[:-1]), spec) != []
        assert check_ac2(good.replace(b" --> ", b" -> ", 1), spec) != []
        # 最終終了時刻が違う
        assert check_ac2(good.replace(spec.last_end.encode(), b"00:00:00,001"), spec) != []
        # 番号の欠番
        assert check_ac2(good.replace(b"\r\n\r\n2\r\n", b"\r\n\r\n3\r\n", 1), spec) != []

    def test_ac3_detects_two_line_text_and_empty_text(self, lec) -> None:
        spec, good = lec
        parts = good.split(b"\r\n\r\n")
        assert check_ac3(good, spec) == []
        two_line = parts[:]
        two_line[1] = two_line[1] + "\r\n追加行".encode()
        assert check_ac3(b"\r\n\r\n".join(two_line), spec) != []
        empty = parts[:]
        empty[1] = b"\r\n".join(empty[1].split(b"\r\n")[:2]) + b"\r\n"
        assert check_ac3(b"\r\n\r\n".join(empty), spec) != []

    def test_ac4_detects_bom_lf_cr_and_trailing_newline(self, lec, tmp_path) -> None:
        spec, good = lec
        assert check_ac4(good, _write(tmp_path, good), spec) == []
        for broken in (
            b"\xef\xbb\xbf" + good,
            good.replace(b"\r\n", b"\n"),
            good.replace(b"\r\n", b"\r", 1),
            good + b"\r\n",
        ):
            assert check_ac4(broken, _write(tmp_path, broken), spec) != []

    def test_ac4_detects_wrong_segment_count(self, lec, tmp_path) -> None:
        spec, good = lec
        parts = good.split(b"\r\n\r\n")
        broken = b"\r\n\r\n".join(parts[:-1])
        assert check_ac4(broken, _write(tmp_path, broken), spec) != []

    def test_ac5_detects_extra_missing_and_moved_sound_effect(self, lec) -> None:
        spec, good = lec
        assert check_ac5(good, spec) == []
        for expected in set(spec.sound_effects.values()):
            assert check_ac5(good.replace(expected.encode(), "[拍手]".encode(), 1), spec) != []
            assert check_ac5(good.replace(expected.encode(), "おんがく".encode(), 1), spec) != []
        # 効果音を 1 つ増やす(別ブロックのテキストを [音楽] にする)
        parts = good.split(b"\r\n\r\n")
        extra = parts[:]
        idx = 1 if 2 not in spec.sound_effects else 2
        lines = extra[idx].split(b"\r\n")
        lines[2] = "[音楽]".encode()
        extra[idx] = b"\r\n".join(lines)
        assert check_ac5(b"\r\n\r\n".join(extra), spec) != []

    def test_ac23_lecture3_laugh_must_stay_laugh(self) -> None:
        """lecture-3 の [笑い] を [音楽] にしても失敗する(講義別設定が効いている)。"""
        spec = LECTURES["lecture-3"]
        if not spec.srt_path.is_file():
            pytest.skip("lecture-3/subtitles.srt が存在しない")
        good = spec.srt_path.read_bytes()
        assert check_ac5(good.replace("[笑い]".encode(), "[音楽]".encode(), 1), spec) != []
        # lecture-1 の設定では lecture-3 の [笑い] は許されない(設定が混ざらない)
        assert check_ac5(good, LECTURES["lecture-1"]) != []
