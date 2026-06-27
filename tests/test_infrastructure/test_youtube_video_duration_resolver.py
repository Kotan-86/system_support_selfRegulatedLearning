# 仕様: docs/spec/interfaces-layer.md#VideoDurationResolver
"""YouTube VideoDurationResolver Adapter のテスト。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from application.common.errors import ErrorCode, ValidationError, VideoMetadataGatewayError
from application.common.result import Err, Ok
from domain.learning.lecture import Lecture
from domain.learning.quiz_definition import Question, QuizDefinition
from domain.shared.ids import LectureId
from infrastructure.learning.youtube_duration_cache import YoutubeDurationCache
from infrastructure.learning.youtube_video_duration_resolver import (
    YoutubeVideoDurationResolver,
    parse_iso8601_duration,
)
from infrastructure.learning.youtube_video_id import extract_youtube_video_id
from interfaces.learning.ports.video_duration_resolver import VideoDurationResolver


def _lecture(*, video_url: str) -> Lecture:
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


def _api_payload(*, duration: str, video_id: str = "dQw4w9WgXcQ") -> bytes:
    return json.dumps(
        {
            "items": [
                {
                    "id": video_id,
                    "contentDetails": {"duration": duration},
                }
            ]
        }
    ).encode("utf-8")


class TestExtractYoutubeVideoId:
    @pytest.mark.parametrize(
        ("video_url", "expected"),
        [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            (
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120",
                "dQw4w9WgXcQ",
            ),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ],
    )
    def test_extracts_supported_formats(self, video_url: str, expected: str) -> None:
        assert extract_youtube_video_id(video_url) == expected

    @pytest.mark.parametrize(
        "video_url",
        [
            "",
            "https://example.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch",
            "not-a-video-id",
        ],
    )
    def test_returns_none_for_unresolvable_url(self, video_url: str) -> None:
        assert extract_youtube_video_id(video_url) is None


class TestParseIso8601Duration:
    @pytest.mark.parametrize(
        ("duration", "expected_sec"),
        [
            ("PT45S", 45),
            ("PT15M33S", 933),
            ("PT1H2M10S", 3730),
        ],
    )
    def test_parses_youtube_duration(self, duration: str, expected_sec: int) -> None:
        assert parse_iso8601_duration(duration) == expected_sec

    def test_rejects_non_positive_duration(self) -> None:
        with pytest.raises(ValueError, match="duration must be positive"):
            parse_iso8601_duration("PT0S")


class TestYoutubeDurationCache:
    def test_persists_to_json_file(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "youtube_duration_cache.json"
        cache = YoutubeDurationCache(file_path=cache_path)
        cache.set("dQw4w9WgXcQ", 212)

        reloaded = YoutubeDurationCache(file_path=cache_path)
        assert reloaded.get("dQw4w9WgXcQ") == 212


class TestYoutubeVideoDurationResolver:
    def test_satisfies_video_duration_resolver_protocol(self) -> None:
        resolver: VideoDurationResolver = YoutubeVideoDurationResolver(api_key="test-key")
        assert callable(resolver.resolve)

    def test_returns_ok_from_api_response(self) -> None:
        def http_get(url: str) -> bytes:
            assert "id=dQw4w9WgXcQ" in url
            assert "part=contentDetails" in url
            assert "key=test-key" in url
            return _api_payload(duration="PT15M33S")

        resolver = YoutubeVideoDurationResolver(
            api_key="test-key",
            http_get=http_get,
        )

        result = resolver.resolve(
            _lecture(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        )

        assert isinstance(result, Ok)
        assert result.value == 933

    def test_caches_successful_api_response(self) -> None:
        cache = YoutubeDurationCache()
        calls = {"count": 0}

        def http_get(url: str) -> bytes:
            calls["count"] += 1
            return _api_payload(duration="PT5M")

        resolver = YoutubeVideoDurationResolver(
            api_key="test-key",
            cache=cache,
            http_get=http_get,
        )
        lecture = _lecture(video_url="https://youtu.be/dQw4w9WgXcQ")

        first = resolver.resolve(lecture)
        second = resolver.resolve(lecture)

        assert isinstance(first, Ok)
        assert isinstance(second, Ok)
        assert first.value == second.value == 300
        assert cache.get("dQw4w9WgXcQ") == 300
        assert calls["count"] == 2

    def test_returns_stale_cache_when_api_fails(self) -> None:
        cache = YoutubeDurationCache()
        cache.set("dQw4w9WgXcQ", 600)

        def http_get(url: str) -> bytes:
            raise OSError("network down")

        resolver = YoutubeVideoDurationResolver(
            api_key="test-key",
            cache=cache,
            http_get=http_get,
        )

        result = resolver.resolve(
            _lecture(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        )

        assert isinstance(result, Ok)
        assert result.value == 600

    def test_returns_gateway_error_when_api_fails_without_cache(self) -> None:
        def http_get(url: str) -> bytes:
            raise OSError("network down")

        resolver = YoutubeVideoDurationResolver(
            api_key="test-key",
            http_get=http_get,
        )

        result = resolver.resolve(
            _lecture(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, VideoMetadataGatewayError)
        assert result.error.code == ErrorCode.VIDEO_METADATA_GATEWAY_ERROR

    def test_returns_validation_error_when_video_id_unresolvable(self) -> None:
        resolver = YoutubeVideoDurationResolver(api_key="test-key")

        result = resolver.resolve(_lecture(video_url="https://example.com/video"))

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)

    def test_returns_validation_error_when_api_returns_no_items(self) -> None:
        def http_get(url: str) -> bytes:
            return json.dumps({"items": []}).encode("utf-8")

        resolver = YoutubeVideoDurationResolver(
            api_key="test-key",
            http_get=http_get,
        )

        result = resolver.resolve(
            _lecture(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, ValidationError)

    def test_returns_gateway_error_when_api_key_missing(self) -> None:
        resolver = YoutubeVideoDurationResolver(api_key="")

        result = resolver.resolve(
            _lecture(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        )

        assert isinstance(result, Err)
        assert isinstance(result.error, VideoMetadataGatewayError)
