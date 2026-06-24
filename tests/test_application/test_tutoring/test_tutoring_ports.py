# 仕様: docs/spec/application-usecase.md#Port 一覧（Tutoring コンテキスト）
"""Tutoring Port ABC の契約検証。"""
from __future__ import annotations

import inspect

from application.learning.ports.learning_snapshot_query import LearningSnapshotQuery
from application.tutoring.ports.chat_prompt_builder import ChatPromptBuilder
from application.tutoring.ports.id_generators import MessageIdGenerator, TutorSessionIdGenerator
from application.tutoring.ports.llm_gateway import LlmGateway
from application.tutoring.ports.tutor_session_repository import TutorSessionRepository
from tests.test_application.fakes.learning.fake_learning_snapshot_query import (
    FakeLearningSnapshotQuery,
)
from tests.test_application.fakes.tutoring.fake_chat_prompt_builder import FakeChatPromptBuilder
from tests.test_application.fakes.tutoring.fake_id_generators import (
    FakeMessageIdGenerator,
    FakeTutorSessionIdGenerator,
)
from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway
from tests.test_application.fakes.tutoring.in_memory_tutor_session_repository import (
    InMemoryTutorSessionRepository,
)


class TestTutoringPortContracts:
    """Fake 実装が Port ABC を満たすことを検証する。"""

    def test_in_memory_repository_is_tutor_session_repository(self) -> None:
        repository = InMemoryTutorSessionRepository()
        assert isinstance(repository, TutorSessionRepository)

    def test_fake_id_generators_satisfy_port_contracts(self) -> None:
        assert isinstance(FakeTutorSessionIdGenerator(), TutorSessionIdGenerator)
        assert isinstance(FakeMessageIdGenerator(), MessageIdGenerator)

    def test_fake_learning_snapshot_query_is_learning_snapshot_query(self) -> None:
        query = FakeLearningSnapshotQuery()
        assert isinstance(query, LearningSnapshotQuery)

    def test_fake_chat_prompt_builder_is_chat_prompt_builder(self) -> None:
        builder = FakeChatPromptBuilder()
        assert isinstance(builder, ChatPromptBuilder)

    def test_fake_llm_gateway_is_llm_gateway(self) -> None:
        gateway = FakeLlmGateway()
        assert isinstance(gateway, LlmGateway)

    def test_tutor_session_repository_declares_required_methods(self) -> None:
        methods = {
            name
            for name, member in inspect.getmembers(TutorSessionRepository)
            if getattr(member, "__isabstractmethod__", False)
        }
        assert methods == {
            "find_by_id",
            "find_by_learning_session_id",
            "list_all",
            "save",
        }

    def test_id_generators_declare_next_id(self) -> None:
        for port in (TutorSessionIdGenerator, MessageIdGenerator):
            methods = {
                name
                for name, member in inspect.getmembers(port)
                if getattr(member, "__isabstractmethod__", False)
            }
            assert methods == {"next_id"}

    def test_chat_prompt_builder_declares_build(self) -> None:
        methods = {
            name
            for name, member in inspect.getmembers(ChatPromptBuilder)
            if getattr(member, "__isabstractmethod__", False)
        }
        assert methods == {"build"}

    def test_llm_gateway_declares_generate(self) -> None:
        methods = {
            name
            for name, member in inspect.getmembers(LlmGateway)
            if getattr(member, "__isabstractmethod__", False)
        }
        assert methods == {"generate"}
