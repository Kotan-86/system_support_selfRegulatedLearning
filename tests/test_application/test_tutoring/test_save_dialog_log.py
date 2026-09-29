# 仕様: docs/spec/dialog-log-save.md#受入基準 (PBI-A-1 A2, A3, A4, A7, A8, A11, A12, A13)
"""SaveDialogLogUseCase: 対話ログの保存(InMemory の Repository で確認)。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from application.common.result import Ok
from application.learning.adapters.get_learning_snapshot_query import (
    GetLearningSnapshotQuery,
)
from application.learning.use_cases.start_or_get_learning_session import (
    StartOrGetLearningSessionUseCase,
)
from application.tutoring.dto.save_dialog_log import EndMethod, SaveDialogLogRequest
from application.tutoring.dto.send_chat_message import SendChatMessageRequest
from application.tutoring.use_cases.run_tutoring_pipeline import RunTutoringPipelineUseCase
from application.tutoring.use_cases.save_dialog_log import SaveDialogLogUseCase
from application.tutoring.use_cases.send_chat_message import SendChatMessageUseCase
from domain.shared.ids import LearnerId, LectureId, TutorSessionId
from domain.tutoring.message import MessageRole
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
from tests.test_application.fakes.tutoring.in_memory_dialog_log_repository import (
    InMemoryDialogLogRepository,
)
from tests.test_application.fakes.tutoring.in_memory_tutor_session_repository import (
    InMemoryTutorSessionRepository,
)
from tests.test_application.test_learning.test_get_learning_snapshot import (
    _get_snapshot_use_case,
    _lecture,
)
from tests.test_application.test_tutoring.test_send_chat_message import (
    _FailingPedagogicalModelGateway,
)
from tests.test_application.test_tutoring.test_start_or_get_tutor_session import (
    _use_case as _start_or_get_tutor_use_case,
)

T0 = datetime(2026, 9, 29, 1, 0, 0, tzinfo=timezone.utc)
SAVE_1 = T0 + timedelta(minutes=5)
SAVE_2 = T0 + timedelta(minutes=30)
LEARNER = "learner-1"
LECTURE = "lecture-1"


class _World:
    """1 つの学習者の、対話と保存を行う組み立て一式。"""

    def __init__(self, *, pedagogical=None) -> None:
        self.learning_repo = InMemoryLearningSessionRepository()
        self.tutor_repo = InMemoryTutorSessionRepository()
        self.dialog_repo = InMemoryDialogLogRepository()
        self.interface = FakeInterfaceModelGateway(response="応答")
        learning_ids = FakeLearningSessionIdGenerator()
        start_learning = StartOrGetLearningSessionUseCase(
            repository=self.learning_repo, id_generator=learning_ids
        )
        start_tutor = _start_or_get_tutor_use_case(repository=self.tutor_repo)
        self.send = SendChatMessageUseCase(
            start_or_get_learning=start_learning,
            start_or_get_tutor=start_tutor,
            learning_snapshot_query=GetLearningSnapshotQuery(
                _get_snapshot_use_case(repository=self.learning_repo)
            ),
            run_tutoring_pipeline=RunTutoringPipelineUseCase(
                student_model=FakeStudentModelGateway(),
                pedagogical_model=pedagogical or FakePedagogicalModelGateway(),
                interface_model=self.interface,
            ),
            repository=self.tutor_repo,
            message_id_generator=FakeMessageIdGenerator(),
            lecture_catalog=FakeLectureCatalog(lectures=(_lecture(),)),
        )
        self.save = SaveDialogLogUseCase(
            start_or_get_learning=start_learning,
            start_or_get_tutor=start_tutor,
            tutor_repository=self.tutor_repo,
            dialog_log_repository=self.dialog_repo,
        )

    def talk(self, user_message: str, ai_reply: str = "応答") -> None:
        self.interface.set_response(ai_reply)
        result = self.send.execute(
            SendChatMessageRequest(
                user_message=user_message,
                sent_at=T0,
                learner_id=LearnerId(LEARNER),
                lecture_id=LectureId(LECTURE),
            )
        )
        assert isinstance(result, Ok), result

    def save_log(self, *, method: EndMethod, at: datetime):
        return self.save.execute(
            SaveDialogLogRequest(
                learner_id=LearnerId(LEARNER),
                lecture_id=LectureId(LECTURE),
                end_method=method,
                received_at=at,
            )
        )


class TestSaveAfterConversation:
    def _two_round_trips(self) -> _World:
        world = _World()
        world.talk("質問1", "回答1")
        world.talk("質問2", "回答2")
        return world

    def test_a2_saves_one_log_with_four_messages_in_order_and_text(self) -> None:
        world = self._two_round_trips()

        result = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_1)

        assert isinstance(result, Ok)
        assert len(world.dialog_repo.logs) == 1
        log = world.dialog_repo.logs[str(result.value.tutor_session_id)]
        assert [m.role for m in log.messages] == [
            MessageRole.USER,
            MessageRole.ASSISTANT,
            MessageRole.USER,
            MessageRole.ASSISTANT,
        ]
        assert [m.content for m in log.messages] == ["質問1", "回答1", "質問2", "回答2"]

    def test_a3_roles_are_only_user_and_assistant(self) -> None:
        world = self._two_round_trips()

        result = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_1)

        log = world.dialog_repo.logs[str(result.value.tutor_session_id)]
        assert {m.role.value for m in log.messages} == {"user", "assistant"}

    def test_a4_identifiers_match_request_and_sessions(self) -> None:
        world = self._two_round_trips()

        result = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_1)

        assert isinstance(result, Ok)
        (learning_session,) = world.learning_repo.all_sessions()
        (tutor_session,) = world.tutor_repo.all_sessions()
        log = world.dialog_repo.logs[str(tutor_session.id)]
        assert log.participant_id == LEARNER
        assert log.lecture_id == LECTURE
        assert log.learning_session_id == str(learning_session.id)
        assert log.tutor_session_id == str(tutor_session.id)
        assert result.value.tutor_session_id == tutor_session.id

    def test_a8_ended_at_is_receipt_time_and_end_method_is_requested_one(self) -> None:
        world = self._two_round_trips()

        result = world.save_log(method=EndMethod.PAGE_LEAVE, at=SAVE_1)

        assert isinstance(result, Ok)
        log = world.dialog_repo.logs[str(result.value.tutor_session_id)]
        assert log.ended_at == SAVE_1
        assert log.end_method is EndMethod.PAGE_LEAVE
        assert result.value.ended_at == SAVE_1
        assert result.value.end_method is EndMethod.PAGE_LEAVE

    def test_a8_end_button_is_recorded_as_end_button(self) -> None:
        world = self._two_round_trips()

        result = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_1)

        log = world.dialog_repo.logs[str(result.value.tutor_session_id)]
        assert log.end_method is EndMethod.END_BUTTON

    def test_a7_failed_round_trip_is_not_in_the_log(self) -> None:
        """AI 応答の生成に失敗した往復(そのユーザーの発言を含む)は、対話ログに含まれない。"""
        world = _World()
        world.talk("成功する質問", "成功する回答")
        # 失敗する Pedagogical Model の送信を、同じ Repository に対して行う(保存されない)。
        send_failing = SendChatMessageUseCase(
            start_or_get_learning=StartOrGetLearningSessionUseCase(
                repository=world.learning_repo,
                id_generator=FakeLearningSessionIdGenerator(),
            ),
            start_or_get_tutor=_start_or_get_tutor_use_case(repository=world.tutor_repo),
            learning_snapshot_query=GetLearningSnapshotQuery(
                _get_snapshot_use_case(repository=world.learning_repo)
            ),
            run_tutoring_pipeline=RunTutoringPipelineUseCase(
                student_model=FakeStudentModelGateway(),
                pedagogical_model=_FailingPedagogicalModelGateway(),
                interface_model=FakeInterfaceModelGateway(),
            ),
            repository=world.tutor_repo,
            message_id_generator=FakeMessageIdGenerator(prefix="fail"),
            lecture_catalog=FakeLectureCatalog(lectures=(_lecture(),)),
        )
        failed = send_failing.execute(
            SendChatMessageRequest(
                user_message="失敗する質問",
                sent_at=T0,
                learner_id=LearnerId(LEARNER),
                lecture_id=LectureId(LECTURE),
            )
        )
        assert not isinstance(failed, Ok)

        result = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_1)

        log = world.dialog_repo.logs[str(result.value.tutor_session_id)]
        assert [m.content for m in log.messages] == ["成功する質問", "成功する回答"]


class TestOneLogPerSessionAndOverwrite:
    def test_a11_saving_twice_in_a_row_keeps_one_log(self) -> None:
        world = _World()
        world.talk("質問", "回答")

        first = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_1)
        second = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_1)

        assert isinstance(first, Ok) and isinstance(second, Ok)
        assert first.value.tutor_session_id == second.value.tutor_session_id
        assert len(world.dialog_repo.logs) == 1

    def test_a12_second_save_after_more_messages_overwrites(self) -> None:
        world = _World()
        world.talk("質問1", "回答1")
        first = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_1)
        assert isinstance(first, Ok)
        world.talk("質問2", "回答2")

        second = world.save_log(method=EndMethod.PAGE_LEAVE, at=SAVE_2)

        assert isinstance(second, Ok)
        assert second.value.tutor_session_id == first.value.tutor_session_id
        assert len(world.dialog_repo.logs) == 1
        log = world.dialog_repo.logs[str(second.value.tutor_session_id)]
        assert [m.content for m in log.messages] == ["質問1", "回答1", "質問2", "回答2"]
        assert log.ended_at == SAVE_2
        assert log.end_method is EndMethod.PAGE_LEAVE


class TestZeroMessages:
    def test_a13_saves_empty_log_and_creates_sessions_when_none_exist(self) -> None:
        world = _World()
        assert world.learning_repo.all_sessions() == ()
        assert world.tutor_repo.all_sessions() == ()

        result = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_1)

        assert isinstance(result, Ok)
        (learning_session,) = world.learning_repo.all_sessions()
        (tutor_session,) = world.tutor_repo.all_sessions()
        assert len(world.dialog_repo.logs) == 1
        log = world.dialog_repo.logs[str(tutor_session.id)]
        assert log.messages == ()
        assert log.participant_id == LEARNER
        assert log.lecture_id == LECTURE
        assert log.learning_session_id == str(learning_session.id)
        assert log.tutor_session_id == str(tutor_session.id)
        assert tutor_session.learning_session_id == learning_session.id
        assert log.ended_at == SAVE_1
        assert log.end_method is EndMethod.END_BUTTON

    def test_a13_later_message_goes_to_the_same_tutor_session(self) -> None:
        world = _World()
        saved = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_1)
        assert isinstance(saved, Ok)

        world.talk("あとからの発言", "あとからの応答")

        (tutor_session,) = world.tutor_repo.all_sessions()
        assert tutor_session.id == saved.value.tutor_session_id
        assert [m.content for m in tutor_session.messages] == [
            "あとからの発言",
            "あとからの応答",
        ]

    def test_a13_existing_session_with_no_messages_is_reused(self) -> None:
        world = _World()
        first = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_1)
        second = world.save_log(method=EndMethod.END_BUTTON, at=SAVE_2)

        assert isinstance(first, Ok) and isinstance(second, Ok)
        assert first.value.tutor_session_id == second.value.tutor_session_id
        assert len(world.learning_repo.all_sessions()) == 1
        assert len(world.tutor_repo.all_sessions()) == 1
        assert len(world.dialog_repo.logs) == 1
        assert isinstance(first.value.tutor_session_id, TutorSessionId)
