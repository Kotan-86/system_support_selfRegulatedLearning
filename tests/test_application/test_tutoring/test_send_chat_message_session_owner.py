# 仕様: docs/spec/participant-login.md#3-参加者の特定fr-52 (AC15: ユースケースの層)
# 仕様: docs/spec/application-error-handling.md#SendChatMessage
"""SendChatMessageUseCase: 他の学習者の対話セッションには書き込まない(30-T2)。

`tutor_session_id` の対話セッションが `learner_id` の学習者のものでないときは、
存在しないセッションと同じ `TutorSessionNotFoundError` を返す。
"""
from __future__ import annotations

from application.common.errors import TutorSessionNotFoundError
from application.common.result import Err, Ok
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)
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
from tests.test_application.test_tutoring.test_send_chat_message import (
    _request,
    _send_chat_use_case,
)


def _world():
    learning_repo = InMemoryLearningSessionRepository()
    tutor_repo = InMemoryTutorSessionRepository()
    student = FakeStudentModelGateway()
    pedagogical = FakePedagogicalModelGateway()
    interface = FakeInterfaceModelGateway(response="reply")
    use_case = _send_chat_use_case(
        learning_repository=learning_repo,
        tutor_repository=tutor_repo,
        student_model=student,
        pedagogical_model=pedagogical,
        interface_model=interface,
    )
    return use_case, tutor_repo, student, pedagogical, interface


class TestAc15SessionOwner:
    def test_ac15_another_learners_tutor_session_is_not_found_and_not_written(self) -> None:
        use_case, tutor_repo, student, pedagogical, interface = _world()
        first = use_case.execute(_request(user_message="Bの質問", learner_id="learner-B"))
        assert isinstance(first, Ok)
        session_id = str(first.value.tutor_session_id)
        stored_before = tutor_repo.find_by_id(first.value.tutor_session_id)
        calls_before = (
            len(student.interpret_calls),
            len(pedagogical.select_move_calls),
            len(interface.generate_calls),
        )
        saves_before = tutor_repo.save_count

        result = use_case.execute(
            _request(user_message="Aが割り込む", learner_id="learner-A", tutor_session_id=session_id)
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, TutorSessionNotFoundError)
        assert tutor_repo.find_by_id(first.value.tutor_session_id) == stored_before
        assert tutor_repo.save_count == saves_before
        assert (
            len(student.interpret_calls),
            len(pedagogical.select_move_calls),
            len(interface.generate_calls),
        ) == calls_before

    def test_ac15_the_error_is_the_same_kind_as_for_a_nonexistent_session(self) -> None:
        use_case, _, _, _, _ = _world()
        first = use_case.execute(_request(user_message="Bの質問", learner_id="learner-B"))
        assert isinstance(first, Ok)

        foreign = use_case.execute(
            _request(
                user_message="x",
                learner_id="learner-A",
                tutor_session_id=str(first.value.tutor_session_id),
            )
        )
        missing = use_case.execute(
            _request(user_message="x", learner_id="learner-A", tutor_session_id="missing-tutor")
        )

        assert isinstance(foreign, Err) and isinstance(missing, Err)
        assert type(foreign.error) is type(missing.error)
        assert foreign.error.code == missing.error.code

    def test_ac15_the_owner_can_continue_the_session(self) -> None:
        use_case, tutor_repo, _, _, _ = _world()
        first = use_case.execute(_request(user_message="1通目", learner_id="learner-B"))
        assert isinstance(first, Ok)

        second = use_case.execute(
            _request(
                user_message="2通目",
                learner_id="learner-B",
                tutor_session_id=str(first.value.tutor_session_id),
            )
        )

        assert isinstance(second, Ok)
        assert second.value.tutor_session_id == first.value.tutor_session_id
        session = tutor_repo.find_by_id(first.value.tutor_session_id)
        assert len(session.messages) == 4

    def test_ac15_the_owner_check_uses_the_learner_not_the_lecture(self) -> None:
        use_case, _, _, _, _ = _world()
        first = use_case.execute(_request(user_message="Bの質問", learner_id="learner-B"))
        assert isinstance(first, Ok)

        result = use_case.execute(
            _request(
                user_message="x",
                learner_id="learner-A",
                lecture_id="lecture-1",
                tutor_session_id=str(first.value.tutor_session_id),
            )
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, TutorSessionNotFoundError)
