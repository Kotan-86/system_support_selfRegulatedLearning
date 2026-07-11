# 仕様: docs/spec/application-usecase.md#Port 一覧（Tutoring コンテキスト）
"""Tutoring Port の Fake / InMemory 実装の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from domain.learning.lecture import Lecture
from domain.learning.learning_snapshot import LearningSnapshot
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.shared.ids import (
    LectureId,
    LearnerId,
    LearningSessionId,
    MessageId,
    TutorSessionId,
)
from domain.tutoring.message import Message, MessageRole
from domain.tutoring.tutor_session import TutorSession

from tests.test_application.fakes.tutoring.fake_chat_prompt_builder import FakeChatPromptBuilder
from tests.test_application.fakes.tutoring.fake_id_generators import (
    FakeMessageIdGenerator,
    FakeTutorSessionIdGenerator,
)
from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway
from tests.test_application.fakes.tutoring.in_memory_tutor_session_repository import (
    InMemoryTutorSessionRepository,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _sample_tutor_session(
    *,
    session_id: str = "tutor-1",
    learning_session_id: str = "learning-1",
) -> TutorSession:
    return TutorSession(
        id=TutorSessionId(session_id),
        learning_session_id=LearningSessionId(learning_session_id),
        started_at=FIXED_NOW,
    )


def _sample_lecture(*, lecture_id: str = "lecture-1") -> Lecture:
    return Lecture.create(
        id=LectureId(lecture_id),
        title="サンプル講義",
        video_url="https://example.com/video.mp4",
        srt_path="/path/to/subtitles.srt",
        quiz_definition=QuizDefinition(
            questions=(
                Question(
                    index=1,
                    text="問1",
                    choices=("A", "B"),
                    correct_answer="A",
                ),
            )
        ),
    )


def _sample_snapshot() -> LearningSnapshot:
    return LearningSnapshot(
        session_id=LearningSessionId("learning-1"),
        learner_id=LearnerId("learner-1"),
        lecture_id=LectureId("lecture-1"),
        viewing_events=(),
        latest_quiz_attempt=None,
        quiz_answers=(),
    )


class TestInMemoryTutorSessionRepository:
    """InMemoryTutorSessionRepository の永続化動作を検証する。"""

    def test_find_by_id_returns_none_when_empty(self) -> None:
        repository = InMemoryTutorSessionRepository()
        assert repository.find_by_id(TutorSessionId("missing")) is None

    def test_find_by_learning_session_id_returns_none_when_empty(self) -> None:
        repository = InMemoryTutorSessionRepository()
        assert (
            repository.find_by_learning_session_id(LearningSessionId("learning-1"))
            is None
        )

    def test_save_and_find_round_trip(self) -> None:
        repository = InMemoryTutorSessionRepository()
        session = _sample_tutor_session()
        repository.save(session)

        assert repository.find_by_id(TutorSessionId("tutor-1")) == session
        assert (
            repository.find_by_learning_session_id(LearningSessionId("learning-1"))
            == session
        )
        assert repository.save_count == 1

    def test_save_upserts_existing_session(self) -> None:
        repository = InMemoryTutorSessionRepository()
        session = _sample_tutor_session()
        repository.save(session)

        updated = session.append_message(
            message_id=MessageId("msg-1"),
            role=MessageRole.USER,
            content="hello",
            created_at=FIXED_NOW,
        )
        repository.save(updated)

        assert repository.find_by_id(TutorSessionId("tutor-1")) == updated
        assert repository.save_count == 2
        assert len(repository.all_sessions()) == 1

    def test_list_all_returns_all_saved_sessions(self) -> None:
        session_a = _sample_tutor_session(session_id="tutor-a", learning_session_id="ls-a")
        session_b = _sample_tutor_session(session_id="tutor-b", learning_session_id="ls-b")
        repository = InMemoryTutorSessionRepository(sessions=(session_a, session_b))

        assert set(repository.list_all()) == {session_a, session_b}


class TestFakeIdGenerators:
    """Fake ID Generator の連番生成を検証する。"""

    def test_tutor_session_id_generator_returns_sequential_ids(self) -> None:
        generator = FakeTutorSessionIdGenerator(prefix="ts", start=1)
        assert generator.next_id() == TutorSessionId("ts-1")
        assert generator.next_id() == TutorSessionId("ts-2")

    def test_message_id_generator_returns_sequential_ids(self) -> None:
        generator = FakeMessageIdGenerator(prefix="msg", start=5)
        assert generator.next_id() == MessageId("msg-5")
        assert generator.next_id() == MessageId("msg-6")


class TestFakeChatPromptBuilder:
    """FakeChatPromptBuilder のプロンプト記録を検証する。"""

    def test_build_returns_configured_prompt_and_records_call(self) -> None:
        builder = FakeChatPromptBuilder(prompt="test-prompt")
        snapshot = _sample_snapshot()
        lecture = _sample_lecture()
        message = Message.create(
            id=MessageId("msg-1"),
            role=MessageRole.USER,
            content="previous",
            created_at=FIXED_NOW,
        )

        result = builder.build(snapshot, (message,), "new message", lecture)

        assert result == "test-prompt"
        assert len(builder.build_calls) == 1
        call = builder.build_calls[0]
        assert call.snapshot == snapshot
        assert call.messages == (message,)
        assert call.user_message == "new message"
        assert call.lecture == lecture

    def test_set_prompt_changes_return_value(self) -> None:
        builder = FakeChatPromptBuilder()
        builder.set_prompt("updated-prompt")
        result = builder.build(_sample_snapshot(), (), "hi", _sample_lecture())
        assert result == "updated-prompt"


class TestFakeLlmGateway:
    """FakeLlmGateway の固定応答と呼び出し記録を検証する。"""

    def test_generate_returns_configured_response_and_records_prompt(self) -> None:
        gateway = FakeLlmGateway(response="assistant reply")
        result = gateway.generate("input prompt")
        assert result == "assistant reply"
        assert gateway.generate_calls == ["input prompt"]

    def test_set_response_changes_return_value(self) -> None:
        gateway = FakeLlmGateway()
        gateway.set_response("new reply")
        assert gateway.generate("any") == "new reply"

    def test_generate_json_returns_configured_dict_and_records_prompt(self) -> None:
        payload = {"dialogue_move": "JOINT_EVIDENCE_CHECK"}
        gateway = FakeLlmGateway(json_response=payload)
        result = gateway.generate_json("json prompt", schema_hint="hint")
        assert result == payload
        assert gateway.generate_json_calls == [("json prompt", "hint")]

    def test_generate_json_returns_stage_defaults_when_not_forced(self) -> None:
        gateway = FakeLlmGateway()

        student = gateway.generate_json("# ITS Student Model (Stage 1)\n...")
        pedagogical = gateway.generate_json("# ITS Pedagogical Model (Stage 2)\n...")

        assert student["utterance_type"] == "VAGUE_MEMORY"
        assert pedagogical["dialogue_move"] == "JOINT_EVIDENCE_CHECK"
        assert pedagogical["interface_instructions"]
