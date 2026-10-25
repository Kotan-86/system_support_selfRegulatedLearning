"""
lecture-1〜3 の整形済みファイル(subtitles.display.srt)と除去一覧(display-fillers.md)の検査。

仕様: docs/spec/subtitle-formatting.md#受入基準 (AC1〜AC10)
  - PO が承認した講義(AC18。lecture-1〜3 とも 2026-10-26 承認済み)では、整形済みファイルと
    除去一覧が存在しなければ失敗する(AC1 の末尾)。
  - 検査ロジックそのもの(check_*)は、一時ディレクトリの小さな合成データで検査する。
    これは整形済みファイルの有無に依らず常に実行される。
  - 除去一覧の形式は仕様の「整形済みファイルの置き場所・名前・形式」の表のとおり:
    markdown の表。列 = 元の番号 / 位置(元キューの文の中の 0 始まりの文字位置) / 除いた語 / メモ。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from interfaces.tutoring.srt import parse_srt_file

ROOT = Path(__file__).resolve().parent.parent.parent
TIME_RE = re.compile(r"^(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})$")
BRACKET_FULL_RE = re.compile(r"^\[[^\]]*\]$")
ALLOWED_FILLERS = {"えっと", "えー", "え", "うーん", "あのー", "ま", "まあ", "ええ"}
KEPT_WORDS = {"その", "はい"}
TIME_TOLERANCE = 0.01  # AC5
MAX_CHARS = 50  # AC7 (Q9 の推奨)


# ---------------------------------------------------------------------------
# 検査ロジック
# ---------------------------------------------------------------------------
def _split_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = [[]]
    for line in text.split("\r\n"):
        if line == "":
            blocks.append([])
        else:
            blocks[-1].append(line)
    if blocks and blocks[-1] == []:
        blocks.pop()  # 末尾の改行は許す(AC1 は末尾改行を規定しない)
    return blocks


def check_format(data: bytes, path: Path) -> list[str]:
    """AC1: 形式。"""
    errors: list[str] = []
    if data.startswith(b"\xef\xbb\xbf"):
        errors.append("UTF-8 BOM がある")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return errors + ["UTF-8 としてデコードできない"]
    if re.search(rb"(?<!\r)\n", data):
        errors.append("CR を伴わない LF がある")
    if re.search(rb"\r(?!\n)", data):
        errors.append("LF を伴わない CR がある")
    blocks = _split_blocks(text)
    if not blocks:
        return errors + ["ブロックが 1 つもない"]
    if [b[0] if b else "" for b in blocks] != [str(i) for i in range(1, len(blocks) + 1)]:
        errors.append("番号が 1 からの連番ではない(欠番・重複)")
    for i, b in enumerate(blocks, 1):
        if len(b) != 3:
            errors.append(f"ブロック{i}: 行数 {len(b)} != 3")
            continue
        if not TIME_RE.match(b[1]):
            errors.append(f"ブロック{i}: 時刻行の形式が不正")
        if not b[2].strip():
            errors.append(f"ブロック{i}: 文が空")
    try:
        n = len(parse_srt_file(path))
    except Exception as e:  # noqa: BLE001
        errors.append(f"parse_srt_file が失敗: {e!r}")
    else:
        if n != len(blocks):
            errors.append(f"parse_srt_file の件数 {n} != ブロック数 {len(blocks)}")
    return errors


def parse_fillers(md_text: str) -> list[tuple[int, int, str]]:
    """除去一覧の表から (元の番号, 位置, 除いた語) を取り出す。"""
    rows: list[tuple[int, int, str]] = []
    for line in md_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or not cells[0].isdigit() or not cells[1].isdigit():
            continue  # 見出し行・区切り行
        rows.append((int(cells[0]), int(cells[1]), cells[2]))
    return rows


@dataclass
class Cue:
    start: float
    end: float
    text: str


@dataclass
class Case:
    """原本のキュー、整形済みの件、除去一覧、およびそこから導く対応づけ。"""

    orig: list[Cue]
    disp: list[Cue]
    fillers: list[tuple[int, int, str]]

    def __post_init__(self) -> None:
        self.starts: list[int] = []  # 各原本キューの文が連結文字列のどこから始まるか
        pos = 0
        for c in self.orig:
            self.starts.append(pos)
            pos += len(c.text)
        self.orig_concat = "".join(c.text for c in self.orig)
        self.removed: set[int] = set()
        for num, p, word in self.fillers:
            if 1 <= num <= len(self.orig):
                base = self.starts[num - 1] + p
                self.removed.update(range(base, base + len(word)))
        self.kept: list[int] = [i for i in range(len(self.orig_concat)) if i not in self.removed]
        self.expected_concat = "".join(self.orig_concat[i] for i in self.kept)
        self.disp_concat = "".join(c.text for c in self.disp)

    def locate(self, g: int) -> tuple[int, int]:
        """連結文字列の位置 g -> (原本キューの添字, その文の中の位置)。"""
        for i in range(len(self.orig) - 1, -1, -1):
            if g >= self.starts[i]:
                return i, g - self.starts[i]
        raise ValueError(g)


def load_case(orig_path: Path, disp_path: Path, fillers_path: Path | None) -> Case:
    def cues(p: Path) -> list[Cue]:
        return [Cue(s["start_sec"], s["end_sec"], s["text"]) for s in parse_srt_file(p)]

    fillers: list[tuple[int, int, str]] = []
    if fillers_path is not None and fillers_path.is_file():
        fillers = parse_fillers(fillers_path.read_text(encoding="utf-8"))
    return Case(cues(orig_path), cues(disp_path), fillers)


def check_char_preservation(case: Case, fillers_exist: bool = True) -> list[str]:
    """AC2: 元の文字の保存。"""
    errors: list[str] = []
    if not fillers_exist:
        errors.append("除去一覧(display-fillers.md)がない")
    seen: set[int] = set()
    for num, p, word in case.fillers:
        if not (1 <= num <= len(case.orig)):
            errors.append(f"除去一覧: 元の番号 {num} が範囲外")
            continue
        text = case.orig[num - 1].text
        if text[p : p + len(word)] != word or not word:
            errors.append(f"除去一覧: 元{num}の位置{p}に「{word}」がない")
        if word not in ALLOWED_FILLERS:
            errors.append(f"除去一覧: 「{word}」は除いてよい語ではない")
        if word in KEPT_WORDS:
            errors.append(f"除去一覧: 「{word}」は残す語")
        span = set(range(case.starts[num - 1] + p, case.starts[num - 1] + p + len(word)))
        if span & seen:
            errors.append(f"除去一覧: 元{num}の位置{p}が重複している")
        seen |= span
    if case.disp_concat != case.expected_concat:
        # 最初の不一致を示す
        a, b = case.disp_concat, case.expected_concat
        k = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
        errors.append(
            f"文字列が一致しない(位置{k}): 整形済み「{a[k:k+15]}」 期待「{b[k:k+15]}」"
        )
    return errors


def check_order(case: Case) -> list[str]:
    """AC3: 時刻の順序と重なり。"""
    errors: list[str] = []
    for i, c in enumerate(case.disp, 1):
        if not c.start < c.end:
            errors.append(f"件{i}: 開始 {c.start} < 終了 {c.end} ではない")
    for i in range(len(case.disp) - 1):
        a, b = case.disp[i], case.disp[i + 1]
        if a.start > b.start:
            errors.append(f"件{i+1}→{i+2}: 開始時刻の順ではない")
        if a.end > b.start:
            errors.append(f"件{i+1}→{i+2}: 前の終了 {a.end} > 次の開始 {b.start}")
    return errors


def check_range(case: Case) -> list[str]:
    """AC4: 時刻の範囲。"""
    errors: list[str] = []
    if not case.disp:
        return ["整形済みの件がない"]
    if abs(case.disp[0].start - case.orig[0].start) > 0.0005:
        errors.append(f"最初の開始 {case.disp[0].start} != 元 {case.orig[0].start}")
    if abs(case.disp[-1].end - case.orig[-1].end) > 0.0005:
        errors.append(f"最後の終了 {case.disp[-1].end} != 元 {case.orig[-1].end}")
    return errors


def expected_times(case: Case) -> list[tuple[float, float]] | None:
    """AC5(Q3 + Q8 の推奨)の期待時刻。AC2 が成り立たないときは None。"""
    if case.disp_concat != case.expected_concat:
        return None
    result: list[tuple[float, float]] = []
    pos = 0  # kept 上の位置
    firsts: list[int] = []
    lasts: list[int] = []
    for c in case.disp:
        firsts.append(case.kept[pos])
        pos += len(c.text)
        lasts.append(case.kept[pos - 1])
    starts: list[float] = []
    for g in firsts:
        i, k = case.locate(g)
        cue = case.orig[i]
        if k == 0:
            starts.append(cue.start)
        else:
            nxt = case.orig[i + 1].start if i + 1 < len(case.orig) else cue.end
            length = min(cue.end, nxt) - cue.start
            starts.append(cue.start + length * (k / len(cue.text)))
    for j, g in enumerate(lasts):
        if j + 1 < len(case.disp):
            end = starts[j + 1]
            i, k = case.locate(g)
            cue = case.orig[i]
            if k == len(cue.text) - 1 and i + 1 < len(case.orig) and cue.end < case.orig[i + 1].start:
                end = cue.end
        else:
            end = case.orig[-1].end
        result.append((starts[j], end))
    return result


def check_times(case: Case) -> list[str]:
    """AC5: 時刻の規則。"""
    exp = expected_times(case)
    if exp is None:
        return ["AC2 が成り立たないため、文字の対応づけができない"]
    errors: list[str] = []
    for i, (c, (s, e)) in enumerate(zip(case.disp, exp), 1):
        if abs(c.start - s) > TIME_TOLERANCE:
            errors.append(f"件{i}「{c.text[:10]}」: 開始 {c.start} != 期待 {s:.3f}")
        if abs(c.end - e) > TIME_TOLERANCE:
            errors.append(f"件{i}「{c.text[:10]}」: 終了 {c.end} != 期待 {e:.3f}")
    return errors


def check_brackets(case: Case) -> list[str]:
    """AC6: 括弧のキューは、それだけの1件として残る。"""
    errors: list[str] = []
    orig_br = [c.text for c in case.orig if BRACKET_FULL_RE.match(c.text)]
    disp_br = [c.text for c in case.disp if BRACKET_FULL_RE.match(c.text)]
    if orig_br != disp_br:
        errors.append(f"括弧だけの件 {disp_br} != 元の括弧のキュー {orig_br}")
    for i, c in enumerate(case.disp, 1):
        if not BRACKET_FULL_RE.match(c.text) and re.search(r"[\[\]]", c.text):
            errors.append(f"件{i}: 括弧がほかの文とつながっている「{c.text}」")
    return errors


def check_length(case: Case) -> list[str]:
    """AC7: 括弧のキューを除き 50 字以下。"""
    return [
        f"件{i}: {len(c.text)} 字 > {MAX_CHARS}「{c.text[:12]}…」"
        for i, c in enumerate(case.disp, 1)
        if not BRACKET_FULL_RE.match(c.text) and len(c.text) > MAX_CHARS
    ]


def check_unbroken(case: Case, strings: list[str]) -> list[str]:
    """AC8: 各文字列が、どれか1件の文の中にそのまま含まれる。"""
    return [f"「{s}」が1件の中に含まれない" for s in strings if not any(s in c.text for c in case.disp)]


def check_fillers_removed(case: Case, pairs: list[tuple[str, str]]) -> list[str]:
    """AC9: 左が含まれず、右が含まれる(時刻の順につなげた文字列)。"""
    errors = []
    for left, right in pairs:
        if left in case.disp_concat:
            errors.append(f"「{left}」が残っている")
        if right not in case.disp_concat:
            errors.append(f"「{right}」がない")
    return errors


def check_kept(case: Case, strings: list[str]) -> list[str]:
    """AC10: フィラーでない語を除いていない。"""
    return [f"「{s}」が含まれない" for s in strings if s not in case.disp_concat]


# ---------------------------------------------------------------------------
# 固定の例(仕様の AC8〜10)
# ---------------------------------------------------------------------------
AC8: dict[str, list[str]] = {
    "lecture-1": ["皆さんの多くは学校で球の表面積が4πr²であることを学んだでしょう", "証明するだけでなく"],
    "lecture-2": ["この問題は割と有名なんですね", "知ってる人も多いと思うんですが"],
    "lecture-3": ["すごくね有名なパラドックスなんですけど", "3人の死刑囚"],
}
AC9: dict[str, list[tuple[str, str]]] = {
    "lecture-1": [("今回の場合まあこれらの2つ", "今回の場合これらの2つ"), ("思いますまあレクチャー", "思いますレクチャー")],
    "lecture-2": [("はいえーもう1回", "はいもう1回"), ("ここはまあ普通", "ここは普通"), ("思うんですがまあ納得", "思うんですが納得")],
    "lecture-3": [
        ("思いますえこれは", "思いますこれは"),
        ("なんですけどえどういう", "なんですけどどういう"),
        ("やってくるんですねえちなみに", "やってくるんですねちなみに"),
        ("言いますえなんと", "言いますなんと"),
        ("わけですま別に", "わけです別に"),
        ("確率ですま条件付", "確率です条件付"),
        ("イコールまあ1/3", "イコール1/3"),
    ],
}
AC10: dict[str, list[str]] = {
    "lecture-1": ["簡単にはいきません"],
    "lecture-2": ["はいこんにちは", "まず大事な", "たまたまハズレ"],
    "lecture-3": ["その面積の割合", "答えます", "はいこんにちは"],
}
BRACKETS: dict[str, list[str]] = {
    "lecture-1": ["[音楽]"] * 3,
    "lecture-2": ["[音楽]"],
    "lecture-3": ["[笑い]", "[音楽]"],
}
LECTURE_IDS = ["lecture-1", "lecture-2", "lecture-3"]


# ---------------------------------------------------------------------------
# 実データの検査(承認済みの講義でファイルがなければ失敗)
# ---------------------------------------------------------------------------
def missing_display_files(lecture_dir: Path) -> list[str]:
    """AC1(AC18 承認後): 整形済みファイルと除去一覧が存在しなければ、その名前を返す。"""
    return [n for n in ("subtitles.display.srt", "display-fillers.md") if not (lecture_dir / n).is_file()]


@pytest.fixture(params=LECTURE_IDS)
def real(request) -> tuple[str, Path, Case]:
    lid: str = request.param
    d = ROOT / "lectures" / lid
    missing = missing_display_files(d)
    if missing:
        pytest.fail(f"{lid}: PO 承認済みの講義なのにファイルがない: {missing}")
    disp = d / "subtitles.display.srt"
    return lid, disp, load_case(d / "subtitles.srt", disp, d / "display-fillers.md")


# 仕様: docs/spec/subtitle-formatting.md#受入基準
class TestRealDisplayData:
    def test_ac1_format(self, real) -> None:
        """AC1: 形式。"""
        _, disp, _ = real
        assert check_format(disp.read_bytes(), disp) == []

    def test_ac2_characters_preserved(self, real) -> None:
        """AC2: 元の文字の保存(除去一覧が指す文字だけが除かれている)。"""
        lid, _, case = real
        fillers = ROOT / "lectures" / lid / "display-fillers.md"
        assert check_char_preservation(case, fillers.is_file()) == []

    def test_ac3_order_and_no_overlap(self, real) -> None:
        """AC3: 時刻の順序と重なり。"""
        assert check_order(real[2]) == []

    def test_ac4_time_range(self, real) -> None:
        """AC4: 時刻の範囲。"""
        assert check_range(real[2]) == []

    def test_ac5_time_rule(self, real) -> None:
        """AC5: 時刻の規則(Q3、±0.01 秒)。"""
        assert check_times(real[2]) == []

    def test_ac6_bracket_cues_kept_alone(self, real) -> None:
        """AC6: 括弧のキューを1件として残す(講義ごとの個数と文は仕様の固定値)。"""
        lid, _, case = real
        assert [c.text for c in case.orig if BRACKET_FULL_RE.match(c.text)] == BRACKETS[lid]
        assert check_brackets(case) == []

    def test_ac7_length_limit(self, real) -> None:
        """AC7: 括弧のキューを除き 50 字以下。"""
        assert check_length(real[2]) == []

    def test_ac8_unbroken_examples(self, real) -> None:
        """AC8: 語の途中で区切らない(固定の例)。"""
        assert check_unbroken(real[2], AC8[real[0]]) == []

    def test_ac9_fillers_removed_examples(self, real) -> None:
        """AC9: フィラーの除去(固定の例)。"""
        assert check_fillers_removed(real[2], AC9[real[0]]) == []

    def test_ac10_non_fillers_kept_examples(self, real) -> None:
        """AC10: フィラーでない語を除かない(固定の例)。"""
        assert check_kept(real[2], AC10[real[0]]) == []


# ---------------------------------------------------------------------------
# 検査ロジックの検査(合成データ。常に実行する)
# ---------------------------------------------------------------------------
def _ts(sec: float) -> str:
    ms = round(sec * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def _srt(cues: list[tuple[float, float, str]]) -> bytes:
    return "\r\n\r\n".join(
        f"{i}\r\n{_ts(s)} --> {_ts(e)}\r\n{t}" for i, (s, e, t) in enumerate(cues, 1)
    ).encode("utf-8")


# 原本: 括弧、フィラー(まあ・えー)を含む文、元キュー間の隙間(10.0 -> 11.0)
ORIG = [
    (0.0, 3.0, "[音楽]"),
    (3.0, 7.0, "今回はまあ線形代数"),
    (7.0, 10.0, "を学びます"),
    (11.0, 13.0, "はいえーもう1回"),
]
FILLERS_MD = (
    "# 除去一覧\n\n| 元の番号 | 位置 | 除いた語 | メモ |\n|---|---|---|---|\n"
    "| 2 | 3 | まあ | |\n| 4 | 2 | えー | |\n"
)
# 2番目の元キューの途中(7/9 の位置)で分ける: 開始 = 3 + 4 * 7/9
SPLIT = 3.0 + 4.0 * 7 / 9
DISP = [
    (0.0, 3.0, "[音楽]"),
    (3.0, SPLIT, "今回は線形"),
    (SPLIT, 7.0, "代数"),
    (7.0, 10.0, "を学びます"),
    (11.0, 13.0, "はいもう1回"),
]
# 2行ロール(lecture-1 型): e1 は次の開始 3.0 までの長さ 3.0 で比を取る(Q8-1 の推奨)
ORIG_ROLL = [(0.0, 6.0, "あいうえおかきくけこ"), (3.0, 9.0, "さしすせそ")]
DISP_ROLL = [(0.0, 1.5, "あいうえお"), (1.5, 9.0, "かきくけこさしすせそ")]


def _make(tmp_path: Path, orig, disp, fillers_md: str = "") -> tuple[Path, Path, Path]:
    o, d, f = tmp_path / "subtitles.srt", tmp_path / "subtitles.display.srt", tmp_path / "display-fillers.md"
    o.write_bytes(_srt(orig))
    d.write_bytes(_srt(disp))
    f.write_text(fillers_md, encoding="utf-8")
    return o, d, f


def _case(tmp_path, orig=ORIG, disp=DISP, md=FILLERS_MD) -> Case:
    o, d, f = _make(tmp_path, orig, disp, md)
    return load_case(o, d, f)


class TestCheckLogic:
    def test_ac1_missing_files_are_detected(self, tmp_path) -> None:
        assert missing_display_files(tmp_path) == ["subtitles.display.srt", "display-fillers.md"]
        (tmp_path / "subtitles.display.srt").write_bytes(b"")
        assert missing_display_files(tmp_path) == ["display-fillers.md"]
        (tmp_path / "display-fillers.md").write_text("", encoding="utf-8")
        assert missing_display_files(tmp_path) == []

    def test_valid_synthetic_data_passes_every_check(self, tmp_path) -> None:
        o, d, f = _make(tmp_path, ORIG, DISP, FILLERS_MD)
        case = load_case(o, d, f)
        assert check_format(d.read_bytes(), d) == []
        assert check_char_preservation(case) == []
        assert check_order(case) == []
        assert check_range(case) == []
        assert check_times(case) == []
        assert check_brackets(case) == []
        assert check_length(case) == []

    def test_valid_two_row_roll_passes_time_rule(self, tmp_path) -> None:
        case = _case(tmp_path, ORIG_ROLL, DISP_ROLL, "")
        assert check_char_preservation(case) == []
        assert check_order(case) == []
        assert check_times(case) == []

    def test_ac1_detects_format_breakage(self, tmp_path) -> None:
        _, d, _ = _make(tmp_path, ORIG, DISP, FILLERS_MD)
        good = d.read_bytes()

        def bad(data: bytes) -> list[str]:
            p = tmp_path / "x.srt"
            p.write_bytes(data)
            return check_format(data, p)

        assert bad(good) == []
        assert bad(b"\xef\xbb\xbf" + good) != []  # BOM
        assert bad(good.replace(b"\r\n", b"\n")) != []  # LF
        assert bad(good.replace(b"\r\n\r\n2\r\n", b"\r\n\r\n3\r\n", 1)) != []  # 欠番
        assert bad(good.replace(b" --> ", b" -> ", 1)) != []  # 時刻形式
        assert bad(good.replace("を学びます".encode(), "を学びます\r\n追加行".encode())) != []  # 2行
        assert bad(good.replace("を学びます".encode(), b"")) != []  # 空の文
        assert bad(b"") != []

    def test_ac2_detects_added_changed_missing_char_and_bad_fillers_list(self, tmp_path) -> None:
        assert check_char_preservation(_case(tmp_path)) == []
        # 文字の追加・変更・欠落
        for disp in (
            [*DISP[:3], (7.0, 10.0, "を学びますよ"), DISP[4]],
            [*DISP[:3], (7.0, 10.0, "を学ぶます"), DISP[4]],
            [*DISP[:3], (7.0, 10.0, "学びます"), DISP[4]],
        ):
            assert check_char_preservation(_case(tmp_path, disp=disp)) != []
        # フィラーを除いていない(除去一覧に無い除去)
        assert check_char_preservation(_case(tmp_path, md=FILLERS_MD.split("| 4 | 2 |")[0])) != []
        # 一覧が実在しない位置を指す / 除いてよい語でない / 残す語
        wrong_pos = FILLERS_MD.replace("| 2 | 3 | まあ |", "| 2 | 4 | まあ |")
        assert check_char_preservation(_case(tmp_path, md=wrong_pos)) != []
        for kept in ("はい", "その"):
            assert (
                check_char_preservation(
                    _case(
                        tmp_path,
                        orig=[(0.0, 1.0, f"A{kept}B")],
                        disp=[(0.0, 1.0, "AB")],
                        md=f"| 元の番号 | 位置 | 除いた語 | メモ |\n|---|---|---|---|\n| 1 | 1 | {kept} | |\n",
                    )
                )
                != []
            )
        # 除去一覧がない
        assert check_char_preservation(_case(tmp_path), fillers_exist=False) != []

    def test_ac3_detects_order_and_overlap_breakage(self, tmp_path) -> None:
        assert check_order(_case(tmp_path)) == []
        swapped = [DISP[0], DISP[2], DISP[1], *DISP[3:]]
        assert check_order(_case(tmp_path, disp=swapped, md=FILLERS_MD)) != []
        zero = [*DISP[:3], (7.0, 7.0, "を学びます"), DISP[4]]
        assert check_order(_case(tmp_path, disp=zero)) != []
        overlap = [DISP[0], (3.0, 7.5, "今回は線形"), (SPLIT, 7.0, "代数"), *DISP[3:]]
        assert check_order(_case(tmp_path, disp=overlap)) != []

    def test_ac4_detects_range_mismatch(self, tmp_path) -> None:
        assert check_range(_case(tmp_path)) == []
        assert check_range(_case(tmp_path, disp=[(0.5, 3.0, "[音楽]"), *DISP[1:]])) != []
        assert check_range(_case(tmp_path, disp=[*DISP[:4], (11.0, 12.5, "はいもう1回")])) != []

    def test_ac5_detects_time_rule_breakage_and_tolerance(self, tmp_path) -> None:
        assert check_times(_case(tmp_path)) == []
        # 文字数の比でない値 / 元キュー先頭でない開始に元の開始を使う
        wrong = [DISP[0], (3.0, 5.0, "今回は線形"), (5.0, 7.0, "代数"), *DISP[3:]]
        assert check_times(_case(tmp_path, disp=wrong)) != []
        # 隙間のある境目の終了を、次の開始にしてしまう
        no_gap_end = [*DISP[:3], (7.0, 11.0, "を学びます"), DISP[4]]
        assert check_times(_case(tmp_path, disp=no_gap_end)) != []
        # 許容: 0.009 秒のずれは通り、0.02 秒のずれは落ちる
        near = [DISP[0], (3.0, SPLIT + 0.009, "今回は線形"), (SPLIT + 0.009, 7.0, "代数"), *DISP[3:]]
        assert check_times(_case(tmp_path, disp=near)) == []
        far = [DISP[0], (3.0, SPLIT + 0.02, "今回は線形"), (SPLIT + 0.02, 7.0, "代数"), *DISP[3:]]
        assert check_times(_case(tmp_path, disp=far)) != []
        # 2行ロール: 元キュー終了(6.0)までの長さで比を取った値(3.0)は誤り
        roll_wrong = [(0.0, 3.0, "あいうえお"), (3.0, 9.0, "かきくけこさしすせそ")]
        assert check_times(_case(tmp_path, ORIG_ROLL, roll_wrong, "")) != []

    def test_ac6_detects_bracket_merged_or_dropped(self, tmp_path) -> None:
        assert check_brackets(_case(tmp_path)) == []
        merged = [(0.0, 3.0, "[音楽]今回は線形"), *DISP[2:]]
        assert check_brackets(_case(tmp_path, disp=merged)) != []
        dropped = [(0.0, 3.0, "今回は線形"), *DISP[2:]]
        assert check_brackets(_case(tmp_path, disp=dropped)) != []

    def test_ac7_detects_over_limit_but_allows_exactly_50_and_brackets(self, tmp_path) -> None:
        def with_len(n: int) -> Case:
            return _case(tmp_path, [(0.0, 1.0, "あ" * n)], [(0.0, 1.0, "あ" * n)], "")

        assert check_length(with_len(50)) == []
        assert check_length(with_len(51)) != []
        long_bracket = "[" + "あ" * 60 + "]"
        assert check_length(_case(tmp_path, [(0.0, 1.0, long_bracket)], [(0.0, 1.0, long_bracket)], "")) == []

    def test_ac8_ac9_ac10_detect_violations(self, tmp_path) -> None:
        case = _case(tmp_path)
        assert check_unbroken(case, ["代数"]) == []
        assert check_unbroken(case, ["線形代数"]) != []  # 件の境目で切れている
        assert check_fillers_removed(case, [("はいえーもう1回", "はいもう1回")]) == []
        assert check_fillers_removed(case, [("今回はまあ", "今回は")]) == []
        assert check_fillers_removed(case, [("を学びます", "はいもう1回")]) != []  # 左が残る
        assert check_fillers_removed(case, [("はいえーもう1回", "存在しない")]) != []  # 右がない
        assert check_kept(case, ["はいもう1回"]) == []
        assert check_kept(case, ["はいえー"]) != []
