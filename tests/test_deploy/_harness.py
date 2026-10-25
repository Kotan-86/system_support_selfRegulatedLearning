# 仕様: docs/spec/db-persistence.md#受入基準 (AC1〜5, AC19〜21 の補助)
"""起動手順(deploy/entrypoint.sh)を、偽の litestream / gunicorn で動かすための補助。

約束(実装が守る前提。tests.md に記録):
- 起動手順は POSIX sh(`sh deploy/entrypoint.sh`)。引数なしで、環境変数だけで動く。
- 環境変数: DB_REPLICA_BUCKET / DB_REPLICA_DISABLED / LEARNING_DB_PATH / TUTOR_DB_PATH。
- 復元は `litestream restore ...` を DB ごとに呼ぶ。復元先は、引数のどこかに
  LEARNING_DB_PATH / TUTOR_DB_PATH と同じパスで現れる(`-o <path>` か位置引数)。
- 「複製なし」は、実の litestream と同じく `-if-replica-exists` なしなら exit 1、ありなら exit 0 で表す。
- 複製の開始は `litestream replicate ... -exec "<gunicorn の起動コマンド>"`。
  偽の replicate は -exec の文字列をシェルで実行する。
- WAL 化は、PATH 上の `python` / `python3`(実の SQLite = 標準 sqlite3)を使ってよい。
  `sqlite3` の CLI は使えない(開発機にない)。
- cwd はプロジェクトのルート。/app が存在することには頼れない。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# テスト自体の検証用に、deploy/ と Dockerfile の置き場を差し替えられる(既定はプロジェクトのルート)。
DEPLOY_ROOT = Path(os.environ.get("DEPLOY_TEST_ROOT") or PROJECT_ROOT)
ENTRYPOINT = DEPLOY_ROOT / "deploy" / "entrypoint.sh"
LITESTREAM_YML = DEPLOY_ROOT / "deploy" / "litestream.yml"
DOCKERFILE = DEPLOY_ROOT / "Dockerfile"


def fwd(path: Path | str) -> str:
    """Windows でも bash と Python の両方が解釈できる `C:/x/y` 形式にする。"""
    return str(path).replace("\\", "/")


def find_bash() -> str | None:
    found = shutil.which("bash")
    if found and "system32" not in found.lower():  # WSL のランチャーは除く
        return found
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432")):
            if base:
                cand = Path(base) / "Git" / "bin" / "bash.exe"
                if cand.exists():
                    return str(cand)
        return None
    return found


BASH = find_bash()
requires_bash = pytest.mark.skipif(
    BASH is None, reason="bash が見つからない(AC2〜5, AC21 は bash が前提)"
)


def posix_dir_for_path(path: Path) -> str:
    """PATH 先頭に置くための POSIX 形式。`C:/x` -> `/c/x`。"""
    s = fwd(path)
    if len(s) > 1 and s[1] == ":":
        return "/" + s[0].lower() + s[2:]
    return s


_FAKE_LITESTREAM = r'''
import json, os, sqlite3, subprocess, sys, time

LOG = os.environ["FAKE_LOG"]


def log(**kw):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def norm(p):
    return os.path.normcase(os.path.abspath(p))


DBS = {"learning": os.environ["LEARNING_DB_PATH"], "tutor": os.environ["TUTOR_DB_PATH"]}


def modes():
    out = {}
    for name, path in DBS.items():
        if os.path.exists(path):
            c = sqlite3.connect(path)
            try:
                out[name] = str(c.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            finally:
                c.close()
        else:
            out[name] = None
    return out


def which_db(args):
    for a in args:
        for name, path in DBS.items():
            if norm(a) == norm(path):
                return name
    for a in args:
        base = os.path.basename(a.replace("\\", "/")).lower()
        for name in DBS:
            if name in base:
                return name
    return None


args = sys.argv[1:]
cmd = args[0] if args else ""
if cmd == "restore":
    which = which_db(args[1:])
    log(ev="restore-begin", which=which, args=args)
    time.sleep(0.3)  # 待たずに先へ進む実装を、順序の検査で検出できるようにする
    fail_for = os.environ.get("FAKE_RESTORE_FAIL_FOR", "")
    if fail_for and which == fail_for:
        sys.stderr.write("fake litestream: simulated restore failure for %s\n" % which)
        log(ev="restore-end", which=which, rc=1, reason="simulated-failure")
        sys.exit(1)
    mode = os.environ.get("FAKE_RESTORE_MODE", "none")
    if mode == "exists" and which:
        path = DBS[which]
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        c = sqlite3.connect(path)
        c.execute("CREATE TABLE IF NOT EXISTS restored_marker (v TEXT)")
        c.execute("INSERT INTO restored_marker VALUES (?)", ("restored-" + which,))
        c.commit()
        created = str(c.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        c.close()
        log(ev="restore-end", which=which, rc=0, created_mode=created)
        sys.exit(0)
    if mode == "none":
        if "-if-replica-exists" in args:
            log(ev="restore-end", which=which, rc=0, reason="no-replica")
            sys.exit(0)
        sys.stderr.write("fake litestream: no matching backups found\n")
        log(ev="restore-end", which=which, rc=1, reason="no-replica-without-if-replica-exists")
        sys.exit(1)
    log(ev="restore-end", which=which, rc=1, reason="unknown-target")
    sys.exit(1)
elif cmd == "replicate":
    log(ev="replicate-start", args=args, modes=modes())
    exec_cmd = None
    for i, a in enumerate(args):
        if a == "-exec" and i + 1 < len(args):
            exec_cmd = args[i + 1]
        elif a.startswith("-exec="):
            exec_cmd = a[len("-exec="):]
    if exec_cmd is None:
        log(ev="replicate-no-exec")
        sys.exit(0)
    rc = subprocess.call([os.environ["FAKE_SHELL"], "-c", exec_cmd])
    log(ev="replicate-end", rc=rc)
    sys.exit(rc)
else:
    log(ev="litestream-other", args=args)
    sys.exit(0)
'''

_FAKE_GUNICORN = r'''
import json, os, sqlite3, sys

LOG = os.environ["FAKE_LOG"]
DBS = {"learning": os.environ["LEARNING_DB_PATH"], "tutor": os.environ["TUTOR_DB_PATH"]}


def log(**kw):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def modes():
    out = {}
    for name, path in DBS.items():
        if os.path.exists(path):
            c = sqlite3.connect(path)
            try:
                out[name] = str(c.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            finally:
                c.close()
        else:
            out[name] = None
    return out


passthrough = {k: os.environ.get(k) for k in ("SECRET_KEY", "PORT")}
log(ev="gunicorn-start", args=sys.argv[1:], modes=modes(), env=passthrough)
if os.environ.get("FAKE_GUNICORN_INIT_APP") == "1":
    sys.path.insert(0, os.environ["FAKE_PROJECT_ROOT"])
    from framework_drivers.platform.wiring import init_databases

    init_databases()
    log(ev="gunicorn-app-initialized", modes=modes())
sys.exit(0)
'''


@dataclass
class Run:
    returncode: int
    output: str
    events: list[dict]

    def evs(self, name: str) -> list[dict]:
        return [e for e in self.events if e.get("ev") == name]

    def index_of(self, name: str, *, last: bool = False) -> int | None:
        idx = [i for i, e in enumerate(self.events) if e.get("ev") == name]
        if not idx:
            return None
        return idx[-1] if last else idx[0]

    @property
    def litestream_events(self) -> list[dict]:
        return [
            e
            for e in self.events
            if str(e.get("ev", "")).startswith(("restore", "replicate", "litestream"))
        ]


def _write_lf(path: Path, text: str, executable: bool = False) -> None:
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    if executable:
        path.chmod(0o755)


def run_entrypoint(
    tmp_path: Path,
    *,
    restore_mode: str = "none",
    fail_for: str = "",
    bucket: str | None = "test-bucket",
    disabled: str | None = None,
    init_app: bool = False,
    timeout: int = 180,
) -> Run:
    assert ENTRYPOINT.exists(), f"起動手順がない: {ENTRYPOINT}"
    assert BASH is not None

    fakebin = tmp_path / "fakebin"
    impl = tmp_path / "fakeimpl"
    work = tmp_path / "work"
    for d in (fakebin, impl, work):
        d.mkdir(parents=True, exist_ok=True)
    log_path = tmp_path / "events.jsonl"
    log_path.write_text("", encoding="utf-8")
    _write_lf(impl / "fake_litestream.py", _FAKE_LITESTREAM)
    _write_lf(impl / "fake_gunicorn.py", _FAKE_GUNICORN)
    _write_lf(
        fakebin / "litestream",
        '#!/bin/sh\nexec "$FAKE_PYTHON" "$FAKE_IMPL/fake_litestream.py" "$@"\n',
        executable=True,
    )
    _write_lf(
        fakebin / "gunicorn",
        '#!/bin/sh\nexec "$FAKE_PYTHON" "$FAKE_IMPL/fake_gunicorn.py" "$@"\n',
        executable=True,
    )
    for name in ("python", "python3"):  # 実の Python(標準 sqlite3)をそのまま使う
        _write_lf(fakebin / name, '#!/bin/sh\nexec "$FAKE_PYTHON" "$@"\n', executable=True)

    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("DB_REPLICA_", "FAKE_"))
    }
    env.update(
        {
            "FAKE_PYTHON": fwd(sys.executable),
            "FAKE_IMPL": fwd(impl),
            "FAKE_BIN": posix_dir_for_path(fakebin),
            "FAKE_LOG": fwd(log_path),
            "FAKE_SHELL": fwd(BASH),
            "FAKE_PROJECT_ROOT": fwd(PROJECT_ROOT),
            "FAKE_RESTORE_MODE": restore_mode,
            "FAKE_RESTORE_FAIL_FOR": fail_for,
            "FAKE_GUNICORN_INIT_APP": "1" if init_app else "0",
            "ENTRYPOINT_PATH": fwd(ENTRYPOINT),
            "LEARNING_DB_PATH": fwd(work / "db" / "learning.db"),
            "TUTOR_DB_PATH": fwd(work / "db" / "tutor.db"),
            "SECRET_KEY": "test-secret-key",
            "PORT": "8080",
        }
    )
    if bucket is not None:
        env["DB_REPLICA_BUCKET"] = bucket
    if disabled is not None:
        env["DB_REPLICA_DISABLED"] = disabled
    (work / "db").mkdir(parents=True, exist_ok=True)

    proc = subprocess.run(
        [BASH, "-c", 'export PATH="$FAKE_BIN:$PATH"; exec sh "$ENTRYPOINT_PATH"'],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        timeout=timeout,
    )
    out = (proc.stdout or b"").decode("utf-8", "replace") + (proc.stderr or b"").decode(
        "utf-8", "replace"
    )
    events = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return Run(proc.returncode, out, events)


def db_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "learning": tmp_path / "work" / "db" / "learning.db",
        "tutor": tmp_path / "work" / "db" / "tutor.db",
    }
