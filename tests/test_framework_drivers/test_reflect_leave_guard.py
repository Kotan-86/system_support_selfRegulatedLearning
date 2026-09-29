"""振り返り画面の離脱ガード(leave_guard.js)の論理を Node で検証し、pytest から呼ぶ。

仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-B)
対象AC: B1, B2, B3, B4, B6(自動テスト部分)。AC番号は js/reflect_leave_guard.mjs の各検証名に入っている。
実ブラウザのダイアログ表示と離脱時の通信の到達は PO確認。Node が見つからない環境ではスキップする。
"""

import shutil
import subprocess
from pathlib import Path

import pytest

_MJS = Path(__file__).resolve().parent / "js" / "reflect_leave_guard.mjs"
_NODE = shutil.which("node")


@pytest.fixture(scope="module")
def node_output() -> str:
    if _NODE is None:
        pytest.skip("Node が見つからない")
    result = subprocess.run([_NODE, str(_MJS)], capture_output=True, text=True, timeout=60)
    return result.stdout + "\n" + result.stderr + f"\n(exit={result.returncode})"


def _assert_ac(output: str, prefix: str) -> None:
    lines = [ln for ln in output.splitlines() if ln.startswith(("ok   ", "FAIL "))]
    ac_lines = [ln for ln in lines if ln[5:].startswith(prefix)]
    assert ac_lines, f"{prefix} の検証が出力に無い\n{output}"
    failed = [ln for ln in ac_lines if ln.startswith("FAIL ")]
    assert not failed, f"{prefix} の検証が失敗\n" + "\n".join(failed) + f"\n--- 全出力 ---\n{output}"


@pytest.mark.parametrize("ac", ["B1", "B2", "B3", "B4", "B6"])
def test_leave_guard_logic_via_node(node_output: str, ac: str) -> None:
    # 仕様: docs/spec/dialog-log-save.md#受入基準 B1〜B4, B6
    _assert_ac(node_output, ac)


def test_leave_guard_node_exit_code_zero(node_output: str) -> None:
    # 仕様: docs/spec/dialog-log-save.md#受入基準 B1〜B4, B6(防御を含む全検証)
    assert node_output.rstrip().endswith("(exit=0)"), node_output
