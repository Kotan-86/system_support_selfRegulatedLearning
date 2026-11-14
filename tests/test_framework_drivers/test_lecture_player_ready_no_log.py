"""講義の画面の player.js が、準備完了の自動の再生・一時停止を視聴ログに記録しないこと(AC16)を Node で検証し、pytest から呼ぶ。

仕様: docs/spec/multi-video-learning.md#受入基準 (AC16。What 9節、Q15)
方式は bugs/seek-duplicate-count.md の AC10(test_lecture_player_seek_count.py)と同じ。
Node が見つからない環境ではスキップする(AC16 の本文どおり。品質報告で PASSED を確認する)。
"""

import shutil
import subprocess
from pathlib import Path

import pytest

_MJS = Path(__file__).resolve().parent / "js" / "lecture_player_ready_no_log.mjs"
_NODE = shutil.which("node")


@pytest.mark.skipif(_NODE is None, reason="Node が見つからない")
def test_ac16_ready_sends_no_viewing_log_and_user_play_pause_send_one_each() -> None:
    # 仕様: docs/spec/multi-video-learning.md#受入基準 AC16
    result = subprocess.run(
        [_NODE, str(_MJS)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, (
        f"Node 検証が失敗 (終了コード {result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert "ok   AC16 準備完了まで進めただけでは視聴ログが0件" in result.stdout, result.stdout
