# 仕様: docs/spec/interfaces-layer.md#Tutoring-ACL-ChatPromptBuilder
# 仕様: docs/spec/interfaces-layer.md#ViewingBehaviorMetrics
"""プロンプト組み立て用のコンテキスト整形ユーティリティ。"""
from __future__ import annotations

import json
import os
from pathlib import Path

from domain.learning.lecture import Lecture
from domain.learning.lecture_outline import LectureOutline
from domain.learning.learning_snapshot import LearningSnapshot
from domain.learning.viewing_event import ViewingAction, ViewingEvent
from domain.tutoring.dialogue_move_history import DialogueMoveHistory
from domain.tutoring.message import Message

from interfaces.learning.services.quiz_result_rows import build_quiz_result_rows
from interfaces.learning.services.viewing_behavior_metrics import (
    SEGMENT_WIDTH_SEC,
    ViewingBehaviorMetrics,
    timeline_action_label,
)
from interfaces.tutoring.srt import get_segments_for_times, parse_srt_file

EMPTY_PLACEHOLDER = "(なし)"
HISTORY_EMPTY_PLACEHOLDER = "(履歴なし)"
LAD_TIMELINE_RECENT_LIMIT = 10
LAD_BUSY_SEGMENT_LIMIT = 3


def format_timestamp(occurred_at) -> str:
    return occurred_at.replace(microsecond=0).isoformat()


def format_history(messages: tuple[Message, ...]) -> str:
    """対話履歴をプロンプト用の文字列に整形する。"""
    lines = [f"{message.role.value}: {message.content}" for message in messages]
    return "\n".join(lines)


def format_move_history_json(history: DialogueMoveHistory) -> str:
    """直近 Coach Move 履歴を JSON 文字列に整形する。"""
    payload = [
        {
            "turn_index": record.turn_index,
            "dialogue_move": record.dialogue_move.value,
            "target_fields": list(record.target_fields),
        }
        for record in history.records
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_lecture_log(snapshot: LearningSnapshot) -> str:
    """視聴イベントを時系列で列挙する。データが無い場合は "(なし)"。"""
    if not snapshot.viewing_events:
        return EMPTY_PLACEHOLDER

    lines = []
    for event in snapshot.viewing_events:
        lines.append(
            f"{format_timestamp(event.occurred_at)} "
            f"action={event.action.value} "
            f"current_time={event.video_position} "
            f"duration={event.position_delta}"
        )
    return "\n".join(lines)


def format_evidence_list(evidence: tuple[str, ...] | list[str]) -> str:
    """提示必須証拠 ID をプロンプト用に整形する。空のときは "(なし)"。"""
    if not evidence:
        return EMPTY_PLACEHOLDER
    return ", ".join(str(item) for item in evidence)


def _infer_video_duration_sec(events: tuple[ViewingEvent, ...]) -> int:
    """視聴イベントから動画尺（秒）を推定する。"""
    if not events:
        return 1
    max_reached = max(
        event.video_position + max(event.position_delta, 0) for event in events
    )
    return max(max(event.video_position for event in events), max_reached, 1)


def _format_timeline_event(event: ViewingEvent) -> str:
    timecode = _format_timecode(event.video_position)
    label = timeline_action_label(event.action)

    if event.action in (ViewingAction.PLAY, ViewingAction.PAUSE):
        return f"- {timecode} {label}"

    target_sec = event.video_position + event.position_delta
    if event.action in (
        ViewingAction.FORWARD_SKIP,
        ViewingAction.FORWARD_SEEK,
    ):
        return (
            f"- {timecode} {label}"
            f"（+{event.position_delta}秒 → {_format_timecode(target_sec)}）"
        )

    return (
        f"- {timecode} {label}"
        f"（{event.position_delta}秒 → {_format_timecode(target_sec)}）"
    )


def format_lad_timeline(snapshot: LearningSnapshot) -> str:
    """視聴イベントを人間可読タイムラインに整形する。データが無い場合は "(なし)"。"""
    if not snapshot.viewing_events:
        return EMPTY_PLACEHOLDER

    lines = [_format_timeline_event(event) for event in snapshot.viewing_events]
    return "\n".join(lines)


def _format_busy_segment_ranges(
    metrics: ViewingBehaviorMetrics,
    *,
    limit: int = LAD_BUSY_SEGMENT_LIMIT,
) -> str:
    ranked_segments = sorted(
        metrics.video_segments,
        key=lambda segment: sum(segment.action_counts.values()),
        reverse=True,
    )
    busy_segments = [
        segment
        for segment in ranked_segments
        if sum(segment.action_counts.values()) > 0
    ][:limit]
    if not busy_segments:
        return EMPTY_PLACEHOLDER

    return ", ".join(
        _format_time_range(
            segment.segment_start_sec,
            segment.segment_start_sec + SEGMENT_WIDTH_SEC,
        )
        for segment in busy_segments
    )


def _format_lad_action_summary(metrics: ViewingBehaviorMetrics) -> str:
    counts = metrics.action_counts
    forward_ops = (
        counts[ViewingAction.FORWARD_SKIP.value]
        + counts[ViewingAction.FORWARD_SEEK.value]
    )
    backward_ops = (
        counts[ViewingAction.BACKWARD_SKIP.value]
        + counts[ViewingAction.BACKWARD_SEEK.value]
    )
    pause_ops = counts[ViewingAction.PAUSE.value]
    return (
        f"- 早送り: {forward_ops}回 / 巻き戻し: {backward_ops}回 / "
        f"一時停止: {pause_ops}回"
    )


def format_lad_digest(snapshot: LearningSnapshot, _lecture: Lecture) -> str:
    """視聴ログの集計サマリと直近タイムラインを整形する。データが無い場合は "(なし)"。"""
    if not snapshot.viewing_events:
        return EMPTY_PLACEHOLDER

    video_duration_sec = _infer_video_duration_sec(snapshot.viewing_events)
    metrics = ViewingBehaviorMetrics.from_events(
        snapshot.viewing_events,
        video_duration_sec=video_duration_sec,
    )
    recent_events = snapshot.viewing_events[-LAD_TIMELINE_RECENT_LIMIT:]
    recent_timeline = "\n".join(
        _format_timeline_event(event) for event in recent_events
    )

    return "\n".join(
        [
            "## 視聴ログ要約",
            _format_lad_action_summary(metrics),
            f"- 操作が多い区間: {_format_busy_segment_ranges(metrics)}",
            f"## 操作タイムライン（直近{LAD_TIMELINE_RECENT_LIMIT}件）",
            recent_timeline,
        ]
    )


def format_quiz_result(snapshot: LearningSnapshot, lecture: Lecture) -> str:
    """最新小テストのスコアと各問詳細を列挙する。データが無い場合は "(なし)"。"""
    attempt = snapshot.latest_quiz_attempt
    answers = snapshot.quiz_answers
    if attempt is None and not answers:
        return EMPTY_PLACEHOLDER

    parts: list[str] = []
    if attempt is not None:
        parts.append(
            f"スコア: {attempt.score_numerator}/{attempt.score_denominator}"
        )

    questions_by_index = {
        question.index: question for question in lecture.quiz_definition.questions
    }
    rows = build_quiz_result_rows(answers, lecture.quiz_definition)
    for row in rows:
        question = questions_by_index.get(row.question_index)
        lines = [f"問{row.question_index}:", f"  問題文: {row.question_text}"]
        if question is not None:
            lines.append(f"  選択肢: {', '.join(question.choices)}")
        lines.append(f"  学習者の解答: {row.selected_choice}")
        if question is not None:
            lines.append(f"  正解選択肢: {question.correct_answer}")
        lines.append(f"  正解フラグ: {1 if row.is_correct else 0}")
        parts.append("\n".join(lines))

    return "\n".join(parts) if parts else EMPTY_PLACEHOLDER


def _format_timecode(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


def _format_time_range(start_sec: int, end_sec: int | None) -> str:
    start = _format_timecode(start_sec)
    if end_sec is None:
        return start
    return f"{start}–{_format_timecode(end_sec)}"


def format_lecture_outline(outline: LectureOutline) -> str:
    """講義構造メタデータをプロンプト用に整形する。"""
    if outline.is_empty:
        return EMPTY_PLACEHOLDER

    parts: list[str] = ["## 講義構造"]

    for section in outline.sections:
        time_range = _format_time_range(section.start_sec, section.end_sec)
        parts.append(f"### セクション: {section.title} ({time_range})")
        if section.summary:
            parts.append(f"  概要: {section.summary}")

    for exercise in outline.in_video_exercises:
        timecode = _format_timecode(exercise.timestamp_sec)
        parts.append(f"### 演習: {exercise.title} ({timecode})")
        parts.append(f"  説明: {exercise.description}")

    if outline.quiz_rubric_notes:
        parts.append("### 小テスト採点意図")
        for note in outline.quiz_rubric_notes:
            parts.append(f"  問{note.question_index}: {note.note}")

    return "\n".join(parts)


def resolve_srt_path(lecture: Lecture) -> Path | None:
    """講義の SRT パスを解決する。存在しない場合は None。"""
    if lecture.srt_path:
        path = Path(lecture.srt_path)
        if path.exists():
            return path

    srt_path_str = os.environ.get("LECTURE_SRT_PATH")
    if srt_path_str:
        path = Path(srt_path_str)
        if path.exists():
            return path

    return None


def format_lecture_transcript(snapshot: LearningSnapshot, lecture: Lecture) -> str:
    """視聴位置に対応する講義字幕を抽出する。SRT 未設定・なしの場合は "(なし)"。"""
    if snapshot.lecture_transcript_excerpts:
        text = "\n".join(snapshot.lecture_transcript_excerpts)
        return text if text else EMPTY_PLACEHOLDER

    srt_path = resolve_srt_path(lecture)
    if srt_path is None:
        return EMPTY_PLACEHOLDER

    try:
        segments = parse_srt_file(srt_path)
    except (OSError, ValueError):
        return EMPTY_PLACEHOLDER

    times = [event.video_position for event in snapshot.viewing_events]
    text = get_segments_for_times(segments, times)
    return text if text else EMPTY_PLACEHOLDER
