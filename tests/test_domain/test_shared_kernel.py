# 仕様: docs/spec/domain-model.md#Shared Kernel — Value Object
# 仕様: docs/spec/domain-implementation-plan.md Phase 0
"""
Shared Kernel の ID 型（Value Object）とパッケージ骨格の単体テスト。

Phase 0 では Entity 本体は未実装。ID 型の不変条件と domain/ パッケージ境界を定義する。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from domain.shared.ids import (
    LectureId,
    LearnerId,
    LearningSessionId,
    MessageId,
    ParticipantProgramId,
    ProgramId,
    QuizAttemptId,
    TutorSessionId,
    ViewingEventId,
)

# Phase 0 で実装対象の全 ID 型（空文字拒否・等価性テスト用）
ALL_ID_TYPES: tuple[type, ...] = (
    LearnerId,
    LectureId,
    LearningSessionId,
    ViewingEventId,
    QuizAttemptId,
    TutorSessionId,
    MessageId,
    ParticipantProgramId,
    ProgramId,
)

FORBIDDEN_DOMAIN_IMPORTS = frozenset({"flask", "sqlite3", "vertexai"})


class TestSharedKernelIdTypes:
    """Shared Kernel ID 型の不変条件を検証する。"""

    @pytest.mark.parametrize("id_type", ALL_ID_TYPES, ids=lambda t: t.__name__)
    def test_accepts_non_empty_string(self, id_type: type) -> None:
        """非空文字列で ID を生成できる。"""
        id_value = id_type("sample-id-1")
        assert str(id_value) == "sample-id-1" or id_value == "sample-id-1"

    @pytest.mark.parametrize("id_type", ALL_ID_TYPES, ids=lambda t: t.__name__)
    def test_rejects_empty_string(self, id_type: type) -> None:
        """空文字列は ValueError で拒否される。"""
        with pytest.raises(ValueError):
            id_type("")

    @pytest.mark.parametrize("id_type", ALL_ID_TYPES, ids=lambda t: t.__name__)
    def test_same_value_is_equal(self, id_type: type) -> None:
        """同一値の ID は等価（==）である。"""
        first = id_type("same-id")
        second = id_type("same-id")
        assert first == second

    @pytest.mark.parametrize("id_type", ALL_ID_TYPES, ids=lambda t: t.__name__)
    def test_different_value_is_not_equal(self, id_type: type) -> None:
        """異なる値の ID は等価でない。"""
        assert id_type("id-a") != id_type("id-b")


class TestDomainPackageSkeleton:
    """domain/ パッケージ骨格とインフラ依存の不在を検証する。"""

    def test_domain_package_imports(self) -> None:
        """domain ルートと各境界づけられたコンテキストが import 可能である。"""
        import domain
        import domain.learning
        import domain.research_export
        import domain.tutoring

        assert domain is not None
        assert domain.learning is not None
        assert domain.tutoring is not None
        assert domain.research_export is not None

    def test_domain_has_no_flask_sqlite3_or_vertexai_imports(self) -> None:
        """domain/ 配下の Python ソースに Flask / sqlite3 / vertexai の import がない。"""
        domain_root = Path(__file__).resolve().parents[2] / "domain"
        assert domain_root.is_dir(), "domain/ パッケージが存在すること"

        violations: list[str] = []
        for py_file in sorted(domain_root.rglob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                module_name: str | None = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split(".")[0]
                        if module_name in FORBIDDEN_DOMAIN_IMPORTS:
                            rel = py_file.relative_to(domain_root)
                            violations.append(f"{rel}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module_name = node.module.split(".")[0]
                    if module_name in FORBIDDEN_DOMAIN_IMPORTS:
                        rel = py_file.relative_to(domain_root)
                        violations.append(f"{rel}: from {node.module} import ...")

        assert violations == [], "禁止 import が検出された:\n" + "\n".join(violations)
