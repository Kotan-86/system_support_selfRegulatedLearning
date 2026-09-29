"""振り返り画面のチャット入力(chat_panel.js)のキー操作・送信制御を Node で検証し、pytest から呼ぶ。

仕様: docs/spec/reflect-chat-multiline-input.md#受入基準
対象AC: AC5〜AC14, AC17(自動テスト部分)。AC番号は js/reflect_chat_panel_input.mjs の各検証名に入っている。
Node が見つからない環境ではスキップする(理由を表示)。
"""

import shutil
import subprocess
from pathlib import Path

import pytest

_MJS = Path(__file__).resolve().parent / "js" / "reflect_chat_panel_input.mjs"
_NODE = shutil.which("node")


@pytest.mark.skipif(_NODE is None, reason="Node が見つからない")
def test_ac5_to_ac14_ac17_chat_input_logic_via_node() -> None:
    # 仕様: docs/spec/reflect-chat-multiline-input.md#受入基準 AC5〜AC14, AC17
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
