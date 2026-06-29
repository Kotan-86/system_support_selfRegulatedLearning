# 仕様: docs/spec/framework-drivers-persistence.md#id-生成mapper--repository
# 仕様: docs/spec/application-usecase.md#TutorSessionIdGenerator
"""Tutoring コンテキストの SQLite Adapter 向け ID 生成。"""
from __future__ import annotations

import uuid

from application.tutoring.ports.id_generators import (
    MessageIdGenerator,
    TutorSessionIdGenerator,
)
from domain.shared.ids import MessageId, TutorSessionId


class UuidMessageIdGenerator(MessageIdGenerator):
    """UUID 文字列の MessageId を生成する。"""

    def next_id(self) -> MessageId:
        return MessageId(str(uuid.uuid4()))


class UuidTutorSessionIdGenerator(TutorSessionIdGenerator):
    """UUID 文字列の TutorSessionId を生成する。"""

    def next_id(self) -> TutorSessionId:
        return TutorSessionId(str(uuid.uuid4()))
