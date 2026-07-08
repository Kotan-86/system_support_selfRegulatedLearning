# 仕様: docs/spec/interfaces-layer.md#VideoDurationResolver
"""YouTube Data API による VideoDurationResolver 実装。"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from collections.abc import Callable
from typing import Any

from application.common.errors import AppError, ValidationError, VideoMetadataGatewayError
from application.common.result import Result, err, ok
from domain.learning.lecture import Lecture
from framework_drivers.external.youtube.youtube_duration_cache import YoutubeDurationCache
from framework_drivers.external.youtube.youtube_video_id import extract_youtube_video_id

_ISO8601_DURATION_RE = re.compile(
    r"^PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$"
)
_YOUTUBE_VIDEOS_API = "https://www.googleapis.com/youtube/v3/videos"


class YoutubeApiError(Exception):
    """YouTube Data API 呼び出し失敗。"""


def parse_iso8601_duration(duration: str) -> int:
    """YouTube contentDetails.duration (ISO 8601) を秒へ変換する。"""
    match = _ISO8601_DURATION_RE.fullmatch(duration.strip())
    if match is None:
        raise ValueError(f"unsupported ISO 8601 duration: {duration!r}")

    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    total = hours * 3600 + minutes * 60 + seconds
    if total <= 0:
        raise ValueError("duration must be positive")
    return total


def _default_http_get(url: str) -> bytes:
    from framework_drivers.external.http_proxy_env import should_use_http_proxy

    request = urllib.request.Request(url, method="GET")
    if should_use_http_proxy():
        proxies = urllib.request.getproxies()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
    else:
        # 学外など: 環境変数・OS のプロキシ設定を無視して直接接続
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=10) as response:
        return response.read()


class YoutubeVideoDurationResolver:
    """Lecture.video_url から YouTube Data API で動画総尺を解決する。"""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        cache: YoutubeDurationCache | None = None,
        http_get: Callable[[str], bytes] | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("YOUTUBE_API_KEY")
        self._cache = cache if cache is not None else YoutubeDurationCache()
        self._http_get = http_get if http_get is not None else _default_http_get

    def resolve(self, lecture: Lecture) -> Result[int, AppError]:
        video_id = extract_youtube_video_id(lecture.video_url)
        if video_id is None:
            return err(
                ValidationError(
                    "video ID could not be resolved from video_url",
                )
            )

        try:
            duration_sec = self._fetch_duration_sec(video_id)
        except ValidationError as exc:
            return err(exc)
        except YoutubeApiError as exc:
            cached = self._cache.get(video_id)
            if cached is not None:
                return ok(cached)
            return err(VideoMetadataGatewayError(str(exc)))

        self._cache.set(video_id, duration_sec)
        return ok(duration_sec)

    def _fetch_duration_sec(self, video_id: str) -> int:
        if not self._api_key:
            raise YoutubeApiError("YOUTUBE_API_KEY is not set")

        url = (
            f"{_YOUTUBE_VIDEOS_API}?id={video_id}"
            f"&part=contentDetails&key={self._api_key}"
        )
        try:
            raw = self._http_get(url)
        except OSError as exc:
            raise YoutubeApiError(f"YouTube API request failed: {exc}") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise YoutubeApiError("YouTube API returned invalid JSON") from exc

        return self._parse_duration_from_payload(payload)

    @staticmethod
    def _parse_duration_from_payload(payload: dict[str, Any]) -> int:
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            raise ValidationError("YouTube video metadata was not found")

        content_details = items[0].get("contentDetails")
        if not isinstance(content_details, dict):
            raise ValidationError("YouTube video metadata was not found")

        raw_duration = content_details.get("duration")
        if not isinstance(raw_duration, str):
            raise ValidationError("YouTube video duration is missing")

        try:
            return parse_iso8601_duration(raw_duration)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
