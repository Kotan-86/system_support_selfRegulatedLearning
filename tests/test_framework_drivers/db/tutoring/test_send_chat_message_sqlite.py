# 仕様: docs/spec/application-usecase.md#SendChatMessage
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-3-Tutoring
"""SendChatMessageUseCase と SQLite Repository / Fake LLM の統合テスト。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

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
from application.tutoring.use_cases.send_chat_message import (
    FIRST_MESSAGE_CANNED_RESPONSE,
    SendChatMessageUseCase,
)
from application.tutoring.use_cases.start_or_get_tutor_session import (
    StartOrGetTutorSessionUseCase,
)
from domain.learning.learning_snapshot import LearningSnapshot
from domain.learning.quiz_attempt import QuizAnswer
from domain.learning.viewing_event import ViewingAction
from domain.shared.ids import LectureId, LearnerId, TutorSessionId
from domain.tutoring.message import MessageRole
from framework_drivers.db.learning.id_generators import UuidLearningSessionIdGenerator
from framework_drivers.db.learning.sqlite_learning_session_repository import (
    SqliteLearningSessionRepository,
)
from framework_drivers.db.learning.static_lecture_catalog import StaticLectureCatalog
from framework_drivers.db.tutoring.id_generators import UuidTutorSessionIdGenerator
from framework_drivers.db.tutoring.sqlite_tutor_session_repository import (
    SqliteTutorSessionRepository,
)
from interfaces.common.default_lecture import DEFAULT_LECTURE_ID_VALUE
from interfaces.tutoring.chat_prompt_builder import DefaultChatPromptBuilder
from tests.test_application.fakes.tutoring.fake_id_generators import FakeMessageIdGenerator
from tests.test_application.fakes.tutoring.fake_llm_gateway import FakeLlmGateway
from tests.test_framework_drivers.db.learning.test_record_learning_write_sqlite import (
    _five_answers,
    _quiz_use_case,
    _viewing_use_case,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


class _RecordingLearningSnapshotQuery(GetLearningSnapshotQuery):
    """LearningSnapshotQuery 呼び出しを記録する Adapter。"""

    def __init__(self, use_case: GetLearningSnapshotUseCase) -> None:
        super().__init__(use_case)
        self.call_count = 0

    def get_by_learner_and_lecture(
        self, learner_id: LearnerId, lecture_id: LectureId
    ) -> LearningSnapshot:
        self.call_count += 1
        return super().get_by_learner_and_lecture(learner_id, lecture_id)


def _send_chat_use_case(
    *,
    learning_repository: SqliteLearningSessionRepository,
    tutor_repository: SqliteTutorSessionRepository,
    llm_gateway: FakeLlmGateway | None = None,
    snapshot_query: _RecordingLearningSnapshotQuery | None = None,
) -> tuple[SendChatMessageUseCase, _RecordingLearningSnapshotQuery]:
    lecture_catalog = StaticLectureCatalog()
    snapshot_uc = GetLearningSnapshotUseCase(
        repository=learning_repository,
        lecture_catalog=lecture_catalog,
    )
    query = snapshot_query or _RecordingLearningSnapshotQuery(snapshot_uc)
    use_case = SendChatMessageUseCase(
        start_or_get_learning=StartOrGetLearningSessionUseCase(
            repository=learning_repository,
            id_generator=UuidLearningSessionIdGenerator(),
        ),
        start_or_get_tutor=StartOrGetTutorSessionUseCase(
            repository=tutor_repository,
            id_generator=UuidTutorSessionIdGenerator(),
        ),
        learning_snapshot_query=query,
        chat_prompt_builder=DefaultChatPromptBuilder(),
        llm_gateway=llm_gateway or FakeLlmGateway(response="assistant reply"),
        repository=tutor_repository,
        message_id_generator=FakeMessageIdGenerator(),
        lecture_catalog=lecture_catalog,
    )
    return use_case, query


def _request(
    *,
    user_message: str = "こんにちは",
    learner_id: str = "1",
    tutor_session_id: str | None = None,
) -> SendChatMessageRequest:
    return SendChatMessageRequest(
        user_message=user_message,
        sent_at=FIXED_NOW,
        tutor_session_id=(
            TutorSessionId(tutor_session_id) if tutor_session_id is not None else None
        ),
        learner_id=LearnerId(learner_id),
        lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
    )


class TestSendChatMessageWithSqliteRepositories:
    """SendChatMessageUseCase + SQLite + Fake LLM の受入基準。"""

    def test_first_message_composes_sessions_and_persists_messages(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        learning_db_conn: sqlite3.Connection,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        llm = FakeLlmGateway(response="sqlite assistant reply")
        use_case, query = _send_chat_use_case(
            learning_repository=sqlite_learning_session_repository,
            tutor_repository=sqlite_tutor_session_repository,
            llm_gateway=llm,
        )

        result = use_case.execute(_request(user_message="初回メッセージ"))

        assert isinstance(result, Ok)
        assert result.value.assistant_content == "sqlite assistant reply"
        assert query.call_count == 1
        assert len(llm.generate_calls) == 1

        learning_count = learning_db_conn.execute(
            "SELECT COUNT(*) AS cnt FROM learning_sessions"
        ).fetchone()
        tutor_count = tutor_db_conn.execute(
            "SELECT COUNT(*) AS cnt FROM sessions"
        ).fetchone()
        message_count = tutor_db_conn.execute(
            "SELECT COUNT(*) AS cnt FROM messages"
        ).fetchone()
        assert learning_count is not None and int(learning_count["cnt"]) == 1
        assert tutor_count is not None and int(tutor_count["cnt"]) == 1
        assert message_count is not None and int(message_count["cnt"]) == 2

        saved = sqlite_tutor_session_repository.find_by_id(result.value.tutor_session_id)
        assert saved is not None
        assert saved.learning_session_id
        assert len(saved.messages) == 2

    def test_second_message_appends_to_existing_tutor_session(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
        tutor_db_conn: sqlite3.Connection,
    ) -> None:
        llm = FakeLlmGateway(response="first reply")
        use_case, query = _send_chat_use_case(
            learning_repository=sqlite_learning_session_repository,
            tutor_repository=sqlite_tutor_session_repository,
            llm_gateway=llm,
        )

        first = use_case.execute(_request(user_message="1通目"))
        llm.set_response("second reply")
        assert isinstance(first, Ok)

        second = use_case.execute(
            _request(
                user_message="2通目",
                tutor_session_id=str(first.value.tutor_session_id),
            )
        )

        assert isinstance(second, Ok)
        assert second.value.tutor_session_id == first.value.tutor_session_id
        assert second.value.assistant_content == "second reply"
        assert query.call_count == 2

        message_count = tutor_db_conn.execute(
            "SELECT COUNT(*) AS cnt FROM messages"
        ).fetchone()
        assert message_count is not None and int(message_count["cnt"]) == 4

        saved = sqlite_tutor_session_repository.find_by_id(first.value.tutor_session_id)
        assert saved is not None
        assert len(saved.messages) == 4
        assert saved.messages[2].content == "2通目"
        assert saved.messages[3].content == "second reply"

    def test_snapshot_from_learning_db_is_used_before_llm(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
    ) -> None:
        record_viewing = _viewing_use_case(sqlite_learning_session_repository)
        record_quiz = _quiz_use_case(sqlite_learning_session_repository)
        record_viewing.execute(
            RecordViewingEventRequest(
                learner_id=LearnerId("1"),
                lecture_id=LectureId(DEFAULT_LECTURE_ID_VALUE),
                occurred_at=FIXED_NOW,
                video_position=15,
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
                answers=_five_answers(wrong_at=2),
            )
        )

        llm = FakeLlmGateway(response="lad aware reply")
        use_case, query = _send_chat_use_case(
            learning_repository=sqlite_learning_session_repository,
            tutor_repository=sqlite_tutor_session_repository,
            llm_gateway=llm,
        )

        result = use_case.execute(_request(user_message="小テストの問2がわかりません"))

        assert isinstance(result, Ok)
        assert query.call_count == 1
        assert len(llm.generate_calls) == 1
        prompt = llm.generate_calls[0]
        assert "4" in prompt and "5" in prompt
        assert "play" in prompt.lower() or "視聴" in prompt

    def test_digits_only_first_message_skips_llm_but_persists(
        self,
        sqlite_learning_session_repository: SqliteLearningSessionRepository,
        sqlite_tutor_session_repository: SqliteTutorSessionRepository,
    ) -> None:
        llm = FakeLlmGateway()
        use_case, query = _send_chat_use_case(
            learning_repository=sqlite_learning_session_repository,
            tutor_repository=sqlite_tutor_session_repository,
            llm_gateway=llm,
        )

        result = use_case.execute(_request(user_message="12345"))

        assert isinstance(result, Ok)
        assert result.value.assistant_content == FIRST_MESSAGE_CANNED_RESPONSE
        assert query.call_count == 1
        assert llm.generate_calls == []

        saved = sqlite_tutor_session_repository.find_by_id(result.value.tutor_session_id)
        assert saved is not None
        assert len(saved.messages) == 2
        assert saved.messages[0].role is MessageRole.USER
        assert saved.messages[1].content == FIRST_MESSAGE_CANNED_RESPONSE
