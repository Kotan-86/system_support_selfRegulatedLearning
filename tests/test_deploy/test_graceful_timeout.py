# 仕様: docs/spec/db-persistence.md#受入基準 (AC19)
"""AC19: 起動の入口(Dockerfile と deploy/entrypoint.sh)で gunicorn を起動するコマンドに、
gunicorn の終了猶予(--graceful-timeout)が明示に指定されており、10秒未満である。

最終同期が猶予の内に終わるか(U1・U2)は AC11(PO確認)で観察する。ここでは値の指定だけを見る。
"""
from __future__ import annotations

import re

from tests.test_deploy._harness import DOCKERFILE, ENTRYPOINT

CLOUD_RUN_GRACE_SECONDS = 10


def _logical_lines(text: str) -> list[str]:
    """行末の \\ による継続行をつなぎ、コメント行を除く。"""
    joined = re.sub(r"\\\r?\n\s*", " ", text)
    return [l for l in joined.splitlines() if l.strip() and not l.lstrip().startswith("#")]


def _gunicorn_invocations(path) -> list[str]:
    out = []
    for line in _logical_lines(path.read_text(encoding="utf-8")):
        # アプリを指定して起動するコマンド(module:app を伴う gunicorn)
        if re.search(r"\bgunicorn\b", line) and re.search(r"[\w.]+:\w+", line):
            out.append(line)
    return out


def _graceful_timeout(command: str) -> str | None:
    m = re.search(r"--graceful-timeout(?:\s+|=)[\"']?([^\s\"']+)", command)
    return m.group(1) if m else None


def _all_invocations() -> list[tuple[str, str]]:
    found = []
    for path in (DOCKERFILE, ENTRYPOINT):
        assert path.exists(), f"起動の入口のファイルがない: {path}"
        found += [(path.name, c) for c in _gunicorn_invocations(path)]
    return found


def test_ac19_gunicorn_is_started_somewhere_in_the_entry_files():
    assert _all_invocations(), "Dockerfile / deploy/entrypoint.sh に gunicorn の起動コマンドがない"


def test_ac19_every_gunicorn_start_command_sets_graceful_timeout_under_10s():
    invocations = _all_invocations()
    assert invocations, "gunicorn の起動コマンドがない"
    for name, command in invocations:
        raw = _graceful_timeout(command)
        assert raw is not None, f"{name}: --graceful-timeout が明示されていない: {command}"
        assert re.fullmatch(r"\d+(\.\d+)?", raw), (
            f"{name}: --graceful-timeout の値が数値の直書きでない: {raw}"
        )
        value = float(raw)
        assert 0 < value < CLOUD_RUN_GRACE_SECONDS, (
            f"{name}: --graceful-timeout={raw} は Cloud Run の猶予 {CLOUD_RUN_GRACE_SECONDS} 秒未満でない"
        )
