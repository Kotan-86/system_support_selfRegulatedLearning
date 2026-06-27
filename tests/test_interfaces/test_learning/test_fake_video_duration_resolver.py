# 仕様: docs/spec/interfaces-layer.md#VideoDurationResolver
"""FakeVideoDurationResolver の単体テスト。"""
from __future__ import annotations

import pytest

from application.common.errors import ValidationError, VideoMetadataGatewayError
from application.common.result import Err, Ok
from domain.learning.lecture import Lecture
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.shared.ids import LectureId
from interfaces.learning.ports.video_duration_resolver import VideoDurationResolver
from tests.test_interfaces.fakes.fake_video_duration_resolver import (
    FakeVideoDurationResolver,
)


def _lecture(*, video_url: str = "https://www.youtube.com/watch?v=abc123") -> Lecture:
    return Lecture.create(
        id=LectureId("lecture-1"),
        title="サンプル講義",
        video_url=video_url,
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


class TestFakeVideoDurationResolver:
    """Fake の固定応答と呼び出し記録を検証する。"""

    def test_satisfies_video_duration_resolver_protocol(self) -> None:
        resolver: VideoDurationResolver = FakeVideoDurationResolver()
        assert callable(resolver.resolve)

    def test_returns_ok_with_default_duration(self) -> None:
        resolver = FakeVideoDurationResolver()
        lecture = _lecture()

        result = resolver.resolve(lecture)

        assert isinstance(result, Ok)
        assert result.value == 600
        assert resolver.resolve_calls == [lecture]

    def test_returns_ok_with_custom_duration(self) -> None:
        resolver = FakeVideoDurationResolver(duration_sec=300)
        lecture = _lecture()

        result = resolver.resolve(lecture)

        assert isinstance(result, Ok)
        assert result.value == 300

    def test_set_duration_sec_changes_response(self) -> None:
        resolver = FakeVideoDurationResolver(duration_sec=600)
        resolver.set_duration_sec(900)

        result = resolver.resolve(_lecture())

        assert isinstance(result, Ok)
        assert result.value == 900

    def test_returns_validation_error_when_configured(self) -> None:
        error = ValidationError("video ID could not be resolved")
        resolver = FakeVideoDurationResolver(error=error)

        result = resolver.resolve(_lecture())

        assert isinstance(result, Err)
        assert result.error is error

    def test_set_error_overrides_success_response(self) -> None:
        resolver = FakeVideoDurationResolver(duration_sec=600)
        error = ValidationError("duration must be positive")
        resolver.set_error(error)

        result = resolver.resolve(_lecture())

        assert isinstance(result, Err)
        assert result.error is error

    def test_returns_gateway_error_when_configured(self) -> None:
        error = VideoMetadataGatewayError("YouTube API unavailable")
        resolver = FakeVideoDurationResolver(error=error)

        result = resolver.resolve(_lecture())

        assert isinstance(result, Err)
        assert result.error is error

    @pytest.mark.parametrize("duration_sec", [0, -1])
    def test_constructor_rejects_non_positive_duration(self, duration_sec: int) -> None:
        with pytest.raises(ValueError, match="duration_sec must be > 0"):
            FakeVideoDurationResolver(duration_sec=duration_sec)

    def test_set_duration_sec_rejects_non_positive_duration(self) -> None:
        resolver = FakeVideoDurationResolver()

        with pytest.raises(ValueError, match="duration_sec must be > 0"):
            resolver.set_duration_sec(0)
