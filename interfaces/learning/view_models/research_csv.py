# 仕様: docs/spec/research-lad-csv-download.md#url共有if
"""研究用 CSV ダウンロードの ViewModel(ファイル名と、BOM 付き UTF-8 の本文)。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchCsvViewModel:
    filename: str
    content: bytes
