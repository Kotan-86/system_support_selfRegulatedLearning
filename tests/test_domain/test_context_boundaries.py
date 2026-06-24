# 仕様: docs/spec/domain-model.md#境界づけられたコンテキスト
# 仕様: docs/spec/domain-implementation-plan.md Phase 5
"""
コンテキスト間 import ルールのテスト。

Tutoring は Learning Entity を直接 import せず、LearningSnapshot のみ参照可能。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TUTORING_DIR = PROJECT_ROOT / "domain" / "tutoring"

FORBIDDEN_LEARNING_ENTITY_MODULES = {
    "domain.learning.learning_session",
    "domain.learning.viewing_event",
    "domain.learning.quiz_attempt",
    "domain.learning.lecture",
    "domain.learning.quiz_definition",
}

ALLOWED_LEARNING_READ_MODEL_MODULES = {
    "domain.learning.learning_snapshot",
}


def _python_files_under(path: Path) -> list[Path]:
    return sorted(path.rglob("*.py"))


def _imported_modules(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class TestContextBoundaries:
    """Tutoring コンテキストが Learning Entity を直接 import しないことを検証する。"""

    def test_tutoring_does_not_import_learning_entities(self) -> None:
        """domain/tutoring/ が Learning Entity モジュールを import していない。"""
        violations: list[str] = []
        for py_file in _python_files_under(TUTORING_DIR):
            imported = _imported_modules(py_file)
            forbidden = imported & FORBIDDEN_LEARNING_ENTITY_MODULES
            if forbidden:
                rel = py_file.relative_to(PROJECT_ROOT)
                violations.append(f"{rel}: {sorted(forbidden)}")
        assert violations == []

    def test_tutoring_may_import_learning_snapshot_read_model(self) -> None:
        """LearningSnapshot（Read Model）の import は許可される（現状未使用でも可）。"""
        # 許可リストが定義されていることの smoke test
        assert "domain.learning.learning_snapshot" in ALLOWED_LEARNING_READ_MODEL_MODULES

    def test_domain_package_has_no_infrastructure_imports(self) -> None:
        """domain/ 配下に Flask / sqlite3 / vertexai の import がない。"""
        forbidden_roots = {"flask", "sqlite3", "vertexai", "google.cloud"}
        domain_dir = PROJECT_ROOT / "domain"
        violations: list[str] = []
        for py_file in _python_files_under(domain_dir):
            imported = _imported_modules(py_file)
            bad = {name for name in imported if name.split(".")[0] in forbidden_roots}
            if bad:
                rel = py_file.relative_to(PROJECT_ROOT)
                violations.append(f"{rel}: {sorted(bad)}")
        assert violations == []

    def test_research_export_has_no_entity_modules(self) -> None:
        """Research Export パッケージに Entity ファイルが存在しない。"""
        research_export_dir = PROJECT_ROOT / "domain" / "research_export"
        entity_like = [
            path.name
            for path in research_export_dir.glob("*.py")
            if path.name != "__init__.py"
        ]
        assert entity_like == []
