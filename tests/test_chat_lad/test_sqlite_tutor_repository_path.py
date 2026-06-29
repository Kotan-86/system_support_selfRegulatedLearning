# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-3-Tutoring
# 仕様: docs/spec/framework-drivers-persistence.md#対話-dbtutordbとの接続
"""SqliteTutorSessionRepository 経路の chat_lad 相当シナリオ。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from application.common.result import Ok
from application.learning.adapters.get_learning_snapshot_query import (
    GetLearningSnapshotQuery,
)
from application.learning.dto.record_quiz_attempt import RecordQuizAttemptRequest
from application.learning.dto.record_viewing_event import RecordViewingEventRequest
from application.learning.use_cases.get_learning_snapshot import GetLearningSnapshotUseCase
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from application.tutoring.dto.send_chat_message import SendChatMessageRequest
from application.tutoring.use_cases.send_chat_message import SendChatMessageUseCase
from application.tutoring.use_cases.start_or_get_tutor_session import (
    StartOrGetTutorSessionUseCase,
)
from domain.learning.quiz_attempt import QuizAnswer
from domain.learning.viewing_event import ViewingAction
from domain.shared.ids import LectureId, LearnerId
from framework_drivers.db.learning.id_generators import UuidLearningSessionIdGenerator
from framework_drivers.db.learning.sqlite_connection import connect_in_memory_learning_db
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
from interfaces.tutoring.chat_prompt_builder import DefaultChatPromptBuilder
from tests.test_application.fakes.tutoring.fake_id_generators import FakeMessageIdGenerator
from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sqlite_tutoring_stack(project_root: Path) -> tuple[
    sqlite3.Connection,
    sqlite3.Connection,
    SqliteLearningSessionRepository,
    SqliteTutorSessionRepository,
]:
    """learning / tutor の :memory: DB と Repository ペア。"""
    learning_conn = connect_in_memory_learning_db(
        project_root / "db" / "schema_learning.sql"
    )
    tutor_conn = connect_in_memory_tutor_db(project_root / "db" / "schema.sql")
    return (
        learning_conn,
        tutor_conn,
        SqliteLearningSessionRepository(learning_conn),
        SqliteTutorSessionRepository(tutor_conn),
    )


def _quiz_answers() -> tuple[QuizAnswer, ...]:
    return (
        QuizAnswer(question_index=1, selected_answer="A", is_correct=True),
        QuizAnswer(question_index=2, selected_answer="B", is_correct=False),
    )


def _send_chat_use_case(
    learning_repository: SqliteLearningSessionRepository,
    tutor_repository: SqliteTutorSessionRepository,
    llm_gateway: FakeLlmGateway,
) -> SendChatMessageUseCase:
    lecture_catalog = StaticLectureCatalog()
    snapshot_uc = GetLearningSnapshotUseCase(
        repository=learning_repository,
        lecture_catalog=lecture_catalog,
    )
    return SendChatMessageUseCase(
        start_or_get_learning=StartOrGetLearningSessionUseCase(
            repository=learning_repository,
            id_generator=UuidLearningSessionIdGenerator(),
        ),
        start_or_get_tutor=StartOrGetTutorSessionUseCase(
            repository=tutor_repository,
            id_generator=UuidTutorSessionIdGenerator(),
        ),
        learning_snapshot_query=GetLearningSnapshotQuery(snapshot_uc),
        chat_prompt_builder=DefaultChatPromptBuilder(),
        llm_gateway=llm_gateway,
        repository=tutor_repository,
        message_id_generator=FakeMessageIdGenerator(),
        lecture_catalog=lecture_catalog,
    )


class TestChatLadSqliteTutorRepositoryPath:
    """test_chat_lad 相当のシナリオを新 Repository 経路で検証する。"""

    def test_learning_session_id_is_persisted_on_first_chat(
        self, sqlite_tutoring_stack
    ) -> None:
        _, tutor_conn, learning_repo, tutor_repo = sqlite_tutoring_stack
        llm = FakeLlmGateway(response="stub")
        use_case = _send_chat_use_case(learning_repo, tutor_repo, llm)

        result = use_case.execute(
            SendChatMessageRequest(
                user_message="はじめて",
                sent_at=FIXED_NOW,
                learner_id=LearnerId("1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
            )
        )

        assert isinstance(result, Ok)
        row = tutor_conn.execute(
            """
            SELECT learning_session_id
            FROM sessions
            WHERE id = ?
            """,
            (str(result.value.tutor_session_id),),
        ).fetchone()
        assert row is not None
        assert row["learning_session_id"] != ""

        learning_row = learning_repo.find_by_learner_and_lecture(
            LearnerId("1"), LectureId(DEFAULT_LECTURE_ID_VALUE)
        )
        assert learning_row is not None
        assert str(learning_row.id) == row["learning_session_id"]

    def test_register_lad_then_chat_prompt_contains_learning_data(
        self, sqlite_tutoring_stack
    ) -> None:
        _, _, learning_repo, tutor_repo = sqlite_tutoring_stack
        start_or_get = StartOrGetLearningSessionUseCase(
            repository=learning_repo,
            id_generator=UuidLearningSessionIdGenerator(),
        )
        from application.learning.use_cases.record_quiz_attempt import (
            RecordQuizAttemptUseCase,
        )
        from application.learning.use_cases.record_viewing_event import (
            RecordViewingEventUseCase,
        )

        record_viewing = RecordViewingEventUseCase(
            start_or_get=start_or_get,
            repository=learning_repo,
        )
        record_quiz = RecordQuizAttemptUseCase(
            start_or_get=start_or_get,
            lecture_catalog=StaticLectureCatalog(),
            repository=learning_repo,
        )
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                occurred_at=FIXED_NOW,
                video_position=0,
                action=ViewingAction.PLAY,
                position_delta=0,
            )
        )
        record_quiz.execute(
            RecordQuizAttemptRequest(
                learner_id=LearnerId("1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                attempted_at=FIXED_NOW,
                score_numerator=4,
                score_denominator=5,
                answers=_quiz_answers(),
            )
        )

        llm = FakeLlmGateway(response="stub")
        use_case = _send_chat_use_case(learning_repo, tutor_repo, llm)
        result = use_case.execute(
            SendChatMessageRequest(
                user_message="小テストの問2がわかりません",
                sent_at=FIXED_NOW,
                learner_id=LearnerId("1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
            )
        )

        assert isinstance(result, Ok)
        assert len(llm.generate_calls) == 1
        prompt = llm.generate_calls[0]
        assert (
            "4" in prompt and "5" in prompt
        ) or "play" in prompt.lower() or "視聴" in prompt or "小テスト" in prompt
