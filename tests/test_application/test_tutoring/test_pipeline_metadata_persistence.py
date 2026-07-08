# 仕様: docs/spec/application-usecase.md#SendChatMessage
"""パイプラインメタデータの永続化テスト。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from application.common.result import Ok
from application.learning.adapters.get_learning_snapshot_query import (
    GetLearningSnapshotQuery,
)
from application.learning.use_cases.get_learning_snapshot import GetLearningSnapshotUseCase
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from application.tutoring.dto.send_chat_message import SendChatMessageRequest
from application.tutoring.use_cases.run_tutoring_pipeline import RunTutoringPipelineUseCase
from application.tutoring.use_cases.send_chat_message import SendChatMessageUseCase
from application.tutoring.use_cases.start_or_get_tutor_session import (
    StartOrGetTutorSessionUseCase,
)
from domain.shared.ids import LectureId, LearnerId, TutorSessionId
from domain.tutoring.dialogue_move import DialogueMove
from domain.tutoring.learner_utterance_type import LearnerUtteranceType
from domain.tutoring.message import MessageRole
from framework_drivers.db.learning.id_generators import UuidLearningSessionIdGenerator
from framework_drivers.db.learning.sqlite_learning_session_repository import (
    SqliteLearningSessionRepository,
)
from framework_drivers.db.learning.static_lecture_catalog import StaticLectureCatalog
from framework_drivers.db.tutoring.id_generators import UuidTutorSessionIdGenerator
from framework_drivers.db.tutoring.sqlite_connection import connect_in_memory_tutor_db
from framework_drivers.db.tutoring.sqlite_tutor_session_repository import (
    SqliteTutorSessionRepository,
)
from interfaces.common.default_lecture import DEFAULT_LECTURE_ID_VALUE
from tests.test_application.fakes.tutoring.fake_id_generators import FakeMessageIdGenerator
from tests.test_application.fakes.tutoring.fake_interface_model_gateway import (
    FakeInterfaceModelGateway,
)
from tests.test_application.fakes.tutoring.fake_pedagogical_model_gateway import (
    FakePedagogicalModelGateway,
)
from tests.test_application.fakes.tutoring.fake_student_model_gateway import (
    FakeStudentModelGateway,
    sample_updated_state_card,
)

pytest_plugins = ["tests.test_framework_drivers.conftest"]

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _send_chat_use_case_sqlite(
    *,
    tutor_repo: SqliteTutorSessionRepository,
    learning_repo: SqliteLearningSessionRepository,
    student: FakeStudentModelGateway | None = None,
    pedagogical: FakePedagogicalModelGateway | None = None,
    interface: FakeInterfaceModelGateway | None = None,
) -> SendChatMessageUseCase:
    start_learning = StartOrGetLearningSessionUseCase(
        learning_repo,
        UuidLearningSessionIdGenerator(),
    )
    start_tutor = StartOrGetTutorSessionUseCase(
        tutor_repo,
        UuidTutorSessionIdGenerator(),
    )
    snapshot_query = GetLearningSnapshotQuery(
        GetLearningSnapshotUseCase(learning_repo, StaticLectureCatalog())
    )
    student_model = student or FakeStudentModelGateway()
    pedagogical_model = pedagogical or FakePedagogicalModelGateway()
    interface_model = interface or FakeInterfaceModelGateway(response="assistant reply")
    pipeline = RunTutoringPipelineUseCase(
        student_model,
        pedagogical_model,
        interface_model,
    )
    return SendChatMessageUseCase(
        start_learning,
        start_tutor,
        snapshot_query,
        pipeline,
        tutor_repo,
        FakeMessageIdGenerator(),
        StaticLectureCatalog(),
    )


def _request(
    *,
    user_message: str = "小テストについて",
    tutor_session_id: str | None = None,
) -> SendChatMessageRequest:
    return SendChatMessageRequest(
        learner_id=LearnerId("learner-1"),
        lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
        user_message=user_message,
        sent_at=FIXED_NOW,
        tutor_session_id=TutorSessionId(tutor_session_id) if tutor_session_id else None,
    )


class TestPipelineMetadataPersistence:
    """SQLite 経由で VO が round-trip する。"""

    def test_assistant_message_metadata_round_trips_via_sqlite(
        self,
        learning_db_conn: sqlite3.Connection,
        tutor_schema_path: Path,
    ) -> None:
        learning_repo = SqliteLearningSessionRepository(learning_db_conn)
        tutor_repo = SqliteTutorSessionRepository(
            connect_in_memory_tutor_db(tutor_schema_path)
        )
        updated_card = sample_updated_state_card()
        student = FakeStudentModelGateway(
            utterance_type=LearnerUtteranceType.FACT_REQUEST,
            state_card=updated_card,
        )
        pedagogical = FakePedagogicalModelGateway(
            dialogue_move=DialogueMove.ORIENT_SHARED_REVIEW,
        )
        use_case = _send_chat_use_case_sqlite(
            tutor_repo=tutor_repo,
            learning_repo=learning_repo,
            student=student,
            pedagogical=pedagogical,
        )

        result = use_case.execute(_request())
        assert isinstance(result, Ok)

        saved = tutor_repo.find_by_id(result.value.tutor_session_id)
        assert saved is not None
        assert len(saved.messages) == 2
        assert saved.messages[0].utterance_type is None
        assistant = saved.messages[1]
        assert assistant.role is MessageRole.ASSISTANT
        assert assistant.utterance_type is LearnerUtteranceType.FACT_REQUEST
        assert assistant.dialogue_move is DialogueMove.ORIENT_SHARED_REVIEW
        assert assistant.interpretation_state == updated_card

    def test_second_turn_reads_state_card_from_persisted_assistant_message(
        self,
        learning_db_conn: sqlite3.Connection,
        tutor_schema_path: Path,
    ) -> None:
        learning_repo = SqliteLearningSessionRepository(learning_db_conn)
        tutor_repo = SqliteTutorSessionRepository(
            connect_in_memory_tutor_db(tutor_schema_path)
        )
        updated_card = sample_updated_state_card()
        student = FakeStudentModelGateway(state_card=updated_card)
        interface = FakeInterfaceModelGateway(response="first reply")
        use_case = _send_chat_use_case_sqlite(
            tutor_repo=tutor_repo,
            learning_repo=learning_repo,
            student=student,
            interface=interface,
        )

        first = use_case.execute(_request(user_message="1通目"))
        interface.set_response("second reply")
        assert isinstance(first, Ok)

        second = use_case.execute(
            _request(
                user_message="2通目",
                tutor_session_id=str(first.value.tutor_session_id),
            )
        )
        assert isinstance(second, Ok)
        assert len(student.interpret_calls) == 2
        assert student.interpret_calls[1].previous_state_card == updated_card
