"""
講義動画の SRT 字幕をパースし、視聴ログの current_time に対応するテキストを抽出する。
"""
import re
from pathlib import Path


def _srt_timestamp_to_seconds(s: str) -> float:
    """SRT のタイムスタンプ 'HH:MM:SS,mmm' を秒（float）に変換する。"""
    m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)", s.strip())
    if not m:
        return 0.0
    h, mi, sec, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return h * 3600 + mi * 60 + sec + ms / 1000.0


def parse_srt_file(path: Path) -> list[dict]:
    """
    SRT ファイルをパースし、各セグメントを { start_sec, end_sec, text } の辞書のリストで返す。
    """
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", text)
    segments = []
    for block in blocks:
        lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
        if len(lines) < 2:
            continue
        # lines[0]: 番号, lines[1]: "00:00:14,639 --> 00:00:16,619", lines[2:]: テキスト
        time_line = lines[1]
        arrow = time_line.find("-->")
        if arrow == -1:
            continue
        start_str = time_line[:arrow].strip()
        end_str = time_line[arrow + 3 :].strip()
        start_sec = _srt_timestamp_to_seconds(start_str)
        end_sec = _srt_timestamp_to_seconds(end_str)
        content = " ".join(lines[2:]) if len(lines) > 2 else ""
        segments.append({"start_sec": start_sec, "end_sec": end_sec, "text": content})
    return segments


def get_segments_for_times(
    segments: list[dict], times: list[int] | list[float]
) -> str:
    """
    視聴ログの current_time のリストに対応するセグメントのテキストを、
    時系列で重複なく連結して返す。セグメントが空の場合は "" を返す。
    ちょうどその時刻を含むセグメントが無い場合は、その時刻以降で始まる最初のセグメントを採用する。
    """
    if not segments:
        return ""
    seen: set[tuple[float, float]] = set()
    parts: list[str] = []
    for t in sorted(set(times)):
        t_sec = float(t)
        chosen = None
        for seg in segments:
            if seg["start_sec"] <= t_sec <= seg["end_sec"]:
                chosen = seg
                break
        if chosen is None:
            for seg in segments:
                if seg["start_sec"] >= t_sec:
                    chosen = seg
                    break
        if chosen is not None:
            key = (chosen["start_sec"], chosen["end_sec"])
            if key not in seen:
                seen.add(key)
                txt = chosen["text"].strip()
                if txt:
                    parts.append(txt)
    return "\n".join(parts)
