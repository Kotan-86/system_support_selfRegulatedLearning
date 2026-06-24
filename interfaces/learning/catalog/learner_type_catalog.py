# 仕様: docs/spec/interfaces-layer.md#Catalog（静的文）
"""4 学習者タイプの静的 Catalog 実装。"""
from __future__ import annotations

from interfaces.learning.ports.learner_type_catalog import (
    LearnerTypeCatalogEntry,
)

_ENTRIES: dict[str, LearnerTypeCatalogEntry] = {
    "advanced": LearnerTypeCatalogEntry(
        type_code="advanced",
        type_name="Advanced",
        characteristics="学習内容を素早く把握し、効率的に視聴を進める傾向がある。",
        motivation="高い学習意欲を持ち、自ら進んで内容を理解しようとする。",
        performance="小テストで高得点を取ることが多い。",
    ),
    "diligent": LearnerTypeCatalogEntry(
        type_code="diligent",
        type_name="Diligent",
        characteristics="丁寧に視聴し、一時停止や巻き戻しを活用して理解を深める。",
        motivation="着実に学習を進める意欲が高く、内容をしっかり確認する。",
        performance="安定した成績を維持する傾向がある。",
    ),
    "indifferent": LearnerTypeCatalogEntry(
        type_code="indifferent",
        type_name="Indifferent",
        characteristics="視聴操作が少なく、受動的に動画を見る傾向がある。",
        motivation="学習への関心が低く、最小限の操作で進めることが多い。",
        performance="小テストの成績は平均以下になりやすい。",
    ),
    "persistent": LearnerTypeCatalogEntry(
        type_code="persistent",
        type_name="Persistent",
        characteristics="繰り返し再生や巻き戻しを行い、理解するまで粘り強く学習する。",
        motivation="困難な内容にも諦めず取り組む意欲がある。",
        performance="時間をかけても最終的には理解し、成績が向上する傾向がある。",
    ),
}


class StaticLearnerTypeCatalog:
    """研究用の固定テキストを保持する Catalog。"""

    def lookup(self, type_code: str) -> LearnerTypeCatalogEntry | None:
        return _ENTRIES.get(type_code)
