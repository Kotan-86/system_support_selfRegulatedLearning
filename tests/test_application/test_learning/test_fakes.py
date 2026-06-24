# 仕様: docs/spec/application-usecase.md#Port 一覧（Learning コンテキスト）
"""Learning Port の Fake / InMemory 実装の単体テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

from domain.learning.lecture import Lecture
from domain.learning.learning_session import LearningSession
from domain.learning.learning_snapshot import LearningSnapshot
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.shared.ids import (
    LectureId,
    LearnerId,
    LearningSessionId,
    QuizAttemptId,
    ViewingEventId,
)

from tests.test_application.fakes.learning.fake_id_generators import (
    FakeLearningSessionIdGenerator,
    FakeQuizAttemptIdGenerator,
    FakeViewingEventIdGenerator,
)
from tests.test_application.fakes.learning.fake_learning_snapshot_query import (
    FakeLearningSnapshotQuery,
)
from tests.test_application.fakes.learning.fake_lecture_catalog import FakeLectureCatalog
from tests.test_application.fakes.learning.in_memory_learning_session_repository import (
    InMemoryLearningSessionRepository,
)

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _sample_session(
    *,
    session_id: str = "session-1",
    learner_id: str = "learner-1",
    lecture_id: str = "lecture-1",
) -> LearningSession:
    return LearningSession(
        id=LearningSessionId(session_id),
        learner_id=LearnerId(learner_id),
        lecture_id=LectureId(lecture_id),
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


class TestInMemoryLearningSessionRepository:
    """InMemoryLearningSessionRepository の永続化動作を検証する。"""

    def test_find_by_learner_and_lecture_returns_none_when_empty(self) -> None:
        repository = InMemoryLearningSessionRepository()
        result = repository.find_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId("lecture-1")
        )
        assert result is None

    def test_save_and_find_round_trip(self) -> None:
        repository = InMemoryLearningSessionRepository()
        session = _sample_session()
        repository.save(session)

        found = repository.find_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId("lecture-1")
        )
        assert found == session
        assert repository.save_count == 1

    def test_save_upserts_existing_session(self) -> None:
        repository = InMemoryLearningSessionRepository()
        session = _sample_session()
        repository.save(session)

        updated = _sample_session(session_id="session-1")
        repository.save(updated)

        assert repository.find_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId("lecture-1")
        ) == updated
        assert repository.save_count == 2
        assert len(repository.all_sessions()) == 1

    def test_list_by_learner_returns_only_matching_sessions(self) -> None:
        session_a = _sample_session(session_id="session-a", lecture_id="lecture-a")
        session_b = _sample_session(
            session_id="session-b",
            learner_id="learner-1",
            lecture_id="lecture-b",
        )
        session_other = _sample_session(
            session_id="session-c",
            learner_id="learner-2",
            lecture_id="lecture-a",
        )
        repository = InMemoryLearningSessionRepository(
            sessions=(session_a, session_b, session_other)
        )

        result = repository.list_by_learner(LearnerId("learner-1"))
        assert set(result) == {session_a, session_b}


class TestFakeLectureCatalog:
    """FakeLectureCatalog の参照動作を検証する。"""

    def test_find_by_id_returns_none_when_not_registered(self) -> None:
        catalog = FakeLectureCatalog()
        assert catalog.find_by_id(LectureId("missing")) is None

    def test_find_by_id_returns_registered_lecture(self) -> None:
        lecture = _sample_lecture()
        catalog = FakeLectureCatalog(lectures=(lecture,))
        assert catalog.find_by_id(LectureId("lecture-1")) == lecture

    def test_add_registers_lecture(self) -> None:
        catalog = FakeLectureCatalog()
        lecture = _sample_lecture(lecture_id="lecture-2")
        catalog.add(lecture)
        assert catalog.find_by_id(LectureId("lecture-2")) == lecture


class TestFakeIdGenerators:
    """Fake ID Generator の連番生成を検証する。"""

    def test_learning_session_id_generator_returns_sequential_ids(self) -> None:
        generator = FakeLearningSessionIdGenerator(prefix="ls", start=1)
        assert generator.next_id() == LearningSessionId("ls-1")
        assert generator.next_id() == LearningSessionId("ls-2")

    def test_viewing_event_id_generator_returns_sequential_ids(self) -> None:
        generator = FakeViewingEventIdGenerator(prefix="ve", start=10)
        assert generator.next_id() == ViewingEventId("ve-10")
        assert generator.next_id() == ViewingEventId("ve-11")

    def test_quiz_attempt_id_generator_returns_sequential_ids(self) -> None:
        generator = FakeQuizAttemptIdGenerator(prefix="qa", start=3)
        assert generator.next_id() == QuizAttemptId("qa-3")
        assert generator.next_id() == QuizAttemptId("qa-4")


class TestFakeLearningSnapshotQuery:
    """FakeLearningSnapshotQuery の Snapshot 返却を検証する。"""

    def test_get_by_learner_and_lecture_returns_configured_snapshot(self) -> None:
        snapshot = LearningSnapshot(
            session_id=LearningSessionId("session-1"),
            learner_id=LearnerId("learner-1"),
            lecture_id=LectureId("lecture-1"),
            viewing_events=(),
            latest_quiz_attempt=None,
            quiz_answers=(),
        )
        query = FakeLearningSnapshotQuery()
        query.set_snapshot(LearnerId("learner-1"), LectureId("lecture-1"), snapshot)

        result = query.get_by_learner_and_lecture(
            LearnerId("learner-1"), LectureId("lecture-1")
        )
        assert result == snapshot

    def test_get_by_learner_and_lecture_raises_when_not_configured(self) -> None:
        query = FakeLearningSnapshotQuery()
        try:
            query.get_by_learner_and_lecture(
                LearnerId("learner-1"), LectureId("lecture-1")
            )
            raise AssertionError("expected KeyError")
        except KeyError as exc:
            assert "learner-1" in str(exc)
