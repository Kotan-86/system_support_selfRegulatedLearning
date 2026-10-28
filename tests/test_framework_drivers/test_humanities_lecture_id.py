"""講義ページ・振り返りページの JS が送る講義ID(本文・URL)を Node で検証し、pytest から呼ぶ。

仕様: docs/spec/humanities-lectures.md#受入基準 (PBI #33)
対象AC: AC17(視聴ログ), AC18(小テスト送信), AC19(b)(c)(振り返りページの /chat と LAD 取得),
        AC20(講義IDなしの後方互換), AC21(a)(対話ログの保存要求), AC13(d)(講義IDなしの本文は2つだけ)。
AC番号は js/humanities_lecture_id.mjs の各検証名の先頭に入っている。
Node が見つからない環境ではスキップする。
"""

import shutil
import subprocess
from pathlib import Path

import pytest

_MJS = Path(__file__).resolve().parent / "js" / "humanities_lecture_id.mjs"
_NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(_NODE is None, reason="Node が見つからない")


@pytest.fixture(scope="module")
def node_output() -> subprocess.CompletedProcess:
    return subprocess.run(
        [_NODE, str(_MJS)], capture_output=True, text=True, timeout=120, encoding="utf-8"
    )


def _assert_group(out: subprocess.CompletedProcess, prefix: str) -> None:
    lines = [
        ln for ln in out.stdout.splitlines() if ln.startswith(("ok   " + prefix, "FAIL " + prefix))
    ]
    failed = [ln for ln in lines if ln.startswith("FAIL")]
    assert lines, (
        f"{prefix} の検証が1件も出力されていない\n--- stdout ---\n{out.stdout}\n--- stderr ---\n{out.stderr}"
    )
    assert not failed, "\n".join(failed)


@pytest.mark.parametrize(
    "prefix",
    ["AC17", "AC18", "AC19", "AC20", "AC21", "AC13(d)"],
)
def test_lecture_id_is_sent_via_node(node_output, prefix: str) -> None:
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC17, AC18, AC19, AC20, AC21, AC13(d)
    _assert_group(node_output, prefix)


def test_node_script_exits_zero(node_output) -> None:
    # 仕様: docs/spec/humanities-lectures.md#受入基準 AC17〜AC21(Node 検証全体の成否)
    assert node_output.returncode == 0, (
        f"Node 検証が失敗 (終了コード {node_output.returncode})\n"
        f"--- stdout ---\n{node_output.stdout}\n--- stderr ---\n{node_output.stderr}"
    )
