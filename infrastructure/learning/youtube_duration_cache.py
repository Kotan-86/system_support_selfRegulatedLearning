# 仕様: docs/spec/interfaces-layer.md#VideoDurationResolver
"""YouTube 動画尺のメモリ + 任意 JSON ファイルキャッシュ。"""
from __future__ import annotations

import json
from pathlib import Path


class YoutubeDurationCache:
    """video_id → duration_sec のキャッシュ。API 障害時の stale 返却に用いる。"""

    def __init__(self, *, file_path: Path | None = None) -> None:
        self._file_path = file_path
        self._entries: dict[str, int] = {}
        if file_path is not None and file_path.is_file():
            self._entries = self._load_file(file_path)

    def get(self, video_id: str) -> int | None:
        """キャッシュ hit 時のみ duration_sec (> 0) を返す。"""
        duration_sec = self._entries.get(video_id)
        if duration_sec is None or duration_sec <= 0:
            return None
        return duration_sec

    def set(self, video_id: str, duration_sec: int) -> None:
        """成功取得した尺をメモリと任意ファイルへ保存する。"""
        if duration_sec <= 0:
            raise ValueError("duration_sec must be > 0")
        self._entries[video_id] = duration_sec
        if self._file_path is not None:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text(
                json.dumps(self._entries, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )

    @staticmethod
    def _load_file(file_path: Path) -> dict[str, int]:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("cache file must contain a JSON object")
        entries: dict[str, int] = {}
        for key, value in raw.items():
            if isinstance(key, str) and isinstance(value, int) and value > 0:
                entries[key] = value
        return entries
