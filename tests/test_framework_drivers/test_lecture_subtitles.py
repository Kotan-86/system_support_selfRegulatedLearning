"""講義動画の字幕の表示・非表示(AC2〜8, 10, 12, 14)を Node で検証し、pytest から呼ぶ。

仕様: docs/spec/subtitle-display.md#受入基準
Node が見つからない環境ではスキップする(理由を表示)。
"""

import shutil
import subprocess
from pathlib import Path

import pytest

_MJS = Path(__file__).resolve().parent / "js" / "lecture_subtitles.mjs"
_LECTURES = Path(__file__).resolve().parents[2] / "lectures"
_NODE = shutil.which("node")


@pytest.mark.skipif(_NODE is None, reason="Node が見つからない")
def test_ac2_to_ac14_subtitles_via_node() -> None:
    # 仕様: docs/spec/subtitle-display.md#受入基準 AC2〜AC8, AC10, AC12, AC14
    result = subprocess.run(
        [_NODE, str(_MJS), str(_LECTURES)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert result.returncode == 0, (
        f"Node 検証が失敗 (終了コード {result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# 回帰防止(PBI #36 のPO確認で出た AC13 の問題)。player.js のソースの静的検査。
# 仕様: docs/spec/subtitle-display.md#受入基準 AC13
# ---------------------------------------------------------------------------
import re

_PLAYER_JS = (
    Path(__file__).resolve().parents[2]
    / "framework_drivers" / "platform" / "static" / "js" / "lecture" / "player.js"
)


def _function_body(source: str, name: str) -> str:
    """`function name(...) {` の波括弧が対応するところまでの本文を返す。"""
    m = re.search(r"function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", source)
    assert m, f"player.js に {name} がない"
    depth, i = 1, m.end()
    while depth and i < len(source):
        depth += {"{": 1, "}": -1}.get(source[i], 0)
        i += 1
    assert depth == 0, f"{name} の波括弧が閉じない"
    return source[m.end():i - 1]


def test_ac13_player_vars_do_not_force_youtube_captions() -> None:
    # 仕様: docs/spec/subtitle-display.md#受入基準 AC13
    source = _PLAYER_JS.read_text(encoding="utf-8")
    m = re.search(r"playerVars\s*:\s*\{(.*?)\}", source, re.S)
    assert m, "player.js に playerVars がない"
    policy = re.search(r"cc_load_policy\s*:\s*(\d+)", m.group(1))
    assert policy, "playerVars に cc_load_policy がない"
    assert policy.group(1) == "0", "cc_load_policy は 0(YouTube 側の字幕を強制表示しない)"


def test_ac13_hide_youtube_captions_has_no_side_effects_on_playback_or_log() -> None:
    # 仕様: docs/spec/subtitle-display.md#受入基準 AC13(字幕を外す処理が再生・ログに触れない)
    body = _function_body(_PLAYER_JS.read_text(encoding="utf-8"), "hideYouTubeCaptions")
    assert "unloadModule" in body, "hideYouTubeCaptions が字幕モジュールを外していない"
    for forbidden in ("recordLog", "seekTo", "pauseVideo", "playVideo"):
        assert forbidden not in body, f"hideYouTubeCaptions が {forbidden} を呼んでいる"
