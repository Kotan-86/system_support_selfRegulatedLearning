# 仕様: docs/spec/db-persistence.md#受入基準 (AC1)
"""AC1: Litestream の設定に、learning.db と tutor.db の2つが、それぞれ GCS の複製先とともに
定義されている。設定の DB のパスは、コンテナ内でアプリが使う LEARNING_DB_PATH / TUTOR_DB_PATH の値と一致する。

YAML のパーサーは使わない(Python の依存を足さない)。ブロック形式のインデントを行ベースで読む。
読めるのは `dbs:` の下のリスト(`- path:` と `replica:` / `replicas:`)。フロー形式(`[...]`)は対象外。
"""
from __future__ import annotations

import posixpath
import re
import shlex

from tests.test_deploy._harness import DOCKERFILE, ENTRYPOINT, LITESTREAM_YML

DEFAULTS = {
    # アプリの既定(db/config.py)。WORKDIR は /app。
    "LEARNING_DB_PATH": "/app/db/data/learning.db",
    "TUTOR_DB_PATH": "/app/db/data/tutor.db",
}


def _strip(line: str) -> str:
    return re.sub(r"\s+#.*$", "", line.rstrip())


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse_dbs(text: str) -> list[dict]:
    """[{'path': str, 'replica': {'url','type','bucket','path'}}] を返す。"""
    lines = [_strip(l) for l in text.splitlines()]
    lines = [l for l in lines if l.strip() and not l.lstrip().startswith("#")]
    start = next((i for i, l in enumerate(lines) if re.match(r"^dbs:\s*$", l)), None)
    assert start is not None, "litestream.yml に `dbs:` がない"
    body: list[str] = []
    for l in lines[start + 1 :]:
        if _indent(l) == 0 and not l.startswith("-"):
            break
        body.append(l)
    assert body, "`dbs:` の下が空"
    item_indent = _indent(next(l for l in body if l.lstrip().startswith("-")))
    blocks: list[list[str]] = []
    for l in body:
        if _indent(l) == item_indent and l.lstrip().startswith("-"):
            blocks.append([" " * item_indent + "  " + l.lstrip()[1:].lstrip()])
        elif blocks:
            blocks[-1].append(l)
    key_indent = item_indent + 2
    result = []
    for block in blocks:
        db_path = None
        replica_lines: list[str] = []
        in_replica = False
        for l in block:
            if _indent(l) == key_indent:
                in_replica = False
                m = re.match(r"^\s*([A-Za-z0-9_-]+):\s*(.*)$", l)
                if not m:
                    continue
                key, value = m.group(1), m.group(2)
                if key == "path":
                    db_path = _unquote(value)
                elif key in ("replica", "replicas"):
                    in_replica = True
                    if value:
                        replica_lines.append(value)
            elif in_replica:
                replica_lines.append(l)
        replica: dict[str, str] = {}
        for l in replica_lines:
            m = re.match(r"^\s*-?\s*([A-Za-z0-9_-]+):\s*(.*)$", l)
            if m and m.group(1) not in replica:
                replica[m.group(1)] = _unquote(m.group(2))
        result.append({"path": db_path, "replica": replica})
    return result


def expand(value: str, env: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        name = m.group(1) or m.group(3)
        default = m.group(2)
        if name in env:
            return env[name]
        return default if default is not None else m.group(0)

    return re.sub(r"\$\{(\w+)(?::-([^}]*))?\}|\$(\w+)", repl, value)


def container_db_paths() -> dict[str, str]:
    """コンテナ内でアプリが使う DB のパス: 起動手順の代入 > Dockerfile の ENV > アプリの既定。"""
    env = dict(DEFAULTS)
    if DOCKERFILE.exists():
        for line in DOCKERFILE.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*ENV\s+(.+)$", line)
            if not m:
                continue
            rest = m.group(1).strip()
            if "=" in rest.split()[0]:
                for tok in shlex.split(rest):
                    if "=" in tok:
                        k, v = tok.split("=", 1)
                        if k in env:
                            env[k] = v
            else:
                k, _, v = rest.partition(" ")
                if k in env:
                    env[k] = _unquote(v)
    if ENTRYPOINT.exists():
        text = ENTRYPOINT.read_text(encoding="utf-8")
        for k in list(env):
            m = re.search(
                rf"^\s*(?:export\s+)?{k}=[\"']?(?:\$\{{{k}:-)?([^\"'}}\s]+)", text, re.M
            )
            if m:
                env[k] = m.group(1)
    return env


def _destination(replica: dict[str, str], env: dict[str, str]) -> tuple[str, str]:
    """(バケットを表す文字列, バケット内の場所)。"""
    if replica.get("url"):
        url = expand(replica["url"], env)
        m = re.match(r"^gs://([^/]+)/?(.*)$", url)
        assert m, f"複製先の url が gs:// の形でない: {url}"
        return m.group(1), m.group(2)
    assert replica.get("type", "").lower() in ("gcs", "gs"), (
        f"複製先が GCS でない: {replica}"
    )
    assert replica.get("bucket"), f"GCS の複製先に bucket がない: {replica}"
    return expand(replica["bucket"], env), expand(replica.get("path", ""), env)


def test_ac1_config_file_exists():
    assert LITESTREAM_YML.exists(), f"Litestream の設定がない: {LITESTREAM_YML}"


def test_ac1_two_dbs_defined_with_gcs_replica_each():
    text = LITESTREAM_YML.read_text(encoding="utf-8")
    dbs = parse_dbs(text)
    env = container_db_paths()
    resolved = {posixpath.normpath(expand(d["path"], env)) for d in dbs if d["path"]}

    assert len(dbs) == 2, f"DB の定義が2つでない: {dbs}"
    for d in dbs:
        assert d["path"], f"DB の path がない: {d}"
        assert d["replica"], f"複製先がない: {d}"
        _destination(d["replica"], env)  # GCS であること
    assert resolved == {
        posixpath.normpath(env["LEARNING_DB_PATH"]),
        posixpath.normpath(env["TUTOR_DB_PATH"]),
    }, f"設定の DB パスが、アプリの DB パスと一致しない: {resolved} vs {env}"


def test_ac1_learning_and_tutor_replicas_are_separate_locations():
    text = LITESTREAM_YML.read_text(encoding="utf-8")
    env = container_db_paths()
    by_name = {}
    for d in parse_dbs(text):
        by_name[posixpath.basename(posixpath.normpath(expand(d["path"], env)))] = d

    assert set(by_name) == {"learning.db", "tutor.db"}, by_name
    # バケット名は環境変数 DB_REPLICA_BUCKET から来る(設定か起動手順が参照している)
    entry = ENTRYPOINT.read_text(encoding="utf-8") if ENTRYPOINT.exists() else ""
    assert "DB_REPLICA_BUCKET" in text or "DB_REPLICA_BUCKET" in entry
    # 2つの複製先は同じ場所ではなく、片方がもう片方の下にもない
    env_b = dict(env, DB_REPLICA_BUCKET="b")
    b1, p1 = _destination(by_name["learning.db"]["replica"], env_b)
    b2, p2 = _destination(by_name["tutor.db"]["replica"], env_b)
    assert (b1, p1) != (b2, p2), "2つの DB の複製先が同じ"
    if b1 == b2:
        n1, n2 = p1.strip("/"), p2.strip("/")
        assert n1 and n2, "同じバケットなのに、場所(path)で分かれていない"
        assert not (n1 == n2 or n1.startswith(n2 + "/") or n2.startswith(n1 + "/")), (
            f"複製先が入れ子になっている: {p1} / {p2}"
        )
