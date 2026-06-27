# 仕様: docs/spec/interfaces-layer.md#VideoDurationResolver
"""YouTube video_url から video ID を抽出する。"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_BARE_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_youtube_video_id(video_url: str) -> str | None:
    """watch?v= / youtu.be / 裸 ID 形式から YouTube video ID を返す。解決不可なら None。"""
    stripped = video_url.strip()
    if not stripped:
        return None

    if _BARE_VIDEO_ID_RE.fullmatch(stripped):
        return stripped

    parsed = urlparse(stripped)
    host = (parsed.netloc or "").lower()
    if host.endswith("youtu.be"):
        video_id = parsed.path.lstrip("/").split("/")[0]
        return video_id if _BARE_VIDEO_ID_RE.fullmatch(video_id) else None

    if host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if parsed.path == "/watch":
            values = parse_qs(parsed.query).get("v", [])
            if values and _BARE_VIDEO_ID_RE.fullmatch(values[0]):
                return values[0]
            return None

        if parsed.path.startswith("/embed/"):
            video_id = parsed.path.removeprefix("/embed/").split("/")[0]
            return video_id if _BARE_VIDEO_ID_RE.fullmatch(video_id) else None

    return None
