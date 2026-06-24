# 仕様: docs/spec/application-usecase.md#Port 一覧（Learning コンテキスト）
"""Learning コンテキストの Port 契約。"""
from application.learning.ports.id_generators import (
    LearningSessionIdGenerator,
    QuizAttemptIdGenerator,
    ViewingEventIdGenerator,
)
from application.learning.ports.learning_session_repository import (
    LearningSessionRepository,
)
from application.learning.ports.learning_snapshot_query import LearningSnapshotQuery
from application.learning.ports.lecture_catalog import LectureCatalog

__all__ = [
    "LearningSessionRepository",
    "LectureCatalog",
    "LearningSessionIdGenerator",
    "ViewingEventIdGenerator",
    "QuizAttemptIdGenerator",
    "LearningSnapshotQuery",
]
