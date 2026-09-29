"""振り返り画面の「対話ログを送信して終了する」ボタンの JS の論理(dialog_log.js と chat_panel.js の連携)を Node で検証し、pytest から呼ぶ。

仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-2)
対象AC: A9, A10, A19 の「画面の JS の論理」(自動テスト部分)。UI の見た目・位置・実ブラウザの操作は PO確認。
AC番号は js/reflect_dialog_log.mjs の各検証名の先頭に入っている(A9 / A10 / A19)。
「IF」は 11-T5 の公開IF(ChatPanel.onSendStateChange など。A9・A10・A19 の前提)。
Node が見つからない環境ではスキップする(理由を表示)。
"""

import shutil
import subprocess
from pathlib import Path

import pytest

_MJS = Path(__file__).resolve().parent / "js" / "reflect_dialog_log.mjs"
_NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(_NODE is None, reason="Node が見つからない")


@pytest.fixture(scope="module")
def node_output() -> subprocess.CompletedProcess:
    return subprocess.run(
        [_NODE, str(_MJS)],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _lines(node_output: subprocess.CompletedProcess, prefix: str) -> list[str]:
    return [
        line
        for line in node_output.stdout.splitlines()
        if line.startswith(("ok   " + prefix, "FAIL " + prefix))
    ]


def _assert_group(node_output: subprocess.CompletedProcess, prefix: str) -> None:
    lines = _lines(node_output, prefix)
    failed = [ln for ln in lines if ln.startswith("FAIL")]
    assert lines, f"{prefix} の検証が1件も出力されていない\n--- stdout ---\n{node_output.stdout}\n--- stderr ---\n{node_output.stderr}"
    assert not failed, "\n".join(failed)


def test_a9_end_button_saves_and_shows_complete_via_node(node_output) -> None:
    # 仕様: docs/spec/dialog-log-save.md#受入基準 A9(画面の JS の論理)
    _assert_group(node_output, "A9")


def test_a10_save_failure_display_and_retry_via_node(node_output) -> None:
    # 仕様: docs/spec/dialog-log-save.md#受入基準 A10(画面の JS の論理)
    _assert_group(node_output, "A10")


def test_a19_end_button_disabled_while_waiting_via_node(node_output) -> None:
    # 仕様: docs/spec/dialog-log-save.md#受入基準 A19(画面の JS の論理)
    _assert_group(node_output, "A19")


def test_t5_public_interface_via_node(node_output) -> None:
    # 仕様: docs/spec/dialog-log-save.md#受入基準 A9・A10・A19 の前提(tasks.md 11-T5 の公開IF)
    _assert_group(node_output, "IF")


def test_node_script_exits_zero(node_output) -> None:
    # 仕様: docs/spec/dialog-log-save.md#受入基準 A9・A10・A19(Node 検証全体の成否)
    assert node_output.returncode == 0, (
        f"Node 検証が失敗 (終了コード {node_output.returncode})\n"
        f"--- stdout ---\n{node_output.stdout}\n--- stderr ---\n{node_output.stderr}"
    )
