# 仕様: docs/spec/interfaces-layer.md#default_lecture
"""近い実験向けの固定 lecture_id 解決。"""
from __future__ import annotations

import os

from domain.shared.ids import LectureId

DEFAULT_LECTURE_ID_VALUE = "lecture-1"
"""API に lecture_id が未導入の間、近い実験で用いる既定講義 ID。"""

ENV_VAR_NAME = "DEFAULT_LECTURE_ID"
"""環境変数で既定講義 ID を上書きする際のキー。"""


def resolve_default_lecture_id() -> LectureId:
    """環境変数または定数から LectureId を解決する。"""
    raw = os.environ.get(ENV_VAR_NAME, DEFAULT_LECTURE_ID_VALUE)
    value = raw.strip()
    if not value:
        value = DEFAULT_LECTURE_ID_VALUE
    return LectureId(value)
