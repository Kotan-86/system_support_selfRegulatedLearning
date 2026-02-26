"""
SRT パーサーと「秒 → 該当セグメント」の単体テスト。

app.srt の parse_srt_file / get_segments_for_times が仕様どおり動くことを検証する。
"""
import pytest


# テスト用の最小 SRT（2ブロック）。00:00:14,639〜00:00:16,619 と 00:00:26,100〜00:00:27,000
_SAMPLE_SRT = """1
00:00:14,639 --> 00:00:16,619
のでシリーズを続けるにしたがって

2
00:00:26,100 --> 00:00:27,000
物理学
"""


class TestParseSrtFile:
    """parse_srt_file の仕様を検証する。"""

    def test_returns_list_of_segments_with_start_sec_end_sec_text(self) -> None:
        """パース結果は start_sec, end_sec, text を持つ辞書のリストである。"""
        from app.srt import parse_srt_file
        from pathlib import Path
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False, encoding="utf-8") as f:
            f.write(_SAMPLE_SRT)
            path = Path(f.name)
        try:
            segments = parse_srt_file(path)
        finally:
            path.unlink(missing_ok=True)

        assert isinstance(segments, list)
        assert len(segments) >= 2
        for seg in segments[:2]:
            assert "start_sec" in seg and "end_sec" in seg and "text" in seg
            assert isinstance(seg["start_sec"], (int, float))
            assert isinstance(seg["end_sec"], (int, float))
            assert isinstance(seg["text"], str)

    def test_parses_timestamps_to_seconds(self) -> None:
        """SRT のタイムスタンプが秒（float）に変換されている。"""
        from app.srt import parse_srt_file
        from pathlib import Path
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False, encoding="utf-8") as f:
            f.write(_SAMPLE_SRT)
            path = Path(f.name)
        try:
            segments = parse_srt_file(path)
        finally:
            path.unlink(missing_ok=True)

        # 00:00:14,639 → 14.639, 00:00:26,100 → 26.1
        first = segments[0]
        assert 14.6 <= first["start_sec"] <= 14.7
        assert 16.6 <= first["end_sec"] <= 16.7
        assert first["text"].strip() == "のでシリーズを続けるにしたがって"

        second = segments[1]
        assert 26.0 <= second["start_sec"] <= 26.2
        assert second["text"].strip() == "物理学"


class TestGetSegmentsForTimes:
    """get_segments_for_times の仕様を検証する。"""

    def test_returns_text_for_times_within_segments(self) -> None:
        """current_time のリストに対応するセグメントのテキストが時系列で連結される。"""
        from app.srt import parse_srt_file, get_segments_for_times
        from pathlib import Path
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False, encoding="utf-8") as f:
            f.write(_SAMPLE_SRT)
            path = Path(f.name)
        try:
            segments = parse_srt_file(path)
            text = get_segments_for_times(segments, [15, 26])
        finally:
            path.unlink(missing_ok=True)

        assert "のでシリーズを続けるにしたがって" in text
        assert "物理学" in text

    def test_returns_empty_or_none_when_no_segments(self) -> None:
        """セグメントが空のときは空文字または (なし) 相当。"""
        from app.srt import get_segments_for_times

        result = get_segments_for_times([], [15, 30])
        assert result == "" or "(なし)" in result or result is None
