# 仕様: docs/spec/interfaces-layer.md#import-禁止
"""interfaces パッケージの import 制約を検証する。"""
from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_IMPORT_ROOTS = frozenset({"flask", "sqlite3", "vertexai"})


def _collect_import_roots(source: str) -> set[str]:
    tree = ast.parse(source)
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


class TestForbiddenImports:
    """interfaces/ が禁止モジュールを import しないことを検証する。"""

    def test_interfaces_package_does_not_import_forbidden_modules(self) -> None:
        interfaces_root = Path(__file__).resolve().parents[2] / "interfaces"
        violations: list[str] = []

        for path in sorted(interfaces_root.rglob("*.py")):
            roots = _collect_import_roots(path.read_text(encoding="utf-8"))
            forbidden = roots & FORBIDDEN_IMPORT_ROOTS
            if forbidden:
                rel = path.relative_to(interfaces_root.parent)
                violations.append(f"{rel}: {sorted(forbidden)}")

        assert violations == []
