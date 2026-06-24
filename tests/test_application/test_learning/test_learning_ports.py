# 仕様: docs/spec/application-usecase.md#Port 一覧（Learning コンテキスト）
"""Learning Port ABC の契約検証。"""
from __future__ import annotations

import inspect

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


class TestLearningPortContracts:
    """Fake 実装が Port ABC を満たすことを検証する。"""

    def test_in_memory_repository_is_learning_session_repository(self) -> None:
        repository = InMemoryLearningSessionRepository()
        assert isinstance(repository, LearningSessionRepository)

    def test_fake_lecture_catalog_is_lecture_catalog(self) -> None:
        catalog = FakeLectureCatalog()
        assert isinstance(catalog, LectureCatalog)

    def test_fake_id_generators_satisfy_port_contracts(self) -> None:
        assert isinstance(FakeLearningSessionIdGenerator(), LearningSessionIdGenerator)
        assert isinstance(FakeViewingEventIdGenerator(), ViewingEventIdGenerator)
        assert isinstance(FakeQuizAttemptIdGenerator(), QuizAttemptIdGenerator)

    def test_fake_learning_snapshot_query_is_learning_snapshot_query(self) -> None:
        query = FakeLearningSnapshotQuery()
        assert isinstance(query, LearningSnapshotQuery)

    def test_learning_session_repository_declares_required_methods(self) -> None:
        methods = {
            name
            for name, member in inspect.getmembers(LearningSessionRepository)
            if getattr(member, "__isabstractmethod__", False)
        }
        assert methods == {
            "find_by_learner_and_lecture",
            "list_by_learner",
            "save",
        }

    def test_lecture_catalog_declares_find_by_id(self) -> None:
        methods = {
            name
            for name, member in inspect.getmembers(LectureCatalog)
            if getattr(member, "__isabstractmethod__", False)
        }
        assert methods == {"find_by_id"}

    def test_id_generators_declare_next_id(self) -> None:
        for port in (
            LearningSessionIdGenerator,
            ViewingEventIdGenerator,
            QuizAttemptIdGenerator,
        ):
            methods = {
                name
                for name, member in inspect.getmembers(port)
                if getattr(member, "__isabstractmethod__", False)
            }
            assert methods == {"next_id"}

    def test_learning_snapshot_query_declares_get_by_learner_and_lecture(self) -> None:
        methods = {
            name
            for name, member in inspect.getmembers(LearningSnapshotQuery)
            if getattr(member, "__isabstractmethod__", False)
        }
        assert methods == {"get_by_learner_and_lecture"}
