"""講義動画 player.js のシーク記録件数(AC10)を Node で検証し、pytest から呼ぶ。

仕様: docs/spec/bugs/seek-duplicate-count.md#受入基準 (AC10)
Node が見つからない環境ではスキップする(理由を表示)。
"""

import shutil
import subprocess
from pathlib import Path

import pytest

_MJS = Path(__file__).resolve().parent / "js" / "lecture_player_seek_count.mjs"
_NODE = shutil.which("node")


@pytest.mark.skipif(_NODE is None, reason="Node が見つからない")
def test_ac10_seek_and_other_log_counts_via_node() -> None:
    # 仕様: docs/spec/bugs/seek-duplicate-count.md#受入基準 AC10 (a)(b)(c)(d), N=0,1,3
    result = subprocess.run(
        [_NODE, str(_MJS)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"Node 検証が失敗 (終了コード {result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
