# 仕様: docs/spec/interfaces-layer.md#ingress-規約
"""ingress の単体テスト。"""
from __future__ import annotations

import math

import pytest

from application.common.errors import ValidationError
from application.common.result import Err, Ok
from domain.shared.ids import LearnerId, LectureId
from interfaces.common.default_lecture import DEFAULT_LECTURE_ID_VALUE
from interfaces.common.ingress import (
    parse_attempted_at,
    parse_learner_id,
    parse_lecture_id,
    parse_occurred_at,
    parse_position_delta,
    parse_quiz_answers,
    parse_required_int,
    parse_video_position,
    parse_viewing_action,
)


class TestParseLearnerId:
    """participant_id → LearnerId の変換を検証する。"""

    def test_parses_non_empty_participant_id(self) -> None:
        result = parse_learner_id("learner-1")

        assert isinstance(result, Ok)
        assert result.value == LearnerId("learner-1")

    def test_strips_surrounding_whitespace(self) -> None:
        result = parse_learner_id("  learner-1  ")

        assert isinstance(result, Ok)
        assert result.value == LearnerId("learner-1")

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_rejects_empty_participant_id(self, raw: str) -> None:
        result = parse_learner_id(raw)

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert result.error.code.value == "VALIDATION_ERROR"
        assert "participant_id" in result.error.message


class TestParseLectureId:
    """lecture_id → LectureId の変換を検証する。"""

    def test_parses_explicit_lecture_id(self) -> None:
        result = parse_lecture_id("lecture-2")

        assert isinstance(result, Ok)
        assert result.value == LectureId("lecture-2")

    def test_uses_default_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEFAULT_LECTURE_ID", raising=False)

        result = parse_lecture_id(None)

        assert isinstance(result, Ok)
        assert result.value == LectureId(DEFAULT_LECTURE_ID_VALUE)

    def test_rejects_empty_string(self) -> None:
        result = parse_lecture_id("")

        assert isinstance(result, Err)
        assert "lecture_id" in result.error.message

    def test_rejects_blank_string(self) -> None:
        result = parse_lecture_id("   ")

        assert isinstance(result, Err)
        assert "lecture_id" in result.error.message

    def test_can_disable_default_resolution(self) -> None:
        result = parse_lecture_id(None, use_default_when_missing=False)

        assert isinstance(result, Err)
        assert "lecture_id" in result.error.message


class TestViewingSecondsWrappers:
    """viewing_seconds 委譲ラッパを検証する。"""

    def test_parse_video_position_truncates_fraction(self) -> None:
        result = parse_video_position(90.9)

        assert isinstance(result, Ok)
        assert result.value == 90

    def test_parse_position_delta_truncates_fraction(self) -> None:
        result = parse_position_delta(10.5)

        assert isinstance(result, Ok)
        assert result.value == 10

    def test_parse_video_position_rejects_non_finite(self) -> None:
        result = parse_video_position(math.nan)

        assert isinstance(result, Err)
        assert "current_time" in result.error.message

    def test_parse_position_delta_rejects_non_numeric_string(self) -> None:
        result = parse_position_delta("abc")

        assert isinstance(result, Err)
        assert "duration" in result.error.message


class TestParseOccurredAt:
    """time_stamp → occurred_at の変換を検証する。"""

    def test_parses_iso8601_with_z_suffix(self) -> None:
        result = parse_occurred_at("2026-02-23T11:18:42.000Z")

        assert isinstance(result, Ok)
        assert result.value.year == 2026
        assert result.value.month == 2
        assert result.value.day == 23
        assert result.value.hour == 11
        assert result.value.minute == 18
        assert result.value.second == 42

    def test_rejects_missing_value(self) -> None:
        result = parse_occurred_at(None)

        assert isinstance(result, Err)
        assert "time_stamp" in result.error.message


class TestParseAttemptedAt:
    """timestamp → attempted_at の変換を検証する。"""

    def test_parses_local_iso_format(self) -> None:
        result = parse_attempted_at("2026-01-20T11:30:38")

        assert isinstance(result, Ok)
        assert result.value.hour == 11
        assert result.value.minute == 30


class TestParseViewingAction:
    """action → ViewingAction の変換を検証する。"""

    def test_parses_play(self) -> None:
        from domain.learning.viewing_event import ViewingAction

        result = parse_viewing_action("play")

        assert isinstance(result, Ok)
        assert result.value == ViewingAction.PLAY

    def test_rejects_unknown_action(self) -> None:
        result = parse_viewing_action("invalid")

        assert isinstance(result, Err)
        assert "unknown action" in result.error.message


class TestParseRequiredInt:
    """必須整数フィールドの変換を検証する。"""

    def test_parses_integer(self) -> None:
        result = parse_required_int(5, field_name="score_numerator")

        assert isinstance(result, Ok)
        assert result.value == 5

    def test_rejects_missing_value(self) -> None:
        result = parse_required_int(None, field_name="score_numerator")

        assert isinstance(result, Err)
        assert "score_numerator" in result.error.message


class TestParseQuizAnswers:
    """answers 配列の変換を検証する。"""

    def test_parses_gas_style_answers(self) -> None:
        result = parse_quiz_answers(
            [
                {
                    "question_index": 1,
                    "selected_answer": "A",
                    "is_correct": 1,
                },
                {
                    "question_index": 2,
                    "selected_answer": "B",
                    "is_correct": 0,
                },
            ]
        )

        assert isinstance(result, Ok)
        assert len(result.value) == 2
        assert result.value[0].is_correct is True
        assert result.value[1].is_correct is False

    def test_rejects_non_list(self) -> None:
        result = parse_quiz_answers({})

        assert isinstance(result, Err)
        assert "answers must be a list" in result.error.message
