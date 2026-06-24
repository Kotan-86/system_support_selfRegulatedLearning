# 仕様: docs/spec/interfaces-layer.md#Catalog（静的文）
"""LearnerTypeCatalog の単体テスト。"""
from __future__ import annotations

import pytest

from interfaces.learning.catalog.learner_type_catalog import StaticLearnerTypeCatalog


class TestStaticLearnerTypeCatalog:
    """4 タイプの lookup を検証する。"""

    @pytest.mark.parametrize(
        ("type_code", "type_name"),
        [
            ("advanced", "Advanced"),
            ("diligent", "Diligent"),
            ("indifferent", "Indifferent"),
            ("persistent", "Persistent"),
        ],
    )
    def test_lookup_returns_entry_for_known_type(
        self, type_code: str, type_name: str
    ) -> None:
        catalog = StaticLearnerTypeCatalog()

        entry = catalog.lookup(type_code)

        assert entry is not None
        assert entry.type_code == type_code
        assert entry.type_name == type_name
        assert entry.characteristics
        assert entry.motivation
        assert entry.performance

    def test_lookup_returns_none_for_unknown_type(self) -> None:
        catalog = StaticLearnerTypeCatalog()

        assert catalog.lookup("unknown") is None
