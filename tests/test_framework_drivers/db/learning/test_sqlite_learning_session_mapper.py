# 仕様: docs/spec/framework-drivers-persistence.md#mapper-契約what
"""sqlite_learning_session_mapper の受入基準テスト。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.shared.ids import QuizAttemptId, ViewingEventId
from framework_drivers.db.learning.sqlite_learning_session_mapper import (
    SqliteMapperError,
    duration_to_position_delta,
    format_datetime,
    parse_datetime,
    quiz_answer_row_to_quiz_answer,
    quiz_attempt_rows_to_quiz_attempt,
    rows_to_learning_session,
    viewing_log_row_to_viewing_event,
    viewing_event_to_insert_params,
)
from domain.shared.ids import LearningSessionId

FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


class TestViewingLogRowToViewingEvent:
    """viewing_logs 1 行 → ViewingEvent 変換。"""

    def test_play_action_with_zero_duration(self) -> None:
        row = {
            "id": 7,
            "time_stamp": "2026-06-21T12:00:00+00:00",
            "current_time": 120,
            "action": "play",
            "duration": 0.0,
        }

        event = viewing_log_row_to_viewing_event(row)

        assert isinstance(event, ViewingEvent)
        assert event.id == ViewingEventId("7")
        assert event.action is ViewingAction.PLAY
        assert event.position_delta == 0
        assert event.video_position == 120
        assert event.occurred_at == FIXED_NOW

    def test_duration_fraction_truncates_toward_zero(self) -> None:
        row = {
            "id": 1,
            "time_stamp": "2026-06-21T12:00:00+00:00",
            "current_time": 50,
            "action": "forward_skip",
            "duration": 10.5,
        }

        event = viewing_log_row_to_viewing_event(row)

        assert event.position_delta == 10

    @pytest.mark.parametrize(
        ("duration", "expected"),
        [
            (0.0, 0),
            (10.0, 10),
            (10.5, 10),
            (-30.0, -30),
            (-30.7, -30),
        ],
    )
    def test_duration_to_position_delta_examples(
        self, duration: float, expected: int
    ) -> None:
        assert duration_to_position_delta(duration) == expected

    def test_unknown_action_raises_mapper_error(self) -> None:
        row = {
            "id": 1,
            "time_stamp": "2026-06-21T12:00:00+00:00",
            "current_time": 0,
            "action": "invalid_action",
            "duration": 0.0,
        }

        with pytest.raises(SqliteMapperError, match="unknown viewing action"):
            viewing_log_row_to_viewing_event(row)

    def test_invalid_position_delta_for_action_raises_mapper_error(self) -> None:
        row = {
            "id": 1,
            "time_stamp": "2026-06-21T12:00:00+00:00",
            "current_time": 0,
            "action": "play",
            "duration": 5.0,
        }

        with pytest.raises(SqliteMapperError):
            viewing_log_row_to_viewing_event(row)


class TestChildEntityIdRestoration:
    """INTEGER PK から子 Entity ID を復元する。"""

    def test_viewing_event_id_from_integer_pk(self) -> None:
        row = {
            "id": 7,
            "time_stamp": "2026-06-21T12:00:00+00:00",
            "current_time": 0,
            "action": "pause",
            "duration": 0.0,
        }

        event = viewing_log_row_to_viewing_event(row)

        assert event.id == ViewingEventId("7")

    def test_quiz_attempt_id_from_integer_pk(self) -> None:
        attempt_row = {
            "id": 3,
            "created_at": "2026-06-21T12:30:00+00:00",
            "score_numerator": 2,
            "score_denominator": 3,
        }
        answer_row = {
            "question_index": 0,
            "selected_answer": "A",
            "is_correct": 1,
        }

        attempt = quiz_attempt_rows_to_quiz_attempt(attempt_row, (answer_row,))

        assert attempt.id == QuizAttemptId("3")


class TestDatetimeRoundTrip:
    """日時列の ISO 8601 往復。"""

    def test_format_and_parse_datetime(self) -> None:
        formatted = format_datetime(FIXED_NOW)
        restored = parse_datetime(formatted)

        assert formatted == "2026-06-21T12:00:00+00:00"
        assert restored == FIXED_NOW

    def test_viewing_event_write_params_use_iso8601(self) -> None:
        event = ViewingEvent.create(
            id=ViewingEventId("1"),
            occurred_at=FIXED_NOW,
            video_position=10,
            action=ViewingAction.PLAY,
            position_delta=0,
        )

        params = viewing_event_to_insert_params(event, LearningSessionId("session-1"))

        assert params[1] == "2026-06-21T12:00:00+00:00"


class TestQuizAnswerMapping:
    """quiz_attempt_answers 行の変換。"""

    def test_is_correct_zero_and_one(self) -> None:
        correct = quiz_answer_row_to_quiz_answer(
            {"question_index": 0, "selected_answer": "A", "is_correct": 1}
        )
        incorrect = quiz_answer_row_to_quiz_answer(
            {"question_index": 1, "selected_answer": "B", "is_correct": 0}
        )

        assert correct.is_correct is True
        assert incorrect.is_correct is False

    def test_invalid_is_correct_raises_mapper_error(self) -> None:
        with pytest.raises(SqliteMapperError, match="is_correct must be 0 or 1"):
            quiz_answer_row_to_quiz_answer(
                {"question_index": 0, "selected_answer": "A", "is_correct": 2}
            )


class TestAggregateReconstruction:
    """LearningSession 集約の再構成順序。"""

    def test_viewing_events_ordered_by_time_stamp_then_id(self) -> None:
        session_row = {
            "id": "session-1",
            "learner_id": "learner-1",
            "lecture_id": "lecture-1",
            "started_at": "2026-06-21T12:00:00+00:00",
        }
        viewing_rows = (
            {
                "id": 2,
                "time_stamp": "2026-06-21T12:01:00+00:00",
                "current_time": 10,
                "action": "play",
                "duration": 0.0,
            },
            {
                "id": 1,
                "time_stamp": "2026-06-21T12:00:00+00:00",
                "current_time": 0,
                "action": "play",
                "duration": 0.0,
            },
            {
                "id": 3,
                "time_stamp": "2026-06-21T12:00:00+00:00",
                "current_time": 5,
                "action": "pause",
                "duration": 0.0,
            },
        )

        session = rows_to_learning_session(session_row, viewing_rows, (), {})

        assert [event.id for event in session.viewing_events] == [
            ViewingEventId("1"),
            ViewingEventId("3"),
            ViewingEventId("2"),
        ]
