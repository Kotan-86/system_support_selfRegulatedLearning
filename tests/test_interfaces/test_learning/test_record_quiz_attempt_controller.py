# 仕様: docs/spec/interfaces-layer.md#既存-API-対応表
"""RecordQuizAttemptController の単体テスト。"""
from __future__ import annotations

from application.common.errors import ErrorCode
from application.learning.use_cases.record_quiz_attempt import RecordQuizAttemptUseCase
from domain.learning.lecture import Lecture
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.shared.ids import LectureId
from interfaces.learning.controllers.record_quiz_attempt_controller import (
    RecordQuizAttemptController,
)
from interfaces.learning.presenters.record_quiz_attempt_presenter import (
    RecordQuizAttemptPresenter,
)
from interfaces.learning.view_models.errors import ErrorViewModel
from interfaces.learning.view_models.record_responses import (
    RecordQuizAttemptSuccessViewModel,
)
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)
from tests.test_application.test_learning.test_record_quiz_attempt import _use_case


def _gas_quiz_attempt_payload(**overrides: object) -> dict[str, object]:
    """GAS quizForm.gs が送る想定の JSON と同一の形。"""
    payload: dict[str, object] = {
        "participant_id": "1",
        "timestamp": "2026-01-20T11:30:38",
        "score_numerator": 4,
        "score_denominator": 5,
        "answers": [
            {
                "question_index": 1,
                "selected_answer": "統計学の視点：データの分布",
                "is_correct": 1,
            },
            {
                "question_index": 2,
                "selected_answer": "大きさと向き",
                "is_correct": 1,
            },
            {"question_index": 3, "selected_answer": "2次元", "is_correct": 1},
            {
                "question_index": 4,
                "selected_answer": "1つのベクトルの終点を別のベクトルの始点に重ね、新たなベクトルを作る",
                "is_correct": 1,
            },
            {"question_index": 5, "selected_answer": "スケーリング", "is_correct": 0},
        ],
    }
    payload.update(overrides)
    return payload


def _controller(
    use_case: RecordQuizAttemptUseCase | None = None,
) -> RecordQuizAttemptController:
    return RecordQuizAttemptController(
        use_case=use_case or _use_case(),
        presenter=RecordQuizAttemptPresenter(),
    )


class TestRecordQuizAttemptController:
    """Controller の ingress と UC 連携を検証する。"""

    def test_gas_payload_returns_success_view_model(self) -> None:
        repository = InMemoryLearningSessionRepository()
        controller = _controller(_use_case(repository=repository))

        result = controller.execute(_gas_quiz_attempt_payload())

        assert isinstance(result, RecordQuizAttemptSuccessViewModel)
        assert result.ok is True
        assert len(repository.all_sessions()) == 1
        assert len(repository.all_sessions()[0].quiz_attempts) == 1

    def test_accepts_created_at_instead_of_timestamp(self) -> None:
        repository = InMemoryLearningSessionRepository()
        controller = _controller(_use_case(repository=repository))
        payload = _gas_quiz_attempt_payload()
        del payload["timestamp"]
        payload["created_at"] = "2026-01-20T11:30:38"

        result = controller.execute(payload)

        assert isinstance(result, RecordQuizAttemptSuccessViewModel)

    def test_converts_is_correct_zero_and_one_to_bool(self) -> None:
        repository = InMemoryLearningSessionRepository()
        controller = _controller(_use_case(repository=repository))

        result = controller.execute(_gas_quiz_attempt_payload())

        assert isinstance(result, RecordQuizAttemptSuccessViewModel)
        answers = repository.all_sessions()[0].quiz_attempts[0].answers
        assert answers[0].is_correct is True
        assert answers[4].is_correct is False

    def test_empty_participant_id_returns_validation_error_view_model(self) -> None:
        controller = _controller()

        result = controller.execute(_gas_quiz_attempt_payload(participant_id=""))

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.VALIDATION_ERROR.value
        assert result.status_kind.value == "validation"

    def test_missing_answers_returns_validation_error_view_model(self) -> None:
        controller = _controller()
        payload = _gas_quiz_attempt_payload()
        del payload["answers"]

        result = controller.execute(payload)

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.VALIDATION_ERROR.value
        assert "answers" in result.message

    def test_lecture_not_found_returns_not_found_error_view_model(self) -> None:
        repository = InMemoryLearningSessionRepository()
        missing_lecture = Lecture.create(
            id=LectureId("lecture-missing"),
            title="存在しない講義",
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
        use_case = _use_case(
            repository=repository,
            lectures=(missing_lecture,),
        )
        controller = _controller(use_case)

        result = controller.execute(
            _gas_quiz_attempt_payload(lecture_id="lecture-unknown")
        )

        assert isinstance(result, ErrorViewModel)
        assert result.error_code == ErrorCode.LECTURE_NOT_FOUND.value
        assert result.status_kind.value == "not_found"
