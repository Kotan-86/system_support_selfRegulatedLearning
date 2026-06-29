# 仕様: docs/spec/interfaces-layer.md#default_lecture
"""participant_id → lecture_id 解決の単体テスト。"""
from __future__ import annotations

import pytest

from application.common.errors import ValidationError
from application.common.result import Err, Ok
from domain.shared.ids import LectureId
from interfaces.common.default_lecture import DEFAULT_LECTURE_ID_VALUE
from interfaces.common.ingress import parse_lecture_id_for_participant
from interfaces.common.learner_lecture_mapping import (
    resolve_lecture_id_for_participant,
)


class TestResolveLectureIdForParticipant:
    """resolve_lecture_id_for_participant の解決優先順位を検証する。"""

    @pytest.mark.parametrize(
        ("participant_id", "expected"),
        [
            ("1", "lecture-1"),
            ("2", "lecture-2"),
            ("3", "lecture-3"),
        ],
    )
    def test_maps_near_term_participants(
        self, participant_id: str, expected: str
    ) -> None:
        result = resolve_lecture_id_for_participant(participant_id)

        assert isinstance(result, Ok)
        assert result.value == LectureId(expected)

    def test_falls_back_to_default_for_unknown_participant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DEFAULT_LECTURE_ID", raising=False)

        result = resolve_lecture_id_for_participant("learner-1")

        assert isinstance(result, Ok)
        assert result.value == LectureId(DEFAULT_LECTURE_ID_VALUE)

    def test_explicit_lecture_id_overrides_map(self) -> None:
        result = resolve_lecture_id_for_participant("2", "lecture-3")

        assert isinstance(result, Ok)
        assert result.value == LectureId("lecture-3")

    def test_rejects_empty_explicit_lecture_id(self) -> None:
        result = resolve_lecture_id_for_participant("1", "")

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)
        assert "lecture_id" in result.error.message


class TestParseLectureIdForParticipant:
    """ingress ラッパが resolve に委譲することを検証する。"""

    def test_delegates_to_resolve(self) -> None:
        result = parse_lecture_id_for_participant("2")

        assert isinstance(result, Ok)
        assert result.value == LectureId("lecture-2")
