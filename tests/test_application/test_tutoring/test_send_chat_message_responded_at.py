# 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-1 A5 記録の部分, A14)
"""SendChatMessageUseCase が AI 応答の生成を終えた時刻(responded_at)を記録する。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from application.common.result import Ok
from application.learning.adapters.get_learning_snapshot_query import (
    GetLearningSnapshotQuery,
)
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from application.tutoring.dto.send_chat_message import SendChatMessageRequest
from application.tutoring.use_cases.run_tutoring_pipeline import RunTutoringPipelineUseCase
from application.tutoring.use_cases.send_chat_message import SendChatMessageUseCase
from domain.shared.ids import LearnerId, LectureId
from tests.test_application.fakes.learning.fake_id_generators import (
    FakeLearningSessionIdGenerator,
)
from tests.test_application.fakes.learning.fake_lecture_catalog import FakeLectureCatalog
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)
from tests.test_application.fakes.tutoring.fake_id_generators import FakeMessageIdGenerator
from tests.test_application.fakes.tutoring.fake_interface_model_gateway import (
    FakeInterfaceModelGateway,
)
from tests.test_application.fakes.tutoring.fake_pedagogical_model_gateway import (
    FakePedagogicalModelGateway,
)
from tests.test_application.fakes.tutoring.fake_student_model_gateway import (
    FakeStudentModelGateway,
)
from tests.test_application.fakes.tutoring.in_memory_tutor_session_repository import (
    InMemoryTutorSessionRepository,
)
from tests.test_application.test_learning.test_get_learning_snapshot import (
    _get_snapshot_use_case,
    _lecture,
)
from tests.test_application.test_tutoring.test_start_or_get_tutor_session import (
    _use_case as _start_or_get_tutor_use_case,
)

SENT_AT = datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)
RESPONDED_AT = SENT_AT + timedelta(seconds=7)


def _use_case(*, interface, tutor_repo, clock=None) -> SendChatMessageUseCase:
    learning_repo = InMemoryLearningSessionRepository()
    kwargs = {} if clock is None else {"clock": clock}
    return SendChatMessageUseCase(
        start_or_get_learning=StartOrGetLearningSessionUseCase(
            repository=learning_repo,
            id_generator=FakeLearningSessionIdGenerator(),
        ),
        start_or_get_tutor=_start_or_get_tutor_use_case(repository=tutor_repo),
        learning_snapshot_query=GetLearningSnapshotQuery(
            _get_snapshot_use_case(repository=learning_repo)
        ),
        run_tutoring_pipeline=RunTutoringPipelineUseCase(
            student_model=FakeStudentModelGateway(),
            pedagogical_model=FakePedagogicalModelGateway(),
            interface_model=interface,
        ),
        repository=tutor_repo,
        message_id_generator=FakeMessageIdGenerator(),
        lecture_catalog=FakeLectureCatalog(lectures=(_lecture(),)),
        **kwargs,
    )


def _request() -> SendChatMessageRequest:
    return SendChatMessageRequest(
        user_message="こんにちは",
        sent_at=SENT_AT,
        learner_id=LearnerId("learner-1"),
        lecture_id=LectureId("lecture-1"),
    )


class TestRespondedAtRecording:
    def test_a5_assistant_gets_clock_time_user_gets_none_created_at_is_sent_at(
        self,
    ) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        use_case = _use_case(
            interface=FakeInterfaceModelGateway(response="応答"),
            tutor_repo=tutor_repo,
            clock=lambda: RESPONDED_AT,
        )

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        session = tutor_repo.find_by_id(result.value.tutor_session_id)
        assert session is not None
        user, assistant = session.messages
        assert user.responded_at is None
        assert assistant.responded_at == RESPONDED_AT
        # created_at は従来どおり、受け付けた時刻(並び順に使う)
        assert user.created_at == SENT_AT
        assert assistant.created_at == SENT_AT

    def test_a5_clock_is_read_after_the_ai_response_is_generated(self) -> None:
        """生成を終えた時刻: 時計は AI 応答の生成の後に読まれる。"""
        interface = FakeInterfaceModelGateway(response="応答")
        generate_calls_seen_by_clock: list[int] = []

        def clock() -> datetime:
            generate_calls_seen_by_clock.append(len(interface.generate_calls))
            return RESPONDED_AT

        use_case = _use_case(
            interface=interface,
            tutor_repo=InMemoryTutorSessionRepository(),
            clock=clock,
        )

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert generate_calls_seen_by_clock, "時計が一度も読まれていない"
        assert all(count == 1 for count in generate_calls_seen_by_clock)

    def test_a5_default_clock_is_real_time_not_the_receipt_time(self) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        use_case = _use_case(
            interface=FakeInterfaceModelGateway(response="応答"),
            tutor_repo=tutor_repo,
        )
        before = datetime.now(timezone.utc)

        result = use_case.execute(_request())

        after = datetime.now(timezone.utc)
        assert isinstance(result, Ok)
        session = tutor_repo.find_by_id(result.value.tutor_session_id)
        assert session is not None
        responded_at = session.messages[1].responded_at
        assert responded_at is not None
        assert responded_at != SENT_AT
        assert before <= responded_at <= after

    def test_a14_response_content_and_message_count_unchanged(self) -> None:
        tutor_repo = InMemoryTutorSessionRepository()
        use_case = _use_case(
            interface=FakeInterfaceModelGateway(response="応答"),
            tutor_repo=tutor_repo,
            clock=lambda: RESPONDED_AT,
        )

        result = use_case.execute(_request())

        assert isinstance(result, Ok)
        assert result.value.assistant_content == "応答"
        session = tutor_repo.find_by_id(result.value.tutor_session_id)
        assert session is not None
        assert [m.content for m in session.messages] == ["こんにちは", "応答"]
