# 仕様: docs/spec/framework-drivers-layer.md#Composition-Root
# 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-4-platform-配線
"""Composition Root — Controller / Use Case / Adapter を 1 箇所で組み立てる。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from application.learning.adapters.get_learning_snapshot_query import (
    GetLearningSnapshotQuery,
)
from application.learning.use_cases.get_learning_snapshot import GetLearningSnapshotUseCase
from application.learning.use_cases.record_quiz_attempt import RecordQuizAttemptUseCase
from application.learning.use_cases.record_viewing_event import RecordViewingEventUseCase
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from application.tutoring.ports.llm_gateway import LlmGateway
from application.tutoring.use_cases.send_chat_message import SendChatMessageUseCase
from application.tutoring.use_cases.start_or_get_tutor_session import (
    StartOrGetTutorSessionUseCase,
)
from framework_drivers.db.learning.id_generators import UuidLearningSessionIdGenerator
from framework_drivers.db.learning.sqlite_learning_session_repository import (
    SqliteLearningSessionRepository,
)
from framework_drivers.db.learning.static_lecture_catalog import StaticLectureCatalog
from framework_drivers.db.tutoring.id_generators import (
    UuidMessageIdGenerator,
    UuidTutorSessionIdGenerator,
)
from framework_drivers.db.tutoring.sqlite_tutor_session_repository import (
    SqliteTutorSessionRepository,
)
from framework_drivers.external.vertex.vertex_llm_gateway import VertexLlmGateway
from framework_drivers.external.youtube.youtube_video_duration_resolver import (
    YoutubeVideoDurationResolver,
)
from interfaces.learning.catalog.learner_type_catalog import StaticLearnerTypeCatalog
from interfaces.learning.classifiers.rule_based_learner_type_classifier import (
    RuleBasedLearnerTypeClassifier,
)
from interfaces.learning.controllers.get_last_updated_controller import (
    GetLastUpdatedController,
)
from interfaces.learning.controllers.get_learning_snapshot_controller import (
    GetLearningSnapshotController,
)
from interfaces.learning.controllers.record_quiz_attempt_controller import (
    RecordQuizAttemptController,
)
from interfaces.learning.controllers.record_viewing_event_controller import (
    RecordViewingEventController,
)
from interfaces.learning.ports.video_duration_resolver import VideoDurationResolver
from interfaces.learning.presenters.last_updated_presenter import LastUpdatedPresenter
from interfaces.learning.presenters.lad_dashboard_presenter import LadDashboardPresenter
from interfaces.learning.presenters.record_quiz_attempt_presenter import (
    RecordQuizAttemptPresenter,
)
from interfaces.learning.presenters.record_viewing_event_presenter import (
    RecordViewingEventPresenter,
)
from interfaces.tutoring.chat_prompt_builder import DefaultChatPromptBuilder
from interfaces.tutoring.controllers.send_chat_message_controller import (
    SendChatMessageController,
)
from interfaces.tutoring.presenters.chat_response_presenter import ChatResponsePresenter

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_TUTOR_SCHEMA = _PROJECT_ROOT / "db" / "schema.sql"
_LEARNING_SCHEMA = _PROJECT_ROOT / "db" / "schema_learning.sql"


def get_tutor_db_path() -> Path:
    """対話 DB パス（db.config 経由）。"""
    from db.config import get_tutor_db_path as _get

    return _get()


def get_learning_db_path() -> Path:
    """学習 DB パス（db.config 経由）。"""
    from db.config import get_learning_db_path as _get

    return _get()


def init_databases() -> None:
    """tutor.db / learning.db をスキーマ適用済みで用意する。"""
    from framework_drivers.db.learning.sqlite_connection import (
        apply_learning_schema,
        connect_learning_db,
    )
    from framework_drivers.db.tutoring.sqlite_connection import (
        apply_tutor_schema,
        connect_tutor_db,
    )

    tutor_path = get_tutor_db_path()
    learning_path = get_learning_db_path()
    tutor_path.parent.mkdir(parents=True, exist_ok=True)
    learning_path.parent.mkdir(parents=True, exist_ok=True)

    tutor_conn = connect_tutor_db(tutor_path)
    apply_tutor_schema(tutor_conn, _TUTOR_SCHEMA)
    tutor_conn.close()

    learning_conn = connect_learning_db(learning_path)
    apply_learning_schema(learning_conn, _LEARNING_SCHEMA)
    learning_conn.close()


def reset_databases() -> None:
    """tutor.db / learning.db を削除してから空の DB を再作成する。"""
    for path in (get_tutor_db_path(), get_learning_db_path()):
        if path.exists():
            path.unlink()
    init_databases()


def build_video_duration_resolver() -> VideoDurationResolver:
    """本番用 VideoDurationResolver（YouTube Data API + キャッシュ）を構築する。"""
    return YoutubeVideoDurationResolver()


def build_llm_gateway() -> LlmGateway:
    """本番用 LlmGateway（Vertex AI）を構築する。"""
    return VertexLlmGateway()


def _lecture_catalog() -> StaticLectureCatalog:
    return StaticLectureCatalog()


def _learning_repository(
    connection: sqlite3.Connection,
) -> SqliteLearningSessionRepository:
    return SqliteLearningSessionRepository(connection)


def _tutor_repository(connection: sqlite3.Connection) -> SqliteTutorSessionRepository:
    return SqliteTutorSessionRepository(connection)


def _start_or_get_learning_use_case(
    connection: sqlite3.Connection,
) -> StartOrGetLearningSessionUseCase:
    return StartOrGetLearningSessionUseCase(
        repository=_learning_repository(connection),
        id_generator=UuidLearningSessionIdGenerator(),
    )


def _get_learning_snapshot_use_case(
    connection: sqlite3.Connection,
) -> GetLearningSnapshotUseCase:
    return GetLearningSnapshotUseCase(
        repository=_learning_repository(connection),
        lecture_catalog=_lecture_catalog(),
    )


def build_get_learning_snapshot_controller(
    connection: sqlite3.Connection,
    *,
    video_duration_resolver: VideoDurationResolver | None = None,
) -> GetLearningSnapshotController:
    """SqliteLearningSessionRepository から GetLearningSnapshotController を組み立てる。"""
    lecture_catalog = _lecture_catalog()
    use_case = _get_learning_snapshot_use_case(connection)
    presenter = LadDashboardPresenter(
        catalog=StaticLearnerTypeCatalog(),
        classifier=RuleBasedLearnerTypeClassifier(),
    )
    resolver = (
        video_duration_resolver
        if video_duration_resolver is not None
        else build_video_duration_resolver()
    )
    return GetLearningSnapshotController(
        use_case=use_case,
        presenter=presenter,
        lecture_catalog=lecture_catalog,
        video_duration_resolver=resolver,
    )


def build_get_last_updated_controller(
    connection: sqlite3.Connection,
) -> GetLastUpdatedController:
    """GetLearningSnapshotUseCase を再利用する LastUpdated Controller。"""
    return GetLastUpdatedController(
        use_case=_get_learning_snapshot_use_case(connection),
        presenter=LastUpdatedPresenter(),
    )


def build_record_viewing_event_controller(
    connection: sqlite3.Connection,
) -> RecordViewingEventController:
    """RecordViewingEventController を組み立てる。"""
    return RecordViewingEventController(
        use_case=RecordViewingEventUseCase(
            start_or_get=_start_or_get_learning_use_case(connection),
            repository=_learning_repository(connection),
        ),
        presenter=RecordViewingEventPresenter(),
    )


def build_record_quiz_attempt_controller(
    connection: sqlite3.Connection,
) -> RecordQuizAttemptController:
    """RecordQuizAttemptController を組み立てる。"""
    lecture_catalog = _lecture_catalog()
    return RecordQuizAttemptController(
        use_case=RecordQuizAttemptUseCase(
            start_or_get=_start_or_get_learning_use_case(connection),
            lecture_catalog=lecture_catalog,
            repository=_learning_repository(connection),
        ),
        presenter=RecordQuizAttemptPresenter(),
    )


def build_send_chat_message_controller(
    *,
    learning_connection: sqlite3.Connection,
    tutor_connection: sqlite3.Connection,
    llm_gateway: LlmGateway | None = None,
) -> SendChatMessageController:
    """SendChatMessageController を組み立てる。"""
    lecture_catalog = _lecture_catalog()
    learning_repository = _learning_repository(learning_connection)
    tutor_repository = _tutor_repository(tutor_connection)
    snapshot_use_case = _get_learning_snapshot_use_case(learning_connection)
    gateway = llm_gateway if llm_gateway is not None else build_llm_gateway()

    use_case = SendChatMessageUseCase(
        start_or_get_learning=_start_or_get_learning_use_case(learning_connection),
        start_or_get_tutor=StartOrGetTutorSessionUseCase(
            repository=tutor_repository,
            id_generator=UuidTutorSessionIdGenerator(),
        ),
        learning_snapshot_query=GetLearningSnapshotQuery(snapshot_use_case),
        chat_prompt_builder=DefaultChatPromptBuilder(),
        llm_gateway=gateway,
        repository=tutor_repository,
        message_id_generator=UuidMessageIdGenerator(),
        lecture_catalog=lecture_catalog,
    )
    return SendChatMessageController(
        use_case=use_case,
        presenter=ChatResponsePresenter(),
    )
