# 仕様: docs/spec/application-usecase.md#Port 一覧（Learning コンテキスト）
"""Learning Port のテスト用 Fake / InMemory 実装。"""
from tests.test_application.fakes.learning.fake_id_generators import (
    FakeLearningSessionIdGenerator,
    FakeQuizAttemptIdGenerator,
    FakeViewingEventIdGenerator,
)
from tests.test_application.fakes.learning.fake_learning_snapshot_query import (
    FakeLearningSnapshotQuery,
)
from tests.test_application.fakes.learning.fake_lecture_catalog import FakeLectureCatalog
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)

__all__ = [
    "InMemoryLearningSessionRepository",
    "FakeLectureCatalog",
    "FakeLearningSessionIdGenerator",
    "FakeViewingEventIdGenerator",
    "FakeQuizAttemptIdGenerator",
    "FakeLearningSnapshotQuery",
]
