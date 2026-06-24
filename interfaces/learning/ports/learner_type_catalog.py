# 仕様: docs/spec/interfaces-layer.md#Catalog（静的文）
"""学習者タイプの静的テキスト参照 Port。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LearnerTypeCatalogEntry:
    """type_code に対応する表示用静的文。"""

    type_code: str
    type_name: str
    characteristics: str
    motivation: str
    performance: str


class LearnerTypeCatalog(Protocol):
    """研究用の固定テキストを返す。"""

    def lookup(self, type_code: str) -> LearnerTypeCatalogEntry | None:
        """未知の type_code は None。"""
