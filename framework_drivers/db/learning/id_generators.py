# 仕様: docs/spec/framework-drivers-persistence.md#id-生成mapper--repository
# 仕様: docs/spec/application-usecase.md#LearningSessionIdGenerator
"""Learning コンテキストの SQLite Adapter 向け ID 生成。"""
from __future__ import annotations

import uuid

from application.learning.ports.id_generators import LearningSessionIdGenerator
from domain.shared.ids import LearningSessionId


class UuidLearningSessionIdGenerator(LearningSessionIdGenerator):
    """UUID 文字列の LearningSessionId を生成する。"""

    def next_id(self) -> LearningSessionId:
        return LearningSessionId(str(uuid.uuid4()))
